"""Quegan multi-temporal speckle filter — ported verbatim from legacy.

Reference: legacy ``component/scripts/_quegan.py``.
"""

from __future__ import annotations

import ee


def apply(images: ee.ImageCollection, options: dict) -> ee.ImageCollection:
    """Apply the Quegan multi-temporal filter to an ALOS collection.

    Args:
        images: ImageCollection of ALOS PALSAR backscatter images.
        options: dict with ``radius`` and ``units`` keys for the spatial kernel.

    Returns:
        The filtered ImageCollection — original bands replaced by the filtered
        versions.
    """
    bands = images.first().bandNames()
    mean_band = bands.map(lambda b: ee.String(b).cat("_mean"))
    ratio_band = bands.map(lambda b: ee.String(b).cat("_ratio"))

    def map_mean_space(image: ee.Image) -> ee.Image:
        reducer = ee.Reducer.mean()
        kernel = ee.Kernel.square(options["radius"], options["units"])
        mean = image.reduceNeighborhood(reducer, kernel).rename(mean_band)
        ratio = image.divide(mean).rename(ratio_band)
        return image.addBands(mean).addBands(ratio).copyProperties(image)

    mean_space = images.map(map_mean_space)

    def mt_despeck_single(image: ee.Image) -> ee.Image:
        mean_space2 = ee.ImageCollection(mean_space).select(ratio_band)
        b = image.select(mean_band)
        filtered = (
            b.multiply(mean_space2.sum())
            .divide(mean_space2.count())
            .rename(bands)
            .select(["HH", "HV"])
        )
        return image.addBands(filtered, None, True).select(bands)

    return mean_space.map(mt_despeck_single)
