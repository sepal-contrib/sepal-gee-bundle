"""Forest mask construction for FCDM.

Pure GEE helpers. No UI, no global state.
"""

from __future__ import annotations

import ee

from apps.fcdm.params import HANSEN_GFC, JRC_ROADLESS


def get_forest_mask(
    forest_map: str,
    year: int,
    treecover: int,
    aoi,
) -> tuple[ee.Image, ee.Image]:
    """Return (forest_mask, forest_mask_display) for the given source.

    Args:
        forest_map: one of "gfc", "roadless", "no_map", or an asset id.
        year: baseline year for the forest mask.
        treecover: GFC tree-cover threshold (%) — used only if forest_map == "gfc".
        aoi: ee.FeatureCollection or ee.Geometry.

    Returns:
        (forest_mask, forest_mask_display) where forest_mask is the binary (or
        coded, for roadless) image used by the pipeline, and forest_mask_display
        is the same image prepared for display on the map.
    """
    hansen = ee.Image(HANSEN_GFC).clip(aoi)

    if forest_map == "no_map":
        forest_mask = hansen.select("treecover2000").gte(0)
        forest_mask_display = forest_mask.updateMask(forest_mask)

    elif forest_map == "roadless":
        forest_mask = ee.ImageCollection(JRC_ROADLESS).mosaic().byte().clip(aoi)
        band = f"Dec{year + 1}"
        forest_mask_display = forest_mask.updateMask(forest_mask).select(band)

    elif forest_map == "gfc":
        basemap2000 = hansen.unmask(0).select("treecover2000").gte(treecover)
        loss_year = hansen.unmask(0).select("lossyear")
        change = loss_year.lte(year - 2000).And(loss_year.gt(0)).bitwiseNot()
        forest_mask = basemap2000.multiply(change)
        forest_mask_display = forest_mask.select(0).mask(forest_mask)

    else:
        # Custom asset id — expected binary 0/1
        forest_mask = ee.Image(forest_map).select(0)
        forest_mask_display = forest_mask.updateMask(forest_mask)

    return forest_mask, forest_mask_display
