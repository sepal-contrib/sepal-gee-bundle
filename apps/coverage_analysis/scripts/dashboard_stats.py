"""Dashboard stats computation for Coverage Analysis.

Cheap server-side counts: one ``size()`` call per sensor and per year.
The merged collection has no sensor tag on each image, so per-sensor counts
rebuild a single-sensor collection via :func:`build_collection`.
"""

from __future__ import annotations

from apps.coverage_analysis.scripts.analysis import year_windows
from apps.coverage_analysis.scripts.collection_builder import build_collection


async def compute_dashboard_stats(
    aoi,
    start: str,
    end: str,
    sensors: list[str] | tuple[str, ...],
    sr: bool,
    include_t2: bool,
    measure: str,
    gee_interface,
) -> dict:
    """Count images per sensor and per year, plus totals + AOI area.

    Args:
        aoi: ``ee.FeatureCollection`` (or geometry) of the AOI.
        start: ``YYYY-MM-DD`` inclusive.
        end: ``YYYY-MM-DD`` exclusive.
        sensors: selected sensor codes.
        sr: Surface Reflectance toggle (matches the live collection).
        include_t2: Tier 2 toggle (Landsat).
        measure: active measure code (echoed into totals for the summary).
        gee_interface: session-backed GEE interface.

    Returns:
        ``{"per_sensor": [...], "per_year": [...], "totals": {...}}``.
    """
    per_sensor: list[dict] = []
    total_count = 0

    for sensor in list(sensors or []):
        sub = build_collection(
            aoi=aoi,
            start=start,
            end=end,
            sensors=[sensor],
            sr=sr,
            include_t2=include_t2,
        )
        if sub is None:
            per_sensor.append({"sensor": sensor, "count": 0})
            continue
        size = await gee_interface.get_info_async(sub.size())
        size = int(size or 0)
        per_sensor.append({"sensor": sensor, "count": size})
        total_count += size

    # Per-year counts using the full merged collection — cheaper than
    # rebuilding once per (sensor, year).
    full = build_collection(
        aoi=aoi,
        start=start,
        end=end,
        sensors=list(sensors or []),
        sr=sr,
        include_t2=include_t2,
    )

    per_year: list[dict] = []
    if full is not None:
        for w_start, w_end, year in year_windows(start, end):
            y_count = await gee_interface.get_info_async(full.filterDate(w_start, w_end).size())
            per_year.append({"year": int(year), "count": int(y_count or 0)})

    # AOI area (ha) — single reduceRegion, cheap.
    aoi_area_ha = 0.0
    try:
        geom = aoi.geometry() if hasattr(aoi, "geometry") else aoi
        area_m2 = await gee_interface.get_info_async(geom.area(1))
        aoi_area_ha = float(area_m2 or 0.0) / 10_000.0
    except Exception:
        aoi_area_ha = 0.0

    totals = {
        "aoi_area_ha": aoi_area_ha,
        "total_count": total_count,
        "date_range": f"{start} — {end}",
        "sensors": list(sensors or []),
        "measure": measure,
    }

    return {"per_sensor": per_sensor, "per_year": per_year, "totals": totals}
