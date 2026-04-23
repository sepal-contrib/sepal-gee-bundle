"""Collection assembly for FCDM.

Builds a cloud- and forest-masked ImageCollection ready for NBR computation.
"""

from __future__ import annotations

from functools import partial

import ee

from apps.fcdm.params import SENSORS
from apps.fcdm.scripts.cloud_masking import CLOUD_MASKERS, masking_sensor_errors


def _join_landsat_collections(
    sr_coll: ee.ImageCollection, toa_coll: ee.ImageCollection
) -> ee.ImageCollection:
    """Join SR and TOA collections on system:index to keep simpleCloudScore band."""
    eqfilter = ee.Filter.equals(rightField="system:index", leftField="system:index")
    join = ee.ImageCollection(ee.Join.inner().apply(sr_coll, toa_coll, eqfilter))
    joined = join.map(lambda el: ee.Image.cat(el.get("primary"), el.get("secondary")))
    return joined.sort("system:time_start")


def build_collection(
    sensor: str,
    start: str,
    end: str,
    forest_map: str,
    year: int,
    forest_mask: ee.Image,
    cloud_buffer: float,
    aoi,
) -> ee.ImageCollection:
    """Build a cloud/sensor/forest-masked ImageCollection for the given sensor.

    Args:
        sensor: one of the keys in params.SENSORS.
        start: ISO start date (YYYY-MM-DD).
        end: ISO end date (YYYY-MM-DD).
        forest_map: "gfc" | "roadless" | "no_map" | asset id.
        year: forest mask baseline year.
        forest_mask: ee.Image returned by get_forest_mask().
        cloud_buffer: buffer around cloud pixels (meters), 0 to disable.
        aoi: ee.FeatureCollection or geometry.

    Returns:
        ee.ImageCollection.
    """
    sensor_cfg = SENSORS[sensor]
    sr_collection = (
        ee.ImageCollection(sensor_cfg["dataset"]["sr"]).filterDate(start, end).filterBounds(aoi)
    )

    if "landsat" in sensor:
        toa_collection = (
            ee.ImageCollection(sensor_cfg["dataset"]["toa"])
            .filterDate(start, end)
            .filterBounds(aoi)
            .map(ee.Algorithms.Landsat.simpleCloudScore)
            .select("cloud")
        )
        merged = _join_landsat_collections(sr_collection, toa_collection)
    else:
        merged = sr_collection

    # mask sensor errors / non-forest
    masked = merged.map(
        partial(
            masking_sensor_errors,
            forest_mask=forest_mask,
            year=year,
            forest_map=forest_map,
            sensor=sensor,
        )
    )
    # cloud masking
    cloud_masker = CLOUD_MASKERS[sensor]
    masked = masked.map(partial(cloud_masker, cloud_buffer=cloud_buffer, sensor=sensor))
    return masked
