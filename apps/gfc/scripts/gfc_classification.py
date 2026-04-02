"""GFC forest change classification using Hansen Global Forest Change dataset."""

import ee

from apps.gfc.params import GFC_DATASET


def classify_gfc(
    aoi: ee.FeatureCollection,
    threshold: int,
    start_year: int,
    end_year: int,
    dataset_id: str = GFC_DATASET,
) -> ee.Image:
    """Classify pixels into forest change categories.

    Args:
        aoi: Area of interest as ee.FeatureCollection.
        threshold: Tree cover percentage threshold (0-100).
        start_year: Start year for loss analysis (e.g. 2001).
        end_year: End year for loss analysis (e.g. 2024).
        dataset_id: GFC dataset asset ID.

    Returns:
        Classified ee.Image with values:
            1-24: loss year (year - 2000)
            30: non-forest
            40: stable forest
            50: gain
            51: gain + loss
    """
    start = start_year - 2000
    end = end_year - 2000

    gfc = ee.Image(dataset_id).clip(aoi)

    treecov = gfc.select("treecover2000")
    lossy = gfc.select("lossyear").unmask(0)
    gain = gfc.select("gain")

    classified = (
        ee.Image(0)
        # Non-forest: low tree cover, no gain
        .where(treecov.lte(threshold).And(gain.eq(0)), 30)
        # Gain on non-forest
        .where(treecov.lte(threshold).And(gain.eq(1)), 50)
        # Non-forest: tree cover was high but lost before start year
        .where(treecov.gt(threshold).And(lossy.lt(start)).And(lossy.gt(0)), 30)
        # Stable forest: tree cover high, loss after end year (future loss)
        .where(treecov.gt(threshold).And(lossy.gt(end)), 40)
        # Gain + loss within period
        .where(
            treecov.gt(threshold).And(gain.eq(1)).And(lossy.gte(start)).And(lossy.lte(end)),
            51,
        )
        # Gain only: high tree cover, gain, no loss
        .where(treecov.gt(threshold).And(gain.eq(1)).And(lossy.eq(0)), 50)
        # Loss within period: encoded as loss year
        .where(
            treecov.gt(threshold).And(gain.eq(0)).And(lossy.gte(start)).And(lossy.lte(end)),
            lossy,
        )
        # Stable forest: high tree cover, no loss, no gain
        .where(treecov.gt(threshold).And(gain.eq(0)).And(lossy.eq(0)), 40)
        .selfMask()
    )

    return classified.uint8()
