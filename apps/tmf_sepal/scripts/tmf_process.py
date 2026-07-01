"""Pure GEE helpers for JRC TMF processing.

Mirrors the legacy ``component/scripts/default_process.py`` and
``component/scripts/display.py`` logic without any UI dependency.
"""

from __future__ import annotations

import ee

from apps.tmf_sepal.params import (
    TMF_CHG_TRANSITION_REMAP,
    TMF_SUBTYPE_TO_MAIN,
    change_viz_params,
    chg_dataset_id,
    def_dataset_id,
    deg_dataset_id,
    transition_main_viz_params,
    transitionmap_id,
    year_viz_params,
)

VALID_TYPES = ("DEG", "DEF", "CHG", "TRANS")


def _collection_for(tmf_type: str) -> ee.ImageCollection:
    if tmf_type == "DEG":
        return ee.ImageCollection(deg_dataset_id())
    if tmf_type == "DEF":
        return ee.ImageCollection(def_dataset_id())
    if tmf_type == "CHG":
        return ee.ImageCollection(chg_dataset_id())
    if tmf_type == "TRANS":
        return ee.ImageCollection(transitionmap_id())
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

    For CHG the result is a single ``transition`` band holding the start->end
    transition class (1..7, see ``TMF_CHG_TRANSITION_CLASSES``).

    For TRANS the result is a single ``transition_main`` band holding the JRC
    TransitionMap main class (1..9, see ``TMF_TRANSITION_MAIN_CLASSES``); it is
    whole-period and ignores the year range.
    """
    if tmf_type not in VALID_TYPES:
        raise ValueError(f"Unknown TMF type: {tmf_type!r}")

    collection = _collection_for(tmf_type)
    mosaic = collection.mosaic().clip(aoi)

    if tmf_type == "TRANS":
        return (
            mosaic.remap(
                list(TMF_SUBTYPE_TO_MAIN),
                list(TMF_SUBTYPE_TO_MAIN.values()),
                0,  # subtype codes outside the recode -> masked by selfMask
            )
            .selfMask()
            .rename("transition_main")
            .toInt()
        )

    if year_start > year_end:
        raise ValueError(f"year_start ({year_start}) must be <= year_end ({year_end})")

    if tmf_type == "CHG":
        start = mosaic.select([f"Dec{year_start}"]).rename("cls")
        end = mosaic.select([f"Dec{year_end}"]).rename("cls")
        combo = start.multiply(10).add(end).toInt()
        return (
            combo.remap(
                list(TMF_CHG_TRANSITION_REMAP),
                list(TMF_CHG_TRANSITION_REMAP.values()),
                7,  # default: "Other change"
            )
            .rename("transition")
            .toInt()
        )

    mask = mosaic.lte(ee.Number(year_end)).And(mosaic.gte(ee.Number(year_start))).selfMask()
    return mosaic.mask(mask)


def viz_params_for(tmf_type: str, year_start: int, year_end: int) -> dict:
    """Return the map visualization params for the given layer type."""
    if tmf_type in ("DEG", "DEF"):
        return year_viz_params(year_start, year_end)
    if tmf_type == "CHG":
        return change_viz_params()
    if tmf_type == "TRANS":
        return transition_main_viz_params()
    raise ValueError(f"Unknown TMF type: {tmf_type!r}")
