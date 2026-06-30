"""Dataset staleness checker for the sepal-gee-bundle.

Walks the descriptors in :mod:`apps._commons.datasets`, probes Earth Engine
for newer versions / new years / asset existence, and emits a markdown or
JSON report.

Probe strategies
----------------
- ``version_pattern`` — for ``{year}/{minor}``-style snapshots (Hansen, JRC
  TMF).  Walks forward from the pinned tuple, calling ``getInfo()`` on each
  candidate until ``EEException``.
- ``year_in_collection`` — for year-keyed collections (ALOS).  Aggregates
  the ``year`` property; falls back to ``system:index`` parsing.
- ``static`` — confirms the asset still resolves; emits ``STALE_REVIEW``
  when ``last_reviewed`` is older than 180 days.

Exit codes
----------
- ``0`` — every entry OK.
- ``1`` — at least one ``NEWER_AVAILABLE`` / ``STALE_REVIEW``.
- ``2`` — auth failed or probe error.

Run as ``python -m apps._commons.dataset_check [--json]``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from apps._commons.datasets import (
    REGISTRY,
    DatasetDescriptor,
)

logger = logging.getLogger(__name__)

STALE_REVIEW_THRESHOLD_DAYS = 180
VERSION_PATTERN_FORWARD_STEPS = 10

STATUS_OK = "OK"
STATUS_NEWER = "NEWER_AVAILABLE"
STATUS_STALE_REVIEW = "STALE_REVIEW"
STATUS_ERROR = "ERROR"
NON_OK_STATUSES = {STATUS_NEWER, STATUS_STALE_REVIEW, STATUS_ERROR}


@dataclass
class CheckResult:
    key: str
    status: str
    pinned: dict[str, Any] = field(default_factory=dict)
    latest: dict[str, Any] | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _today_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_date_age_days(iso: str, today: datetime | None = None) -> int:
    today = today or _today_utc()
    parsed = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
    return (today - parsed).days


# ---------------------------------------------------------------------------
# Probe strategies
# ---------------------------------------------------------------------------


def _asset_exists(ee: Any, asset_id: str) -> bool:
    """Return ``True`` if any of ``ImageCollection`` / ``Image`` / ``FeatureCollection``
    can resolve the asset id.  Tries each constructor in turn — EE assets can be
    raster collections, single rasters, or vector collections (HydroSHEDS).
    """
    for ctor_name in ("ImageCollection", "Image", "FeatureCollection"):
        ctor = getattr(ee, ctor_name, None)
        if ctor is None:
            continue
        try:
            obj = ctor(asset_id)
            if hasattr(obj, "limit"):
                obj = obj.limit(0)
            obj.getInfo()
            return True
        except Exception:
            continue
    return False


def _probe_version_pattern(ee: Any, d: DatasetDescriptor) -> CheckResult:
    """Walk forward from the pinned snapshot until we stop finding newer versions."""
    pinned = dict(d.pinned)
    if "year" not in pinned:
        return CheckResult(d.key, STATUS_ERROR, pinned, message="missing pinned.year")

    latest = dict(pinned)
    # Try year+1 (with minor reset to a high-water-mark) and minor+1.
    for _ in range(VERSION_PATTERN_FORWARD_STEPS):
        candidates: list[dict[str, Any]] = []
        if "minor" in latest:
            candidates.append({**latest, "minor": int(latest["minor"]) + 1})
            candidates.append({**latest, "year": int(latest["year"]) + 1, "minor": 12})
        else:
            candidates.append({**latest, "year": int(latest["year"]) + 1})

        advanced = False
        for cand in candidates:
            try:
                asset = _render_version_pattern(d, cand)
            except Exception as exc:
                return CheckResult(d.key, STATUS_ERROR, pinned, message=str(exc))
            if _asset_exists(ee, asset):
                latest = cand
                advanced = True
                break
        if not advanced:
            break

    if latest != pinned:
        return CheckResult(d.key, STATUS_NEWER, pinned, latest=latest)
    return CheckResult(d.key, STATUS_OK, pinned, latest=latest)


def _render_version_pattern(d: DatasetDescriptor, values: dict[str, Any]) -> str:
    """Render a version-pattern asset id, defaulting ``{product}`` for TMF-style ids."""
    pattern = d.pattern or ""
    fill = dict(values)
    if "{product}" in pattern and "product" not in fill:
        fill["product"] = "AnnualChanges"
    return d.resolved_id(**fill)


def _probe_year_in_collection(ee: Any, d: DatasetDescriptor) -> CheckResult:
    pinned_years = sorted(int(y) for y in d.pinned.get("years", []))
    if not pinned_years:
        return CheckResult(d.key, STATUS_ERROR, dict(d.pinned), message="missing pinned.years")
    if d.asset_id is None:
        return CheckResult(d.key, STATUS_ERROR, dict(d.pinned), message="missing asset_id")

    try:
        coll = ee.ImageCollection(d.asset_id)
        years = coll.aggregate_array("year").distinct().getInfo() or []
        years = [int(y) for y in years]
        if not years:
            # Some collections don't expose `year`; fall back to system:index parsing.
            ids = coll.aggregate_array("system:index").getInfo() or []
            years = sorted({_year_from_index(s) for s in ids if _year_from_index(s)})
    except Exception as exc:
        return CheckResult(d.key, STATUS_ERROR, dict(d.pinned), message=str(exc))

    latest = sorted(set(years))
    if set(latest) - set(pinned_years):
        return CheckResult(
            d.key,
            STATUS_NEWER,
            dict(d.pinned),
            latest={"years": latest},
            message=f"new years: {sorted(set(latest) - set(pinned_years))}",
        )
    return CheckResult(d.key, STATUS_OK, dict(d.pinned), latest={"years": latest})


def _year_from_index(s: str) -> int | None:
    """Best-effort extraction of a 4-digit year from a system:index string."""
    for token in s.replace("/", "_").split("_"):
        if len(token) == 4 and token.isdigit() and 1900 < int(token) < 2200:
            return int(token)
    return None


def _probe_static(ee: Any, d: DatasetDescriptor, today: datetime | None = None) -> CheckResult:
    today = today or _today_utc()
    asset = d.asset_id
    if asset is None:
        return CheckResult(d.key, STATUS_ERROR, dict(d.pinned), message="missing asset_id")

    # Templated static (e.g. HydroSHEDS hybas_{level}) — pick a canonical level for liveness.
    probe_id = asset.replace("{level}", "8") if "{level}" in asset else asset
    if not _asset_exists(ee, probe_id):
        return CheckResult(
            d.key, STATUS_ERROR, dict(d.pinned), message=f"asset not found: {probe_id}"
        )

    age = _iso_date_age_days(d.last_reviewed, today=today)
    if age > STALE_REVIEW_THRESHOLD_DAYS:
        return CheckResult(
            d.key,
            STATUS_STALE_REVIEW,
            dict(d.pinned),
            message=f"last_reviewed {d.last_reviewed} ({age}d ago) > {STALE_REVIEW_THRESHOLD_DAYS}d",
        )
    return CheckResult(d.key, STATUS_OK, dict(d.pinned))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


PROBES = {
    "version_pattern": _probe_version_pattern,
    "year_in_collection": _probe_year_in_collection,
    "static": _probe_static,
}


def check_registry(
    ee: Any,
    registry: tuple[DatasetDescriptor, ...] = REGISTRY,
    today: datetime | None = None,
) -> list[CheckResult]:
    """Run probes for every descriptor and collect results."""
    results: list[CheckResult] = []
    for d in registry:
        probe = PROBES.get(d.probe)
        if probe is None:
            results.append(
                CheckResult(
                    d.key, STATUS_ERROR, dict(d.pinned), message=f"unknown probe: {d.probe}"
                )
            )
            continue
        try:
            if d.probe == "static":
                results.append(_probe_static(ee, d, today=today))
            else:
                results.append(probe(ee, d))
        except Exception as exc:
            results.append(CheckResult(d.key, STATUS_ERROR, dict(d.pinned), message=str(exc)))
    return results


def render_markdown(results: list[CheckResult]) -> str:
    lines = ["# Dataset staleness report", ""]
    lines.append("| Dataset | Status | Pinned | Latest | Message |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        pinned = json.dumps(r.pinned, sort_keys=True) if r.pinned else ""
        latest = json.dumps(r.latest, sort_keys=True) if r.latest else ""
        message = r.message.replace("|", "\\|")
        lines.append(f"| `{r.key}` | {r.status} | `{pinned}` | `{latest}` | {message} |")
    lines.append("")
    return "\n".join(lines)


def render_json(results: list[CheckResult]) -> str:
    return json.dumps([r.to_dict() for r in results], indent=2, sort_keys=True)


def overall_exit_code(results: list[CheckResult]) -> int:
    if any(r.status == STATUS_ERROR for r in results):
        return 2
    if any(r.status in NON_OK_STATUSES for r in results):
        return 1
    return 0


def _initialize_ee() -> Any:
    """Initialize the Earth Engine SDK; raise on failure."""
    import ee  # local import — avoids hard dependency at module load

    ee.Initialize()
    return ee


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dataset_check")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = parser.parse_args(argv)

    try:
        ee = _initialize_ee()
    except Exception as exc:
        sys.stderr.write(f"ERROR: GEE auth required: {exc}\n")
        return 2

    results = check_registry(ee)
    out = render_json(results) if args.json else render_markdown(results)
    print(out)
    return overall_exit_code(results)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
