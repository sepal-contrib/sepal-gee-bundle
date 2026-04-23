"""Cloud and shadow masking for Landsat C02 and Sentinel-2.

Landsat C02 (both L2/SR and T1_TOA) exposes the ``QA_PIXEL`` band with bit
flags; we use bit 3 (cloud shadow) and bit 4 (cloud). Sentinel-2 uses the
s2cloudless probability collection joined on ``system:index``.
"""

from __future__ import annotations

import ee

from apps.coverage_analysis.params import (
    S2_CLOUD_PROB_THRESH,
    S2_CLOUD_PROJ_DIST,
    S2_NIR_DARK_THRESH,
    S2_SHADOW_BUFFER,
)


def _bitwise_extract(value: ee.Image, from_bit: int, to_bit: int | None = None) -> ee.Image:
    if to_bit is None:
        to_bit = from_bit
    mask_size = ee.Number(1).add(to_bit).subtract(from_bit)
    mask = ee.Number(1).leftShift(mask_size).subtract(1)
    return value.rightShift(from_bit).bitwiseAnd(mask)


def mask_landsat_c02(image: ee.Image) -> ee.Image:
    """Mask clouds and cloud shadow using Landsat C02 QA_PIXEL bit flags.

    QA_PIXEL bit 3 = cloud shadow, bit 4 = cloud. Works for both L2 (SR)
    and T1_TOA collections in Collection 2.
    """
    qa = image.select("QA_PIXEL")
    cloud = _bitwise_extract(qa, 4).eq(0)
    shadow = _bitwise_extract(qa, 3).eq(0)
    return image.updateMask(cloud).updateMask(shadow)


def mask_s2_simple(image: ee.Image) -> ee.Image:
    """Mask S2 clouds using s2cloudless probability threshold only."""
    cld_prb = ee.Image(image.get("s2cloudless")).select("probability")
    is_not_cloud = cld_prb.lt(S2_CLOUD_PROB_THRESH).rename("clouds")
    return image.updateMask(is_not_cloud)


def mask_s2_full(image: ee.Image) -> ee.Image:
    """Mask S2 clouds and projected shadows via directional distance transform.

    Requires the SCL band (only present in SR). Falls back to ``mask_s2_simple``
    if SCL is missing.
    """
    band_names = image.bandNames()
    has_scl = band_names.contains("SCL")

    # Simple masking (always available).
    cld_prb = ee.Image(image.get("s2cloudless")).select("probability")
    is_cloud = cld_prb.gt(S2_CLOUD_PROB_THRESH).rename("clouds")

    def _with_shadow(img: ee.Image) -> ee.Image:
        not_water = img.select("SCL").neq(6)

        sr_band_scale = 1e4
        dark_pixels = (
            img.select("B8")
            .lt(S2_NIR_DARK_THRESH * sr_band_scale)
            .multiply(not_water)
            .rename("dark_pixels")
        )

        shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get("MEAN_SOLAR_AZIMUTH_ANGLE")))

        cld_proj = (
            is_cloud.directionalDistanceTransform(shadow_azimuth, S2_CLOUD_PROJ_DIST * 10)
            .reproject(crs=img.select(0).projection(), scale=100)
            .select("distance")
            .mask()
            .rename("cloud_transform")
        )

        shadows = cld_proj.multiply(dark_pixels).rename("shadows")
        is_cld_shdw = is_cloud.add(shadows).gt(0)

        is_cld_shdw = (
            is_cld_shdw.focal_min(2)
            .focal_max(S2_SHADOW_BUFFER * 2 / 20)
            .reproject(crs=img.select(0).projection(), scale=20)
            .rename("cloudmask")
        )
        return img.updateMask(is_cld_shdw.unmask(0).neq(1))

    return ee.Image(
        ee.Algorithms.If(has_scl, _with_shadow(image), image.updateMask(is_cloud.Not()))
    )
