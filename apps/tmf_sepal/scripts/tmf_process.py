"""Pure GEE helpers for JRC TMF processing.

Mirrors the legacy ``component/scripts/default_process.py`` and
``component/scripts/display.py`` logic without any UI dependency.
"""

from __future__ import annotations

import ee

from apps.tmf_sepal.params import (
    TMF_MIN_YEAR,
    change_viz_params,
    chg_dataset_id,
    def_dataset_id,
    deg_dataset_id,
    year_viz_params,
)

VALID_TYPES = ("DEG", "DEF", "CHG")


def _collection_for(tmf_type: str) -> ee.ImageCollection:
    if tmf_type == "DEG":
        return ee.ImageCollection(deg_dataset_id())
    if tmf_type == "DEF":
        return ee.ImageCollection(def_dataset_id())
    if tmf_type == "CHG":
        return ee.ImageCollection(chg_dataset_id())
    raise ValueError(f"Unknown TMF type: {tmf_type!r} (expected one of {VALID_TYPES})")


def build_tmf_image(
    aoi: ee.FeatureCollection,
    tmf_type: str,
    year_start: int,
    year_end: int,
) -> ee.Image:
    """Build the JRC TMF image to display for the given AOI and year range.

    For DEG/DEF the result is a single-band mosaic masked to pixels where the
    year-of-event band falls within ``[year_start, year_end]``.

    For CHG the result is a multi-band stack ``DecYYYY`` covering the selected
    years (1990 = band 0).
    """
    if tmf_type not in VALID_TYPES:
        raise ValueError(f"Unknown TMF type: {tmf_type!r}")
    if year_start > year_end:
        raise ValueError(f"year_start ({year_start}) must be <= year_end ({year_end})")

    collection = _collection_for(tmf_type)
    mosaic = collection.mosaic().clip(aoi)

    if tmf_type == "CHG":
        band_beg = year_start - TMF_MIN_YEAR
        band_end = year_end - TMF_MIN_YEAR
        return mosaic.select(ee.List.sequence(band_beg, band_end))

    mask = mosaic.lte(ee.Number(year_end)).And(mosaic.gte(ee.Number(year_start))).selfMask()
    return mosaic.mask(mask)


def viz_params_for(tmf_type: str, year_start: int, year_end: int) -> dict:
    """Return the map visualization params for the given layer type."""
    if tmf_type in ("DEG", "DEF"):
        return year_viz_params(year_start, year_end)
    if tmf_type == "CHG":
        return change_viz_params(year_start, year_end)
    raise ValueError(f"Unknown TMF type: {tmf_type!r}")
