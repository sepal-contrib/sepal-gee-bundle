"""Temporal reduction of coverage / NDVI measures (total or annual).

Pure functions that take a pre-built merged ``ee.ImageCollection`` (with
``NDVI`` and ``COUNT`` bands, see :func:`collection_builder.build_collection`)
and produce a single ``ee.Image`` with one band per (measure, period).
"""

from __future__ import annotations

from datetime import datetime

import ee

MEASURE_BAND = {
    "pixel_count": "COUNT",
    "pixel_count_all": "COUNT",
    "ndvi_median": "NDVI",
    "ndvi_stdDev": "NDVI",
}

MEASURE_REDUCER = {
    "pixel_count": lambda: ee.Reducer.count(),
    "pixel_count_all": lambda: ee.Reducer.count(),
    "ndvi_median": lambda: ee.Reducer.median(),
    "ndvi_stdDev": lambda: ee.Reducer.stdDev(),
}


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def year_windows(start: str, end: str) -> list[tuple[str, str, int]]:
    """Split ``[start, end]`` into year-long windows.

    Args:
        start: inclusive start, ``YYYY-MM-DD``.
        end: exclusive end, ``YYYY-MM-DD``.

    Returns:
        list of ``(window_start, window_end, year)`` tuples. The first
        window begins at ``start`` and subsequent windows start on Jan 1.
        The last window ends at ``end`` if it falls inside a year.
    """
    start_dt = _parse_date(start)
    end_dt = _parse_date(end)
    if start_dt >= end_dt:
        return []

    windows: list[tuple[str, str, int]] = []
    cur = start_dt
    while cur < end_dt:
        year = cur.year
        next_year_start = datetime(year + 1, 1, 1)
        window_end = min(next_year_start, end_dt)
        windows.append((cur.strftime("%Y-%m-%d"), window_end.strftime("%Y-%m-%d"), year))
        cur = next_year_start
    return windows


def _unmask_1(img: ee.Image) -> ee.Image:
    return img.unmask(1)


def reduce_measure(
    coll: ee.ImageCollection,
    measure: str,
    start: str,
    end: str,
    aoi,
    band_suffix: str = "total",
) -> ee.Image:
    """Reduce a collection for a single measure + period.

    Returns a one-band clipped image whose band is named
    ``{measure}_{band_suffix}``.
    """
    if measure not in MEASURE_REDUCER:
        raise ValueError(f"Unknown measure: {measure!r}")

    band = MEASURE_BAND[measure]
    reducer = MEASURE_REDUCER[measure]()
    sub = coll.select(band).filterDate(start, end)

    # pixel_count_all counts every observation including masked-out cloud
    # pixels — unmask to 1 so .count() picks them up.
    if measure == "pixel_count_all":
        sub = sub.map(_unmask_1)

    name = f"{measure}_{band_suffix}"
    return sub.reduce(reducer).rename(name).clip(aoi.geometry())


def compose_measure(
    coll: ee.ImageCollection,
    measure: str,
    start: str,
    end: str,
    aoi,
    annual: bool,
) -> tuple[ee.Image, list[str]]:
    """Build one composite image with total or per-year bands.

    Returns ``(image, band_names)``. When ``annual`` is False, produces a
    single ``{measure}_total`` band; otherwise one ``{measure}_{year}``
    band per year in the range.
    """
    if not annual:
        img = reduce_measure(coll, measure, start, end, aoi, band_suffix="total")
        return img, [f"{measure}_total"]

    windows = year_windows(start, end)
    if not windows:
        raise ValueError("Invalid date range.")

    parts: list[ee.Image] = []
    names: list[str] = []
    for w_start, w_end, year in windows:
        part = reduce_measure(coll, measure, w_start, w_end, aoi, band_suffix=str(year))
        parts.append(part)
        names.append(f"{measure}_{year}")

    img = parts[0]
    for extra in parts[1:]:
        img = img.addBands(extra)
    return img, names


def build_export_image(
    coll: ee.ImageCollection,
    stats: list[str] | tuple[str, ...],
    temps: list[str] | tuple[str, ...],
    start: str,
    end: str,
    aoi,
) -> ee.Image | None:
    """Build a multi-band image covering every (stat, temp) combination.

    Stats items map to measures:
        count       -> pixel_count
        all         -> pixel_count_all
        ndvi_median -> ndvi_median
        ndvi_stdDev -> ndvi_stdDev
    """
    stats_to_measure = {
        "count": "pixel_count",
        "all": "pixel_count_all",
        "ndvi_median": "ndvi_median",
        "ndvi_stdDev": "ndvi_stdDev",
    }

    if not stats or not temps:
        return None

    out: ee.Image | None = None
    for stat in stats:
        measure = stats_to_measure.get(stat)
        if measure is None:
            continue

        if "total_exp" in temps:
            total = reduce_measure(coll, measure, start, end, aoi, band_suffix="total")
            out = total if out is None else out.addBands(total)

        if "annual_exp" in temps:
            for w_start, w_end, year in year_windows(start, end):
                band = reduce_measure(coll, measure, w_start, w_end, aoi, band_suffix=str(year))
                out = band if out is None else out.addBands(band)

    return out
