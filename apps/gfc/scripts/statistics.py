"""Server-side area statistics for GFC classification."""

import ee

from apps.gfc.params import GFC_MAX_YEAR


def compute_area_stats(
    gfc_image: ee.Image,
    aoi: ee.FeatureCollection,
    scale: int = 30,
) -> dict:
    """Compute area in hectares per class using server-side reduction.

    Args:
        gfc_image: Classified GFC image from classify_gfc().
        aoi: Area of interest.
        scale: Reduction scale in meters.

    Returns:
        dict with 'code', 'class', 'area' lists ready for tabular display.
    """
    area_image = ee.Image.pixelArea().divide(10000).addBands(gfc_image)

    result = area_image.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1),
        geometry=aoi.geometry(),
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    )

    return result


def parse_area_stats(raw_result: dict) -> list[dict]:
    """Parse reduceRegion grouped result into a list of dicts.

    Args:
        raw_result: Raw result from compute_area_stats().getInfo().

    Returns:
        List of dicts with keys: code, label, area_ha.
    """
    groups = raw_result.get("groups", [])
    rows = []
    for g in groups:
        code = int(g["group"])
        area = g["sum"]
        rows.append({"code": code, "label": _code_to_label(code), "area_ha": round(area, 2)})
    return sorted(rows, key=lambda r: r["code"])


def _code_to_label(code: int) -> str:
    if 1 <= code <= GFC_MAX_YEAR:
        return f"loss {2000 + code}"
    return {30: "non forest", 40: "forest", 50: "gains", 51: "gain + loss"}.get(
        code, f"unknown ({code})"
    )
