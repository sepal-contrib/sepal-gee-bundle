"""Unit tests for the dataset staleness checker (mocked Earth Engine)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from apps._commons import dataset_check as dc
from apps._commons import datasets as ds

# ---------------------------------------------------------------------------
# Fake ee module
# ---------------------------------------------------------------------------


class FakeImageCollection:
    def __init__(self, asset_id: str, *, exists_set: set[str], year_map: dict[str, list[int]] | None = None,
                 index_map: dict[str, list[str]] | None = None):
        self._id = asset_id
        self._exists = exists_set
        self._year_map = year_map or {}
        self._index_map = index_map or {}

    def limit(self, _n):
        return self

    def aggregate_array(self, prop: str):
        if prop == "year":
            return _Carrier(self._year_map.get(self._id, []))
        if prop == "system:index":
            return _Carrier(self._index_map.get(self._id, []))
        return _Carrier([])

    def getInfo(self):
        if self._id not in self._exists:
            raise RuntimeError(f"asset not found: {self._id}")
        return {}


class FakeImage:
    def __init__(self, asset_id: str, *, exists_set: set[str]):
        self._id = asset_id
        self._exists = exists_set

    def getInfo(self):
        if self._id not in self._exists:
            raise RuntimeError(f"asset not found: {self._id}")
        return {}


class _Carrier:
    def __init__(self, values):
        self._values = list(values)

    def distinct(self):
        return _Carrier(sorted(set(self._values)))

    def getInfo(self):
        return list(self._values)


def fake_ee(*, exists: set[str] | None = None, year_map=None, index_map=None) -> MagicMock:
    exists_set = set(exists or [])
    mock = MagicMock()
    mock.ImageCollection.side_effect = lambda asset: FakeImageCollection(
        asset, exists_set=exists_set, year_map=year_map, index_map=index_map
    )
    mock.Image.side_effect = lambda asset: FakeImage(asset, exists_set=exists_set)
    mock.FeatureCollection.side_effect = lambda asset: FakeImage(asset, exists_set=exists_set)
    return mock


# ---------------------------------------------------------------------------
# version_pattern
# ---------------------------------------------------------------------------


def _hansen_descriptor(year: int = 2024, minor: int = 12) -> ds.DatasetDescriptor:
    return ds.DatasetDescriptor(
        key="HANSEN_TEST",
        probe="version_pattern",
        last_reviewed="2026-04-27",
        pattern="UMD/hansen/global_forest_change_{year}_v1_{minor}",
        pinned={"year": year, "minor": minor},
    )


def test_version_pattern_ok_when_no_newer_published():
    d = _hansen_descriptor()
    ee = fake_ee(exists={d.resolved_id()})
    result = dc._probe_version_pattern(ee, d)
    assert result.status == dc.STATUS_OK


def test_version_pattern_detects_minor_bump():
    d = _hansen_descriptor()
    pinned_id = d.resolved_id()
    next_minor = d.resolved_id(minor=13)
    ee = fake_ee(exists={pinned_id, next_minor})
    result = dc._probe_version_pattern(ee, d)
    assert result.status == dc.STATUS_NEWER
    assert result.latest["minor"] == 13


def test_version_pattern_walks_year_then_minor():
    d = _hansen_descriptor()
    next_year_default = d.resolved_id(year=2025, minor=12)
    ee = fake_ee(exists={d.resolved_id(), next_year_default})
    result = dc._probe_version_pattern(ee, d)
    assert result.status == dc.STATUS_NEWER
    assert result.latest["year"] == 2025
    assert result.latest["minor"] == 12


def test_version_pattern_caps_at_forward_steps():
    d = _hansen_descriptor()
    # Make every conceivable id exist; we shouldn't loop forever.
    ee = fake_ee()
    ee.ImageCollection.side_effect = lambda asset: FakeImageCollection(
        asset, exists_set={asset}
    )
    result = dc._probe_version_pattern(ee, d)
    # Must terminate after VERSION_PATTERN_FORWARD_STEPS bumps.
    assert result.status == dc.STATUS_NEWER
    delta_minor = (result.latest["year"] - 2024) * 0 + (result.latest["minor"] - 12)
    delta_year = result.latest["year"] - 2024
    assert delta_year + delta_minor <= dc.VERSION_PATTERN_FORWARD_STEPS


# ---------------------------------------------------------------------------
# year_in_collection
# ---------------------------------------------------------------------------


def test_year_in_collection_ok_when_pinned_matches_live():
    d = ds.DatasetDescriptor(
        key="ALOS_TEST",
        probe="year_in_collection",
        last_reviewed="2026-04-27",
        asset_id="JAXA/ALOS/PALSAR/YEARLY/SAR",
        pinned={"years": [2018, 2019, 2020]},
    )
    ee = fake_ee(
        exists={d.asset_id},
        year_map={d.asset_id: [2018, 2019, 2020]},
    )
    result = dc._probe_year_in_collection(ee, d)
    assert result.status == dc.STATUS_OK


def test_year_in_collection_detects_new_year():
    d = ds.DatasetDescriptor(
        key="ALOS_TEST",
        probe="year_in_collection",
        last_reviewed="2026-04-27",
        asset_id="JAXA/ALOS/PALSAR/YEARLY/SAR",
        pinned={"years": [2018, 2019, 2020]},
    )
    ee = fake_ee(
        exists={d.asset_id},
        year_map={d.asset_id: [2018, 2019, 2020, 2021]},
    )
    result = dc._probe_year_in_collection(ee, d)
    assert result.status == dc.STATUS_NEWER
    assert 2021 in result.latest["years"]


def test_year_in_collection_falls_back_to_system_index():
    d = ds.DatasetDescriptor(
        key="X",
        probe="year_in_collection",
        last_reviewed="2026-04-27",
        asset_id="some/coll",
        pinned={"years": [2010]},
    )
    ee = fake_ee(
        exists={d.asset_id},
        year_map={d.asset_id: []},
        index_map={d.asset_id: ["x_2010_y", "x_2011_y"]},
    )
    result = dc._probe_year_in_collection(ee, d)
    assert result.status == dc.STATUS_NEWER
    assert 2011 in result.latest["years"]


# ---------------------------------------------------------------------------
# static
# ---------------------------------------------------------------------------


def _today(year=2026, month=4, day=27) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_static_ok_when_recent():
    d = ds.DatasetDescriptor(
        key="S2_T",
        probe="static",
        last_reviewed="2026-03-01",
        asset_id="COPERNICUS/S2_HARMONIZED",
    )
    ee = fake_ee(exists={d.asset_id})
    result = dc._probe_static(ee, d, today=_today())
    assert result.status == dc.STATUS_OK


def test_static_stale_when_review_older_than_threshold():
    old_date = (_today() - timedelta(days=dc.STALE_REVIEW_THRESHOLD_DAYS + 5)).date().isoformat()
    d = ds.DatasetDescriptor(
        key="S2_T",
        probe="static",
        last_reviewed=old_date,
        asset_id="COPERNICUS/S2_HARMONIZED",
    )
    ee = fake_ee(exists={d.asset_id})
    result = dc._probe_static(ee, d, today=_today())
    assert result.status == dc.STATUS_STALE_REVIEW


def test_static_error_when_missing():
    d = ds.DatasetDescriptor(
        key="MISSING",
        probe="static",
        last_reviewed="2026-04-27",
        asset_id="not/here",
    )
    ee = fake_ee(exists=set())
    result = dc._probe_static(ee, d, today=_today())
    assert result.status == dc.STATUS_ERROR


def test_static_template_probes_canonical_level():
    d = ds.DatasetDescriptor(
        key="HYBAS",
        probe="static",
        last_reviewed="2026-04-27",
        asset_id="WWF/HydroSHEDS/v1/Basins/hybas_{level}",
    )
    ee = fake_ee(exists={"WWF/HydroSHEDS/v1/Basins/hybas_8"})
    result = dc._probe_static(ee, d, today=_today())
    assert result.status == dc.STATUS_OK


# ---------------------------------------------------------------------------
# render + exit code
# ---------------------------------------------------------------------------


def test_render_markdown_includes_every_key():
    results = [
        dc.CheckResult("A", dc.STATUS_OK, {"year": 2024}),
        dc.CheckResult("B", dc.STATUS_NEWER, {"year": 2024}, latest={"year": 2025}),
    ]
    md = dc.render_markdown(results)
    assert "| `A` |" in md
    assert "| `B` |" in md
    assert "NEWER_AVAILABLE" in md


def test_render_json_round_trips():
    import json

    results = [dc.CheckResult("A", dc.STATUS_OK, {"year": 2024})]
    data = json.loads(dc.render_json(results))
    assert data == [{"key": "A", "status": "OK", "pinned": {"year": 2024}, "latest": None, "message": ""}]


@pytest.mark.parametrize(
    "statuses,expected",
    [
        ([dc.STATUS_OK, dc.STATUS_OK], 0),
        ([dc.STATUS_OK, dc.STATUS_NEWER], 1),
        ([dc.STATUS_OK, dc.STATUS_STALE_REVIEW], 1),
        ([dc.STATUS_OK, dc.STATUS_ERROR], 2),
        ([dc.STATUS_NEWER, dc.STATUS_ERROR], 2),
    ],
)
def test_overall_exit_code(statuses, expected):
    results = [dc.CheckResult(str(i), s) for i, s in enumerate(statuses)]
    assert dc.overall_exit_code(results) == expected


# ---------------------------------------------------------------------------
# Integration: check_registry against a fully-pinned-OK fake EE
# ---------------------------------------------------------------------------


def test_check_registry_all_ok_when_pinned_matches_live():
    """Build a fake EE that has exactly the pinned ids and pinned year sets."""
    pinned_ids: set[str] = set()
    year_map: dict[str, list[int]] = {}
    for d in ds.REGISTRY:
        if d.probe == "version_pattern":
            # Pinned id resolves; minor+1 / year+1 do not.
            if "{product}" in (d.pattern or ""):
                pinned_ids.add(d.resolved_id(product="AnnualChanges"))
            else:
                pinned_ids.add(d.resolved_id())
        elif d.probe == "year_in_collection" and d.asset_id is not None:
            pinned_ids.add(d.asset_id)
            year_map[d.asset_id] = list(d.pinned["years"])
        elif d.probe == "static" and d.asset_id is not None:
            asset = d.asset_id.replace("{level}", "8")
            pinned_ids.add(asset)

    ee = fake_ee(exists=pinned_ids, year_map=year_map)
    results = dc.check_registry(ee, today=_today())
    non_ok = [r for r in results if r.status != dc.STATUS_OK]
    assert non_ok == [], non_ok
