"""Cloud masking helpers for FCDM.

Sensor-specific cloud masking functions. Adapted from the legacy FCDM
`process_scripts.py` (Copyright: Dario Simonetti, JRC) and ported to Landsat
Collection 2. All functions are pure (image -> image) and take the sensor key.
"""

from __future__ import annotations

import ee

from apps.fcdm.params import SENSORS

# ---------------------------------------------------------------------------
# Landsat C02 QA_PIXEL bit mask helpers
# ---------------------------------------------------------------------------
# Landsat C02 QA_PIXEL bits:
#   bit 1 = dilated cloud
#   bit 2 = cirrus
#   bit 3 = cloud
#   bit 4 = cloud shadow
#   bit 5 = snow
#   bit 6 = clear  (0 = cloud/shadow/snow, 1 = clear)

_L_C02_CLOUD_BITS = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4)


def _apply_buffer(mask: ee.Image, cloud_buffer: float) -> ee.Image:
    if cloud_buffer:
        return mask.focal_max(cloud_buffer, "circle", "meters", 1)
    return mask


def masking_landsat(image: ee.Image, cloud_buffer: float, sensor: str) -> ee.Image:
    """Mask clouds / shadows for any Landsat sensor using QA_PIXEL (C02)."""
    bands = SENSORS[sensor]["bands"]
    pixel_qa = image.select(bands["pixel_qa"])
    nir = image.select(bands["nir"])
    swir2 = image.select(bands["swir2"])

    no_data = nir.eq(0).And(swir2.eq(0))
    qa_cloud = pixel_qa.bitwiseAnd(_L_C02_CLOUD_BITS).neq(0)

    # Optional supplementary simpleCloudScore band ("cloud") joined from TOA.
    try:
        cloud = image.select("cloud")
        qa_cloud = qa_cloud.Or(cloud.gte(13))
    except Exception:
        pass

    masked = no_data.Or(qa_cloud)
    masked = _apply_buffer(masked, cloud_buffer)
    return image.updateMask(masked.add(1).unmask(0).eq(1))


def masking_sentinel2_sr(image: ee.Image, cloud_buffer: float, sensor: str) -> ee.Image:
    """Sentinel-2 L2A cloud mask using SCL band."""
    scl = image.select(SENSORS[sensor]["bands"]["scl"])
    clouds = scl.eq(7).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10))
    shadows = scl.eq(3)
    water = scl.eq(6)
    masked = clouds.Or(shadows).Or(water)
    masked = _apply_buffer(masked, cloud_buffer)
    return image.updateMask(masked.add(1).unmask(255).eq(1))


def iforce_pino_step1(
    image: ee.Image,
    apply_buffer: bool,
    cloud_buffer: float,
) -> ee.Image:
    """Sentinel-2 L1C cloud masking (Dario Simonetti, JRC) — preserved verbatim.

    Applies a growing-vegetation exemption to the simple ESA QA60 + aerosol mask.
    """
    bands = SENSORS["sentinel 2"]["bands"]
    blue = image.select(bands["blue"])
    green = image.select(bands["green"])
    red = image.select(bands["red"])
    red_edge_3 = image.select(bands["red_edge_3"])
    red_edge_4 = image.select(bands["red_edge_4"])
    swir1 = image.select(bands["swir1"])
    aerosol = image.select(bands["aerosol"])
    red_edge_2 = image.select(bands["red_edge_2"])
    qa60 = image.select(bands["qa60"])
    water_vapor = image.select(bands["water_vapor"])

    growing111 = (
        blue.lte(green.add(blue.multiply(0.05)))
        .And(green.lte(red.add(green.multiply(0.05))))
        .And(red.lte(red_edge_3.add(red.multiply(0.05))))
        .And(red_edge_3.lte(red_edge_4.add(red_edge_3.multiply(0.05))))
        .And(red_edge_4.lte(swir1.add(red_edge_4.multiply(0.05))))
        .And(swir1.lt(1500))
    )
    growing28 = (
        blue.lte(green)
        .lte(red)
        .lte(red_edge_2)
        .lte(red_edge_3)
        .lte(red_edge_4)
        .And(swir1.gte(red_edge_2))
        .And(aerosol.lt(1500))
    )
    esa_mask = qa60.eq(2048).And(blue.gt(0.12)).And(aerosol.gt(1800))
    cloud_mask = (
        aerosol.gt(2000)
        .Or(aerosol.gt(1340).And(water_vapor.gt(300)))
        .Or(aerosol.gt(1750).And(water_vapor.gt(230)))
        .Or(esa_mask)
    )
    if apply_buffer:
        cloud_mask = cloud_mask.focal_max(cloud_buffer, "circle", "meters", 1)
    cloud_mask = cloud_mask.where(growing111.Or(growing28), 0)
    return image.updateMask(cloud_mask.eq(0))


# Registry: sensor -> cloud masking function
CLOUD_MASKERS = {
    "landsat 4": masking_landsat,
    "landsat 5": masking_landsat,
    "landsat 7": masking_landsat,
    "landsat 8": masking_landsat,
    "landsat 9": masking_landsat,
    "sentinel 2": masking_sentinel2_sr,
}


def masking_sensor_errors(
    image: ee.Image,
    forest_mask: ee.Image,
    year: int,
    forest_map: str,
    sensor: str,
) -> ee.Image:
    """Mask sensor errors and non-forest areas."""
    bands = SENSORS[sensor]["bands"]
    nir = image.select(bands["nir"])
    swir2 = image.select(bands["swir2"])
    blue = image.select(bands["blue"])
    green = image.select(bands["green"])
    red = image.select(bands["red"])
    swir1 = image.select(bands["swir1"])

    sensor_error = (
        nir.lte(0)
        .Or(swir2.lte(0))
        .Or(blue.lte(0))
        .Or(green.lte(0))
        .Or(red.lte(0))
        .Or(swir1.lte(0))
        .add(1)
        .unmask(0)
    )
    sensor_error_buffer = sensor_error.focal_min(
        radius=50, kernelType="circle", units="meters", iterations=1
    )
    image = image.unmask(0)

    if forest_map == "no_map":
        return image.updateMask(sensor_error_buffer.eq(1).And(forest_mask.eq(1)))
    if forest_map == "roadless":
        band = f"Dec{year + 1}"
        valid = (
            forest_mask.select(band)
            .eq(1)
            .Or(forest_mask.select(band).eq(2))
            .Or(forest_mask.select(band).eq(13))
            .Or(forest_mask.select(band).eq(14))
        )
        return image.updateMask(sensor_error_buffer.eq(1)).updateMask(valid)
    # "gfc" or custom asset -> treat as binary forest mask
    return image.updateMask(sensor_error_buffer.eq(1)).updateMask(forest_mask)
