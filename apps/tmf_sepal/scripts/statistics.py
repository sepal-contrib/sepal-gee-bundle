"""Server-side area statistics for JRC TMF layers.

For DEG / DEF, pixels hold the year of the disturbance event: we group the
area by year and the resulting rows are keyed by year (e.g. 2005).

For CHG, the image holds a single ``transition`` band with the start->end
transition class codes 1..7 (see ``TMF_CHG_TRANSITION_CLASSES``); we compute
area per transition class.
"""

from __future__ import annotations

import ee

from apps.tmf_sepal.params import TMF_CHG_TRANSITION_CLASSES


def _group_by_class_image(stats_image: ee.Image) -> ee.Image:
    """Area-in-ha image with a second band holding the class/year code."""
    return ee.Image.pixelArea().divide(10000).addBands(stats_image)


def compute_area_stats(
    tmf_image: ee.Image,
    aoi: ee.FeatureCollection,
    tmf_type: str,
    year_end: int,
    scale: int = 30,
) -> dict:
    """Server-side area (ha) per class for the given TMF layer.

    The image is single-band for every type — the year-of-event band for
    ``DEG`` / ``DEF``, the ``transition`` class band for ``CHG`` — so we group
    area by that band's value. ``tmf_type`` / ``year_end`` are retained for
    call-site compatibility.
    """
    stats_band = tmf_image.rename("class").toInt()

    area_image = _group_by_class_image(stats_band)

    return area_image.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1),
        geometry=aoi.geometry(),
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    )


# Lookup tables for CHG ------------------------------------------------------
_CHG_LABEL_BY_CODE = {code: label for code, label, _color in TMF_CHG_TRANSITION_CLASSES}
_CHG_COLOR_BY_CODE = {code: color for code, _label, color in TMF_CHG_TRANSITION_CLASSES}


def parse_area_stats(raw_result: dict, tmf_type: str) -> list[dict]:
    """Parse a grouped ``reduceRegion`` result into table rows.

    Returns rows with keys: ``code``, ``label``, ``color``, ``area_ha``.
    Rows with non-positive area are dropped. For ``CHG``, unknown codes are
    preserved but shown as ``unknown (<code>)`` without a palette color.
    """
    rows: list[dict] = []
    for g in raw_result.get("groups", []) or []:
        code_val = g.get("group")
        if code_val is None:
            continue
        try:
            code = int(code_val)
        except (TypeError, ValueError):
            continue
        area = float(g.get("sum", 0.0) or 0.0)
        if area <= 0:
            continue
        label, color = _label_and_color(code, tmf_type)
        rows.append({"code": code, "label": label, "color": color, "area_ha": round(area, 2)})
    rows.sort(key=lambda r: r["code"])
    return rows


def _label_and_color(code: int, tmf_type: str) -> tuple[str, str | None]:
    if tmf_type == "CHG":
        return (
            _CHG_LABEL_BY_CODE.get(code, f"unknown ({code})"),
            _CHG_COLOR_BY_CODE.get(code),
        )
    # DEG / DEF: the code is the year of the event
    return (str(code), None)
