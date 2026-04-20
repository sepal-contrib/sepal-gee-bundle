"""GFC forest change classification (Basin Rivers copy — no cross-app imports)."""

import ee

from apps.basin_rivers.params import GFC_DATASET


def classify_gfc(
    aoi: ee.FeatureCollection,
    threshold: int,
    start_year: int,
    end_year: int,
    dataset_id: str = GFC_DATASET,
) -> ee.Image:
    """Classify pixels into forest change categories.

    Returns ee.Image with values: 1-24 (loss year), 30 (non-forest),
    40 (stable forest), 50 (gain), 51 (gain+loss).
    """
    start = start_year - 2000
    end = end_year - 2000

    gfc = ee.Image(dataset_id).clip(aoi)
    treecov = gfc.select("treecover2000")
    lossy = gfc.select("lossyear").unmask(0)
    gain = gfc.select("gain")

    classified = (
        ee.Image(0)
        .where(treecov.lte(threshold).And(gain.eq(0)), 30)
        .where(treecov.lte(threshold).And(gain.eq(1)), 50)
        .where(treecov.gt(threshold).And(lossy.lt(start)).And(lossy.gt(0)), 30)
        .where(treecov.gt(threshold).And(lossy.gt(end)), 40)
        .where(
            treecov.gt(threshold).And(gain.eq(1)).And(lossy.gte(start)).And(lossy.lte(end)),
            51,
        )
        .where(treecov.gt(threshold).And(gain.eq(1)).And(lossy.eq(0)), 50)
        .where(
            treecov.gt(threshold).And(gain.eq(0)).And(lossy.gte(start)).And(lossy.lte(end)),
            lossy,
        )
        .where(treecov.gt(threshold).And(gain.eq(0)).And(lossy.eq(0)), 40)
        .selfMask()
    )

    return classified.uint8()
