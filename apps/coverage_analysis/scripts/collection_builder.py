"""Build a merged, cloud-masked, NDVI-augmented image collection.

Consolidates the legacy ``bfast_preanalysis.analysis`` + ``helpers.create_collection``
into a single entry point that handles:

- Landsat 4/5/7/8 C02 (SR via L2, TOA via T1_TOA), with optional Tier 2 merge.
- Sentinel-2 (SR or TOA, harmonized) joined with s2cloudless probability.
- Per-sensor cloud masking.
- Per-sensor NDVI addition with a common band name ``NDVI``.
- A common ``count_band`` renamed to ``COUNT`` so downstream reducers can
  operate on one band regardless of sensor.
"""

from __future__ import annotations

import ee

from apps.coverage_analysis.params import (
    COUNT_BAND_SR,
    COUNT_BAND_TOA,
    LANDSAT_C02_SR,
    LANDSAT_C02_TOA,
    NDVI_BANDS_SR,
    NDVI_BANDS_TOA,
    S2_CLOUD_PROB_ID,
    S2_SR_ID,
    S2_TOA_ID,
)
from apps.coverage_analysis.scripts.cloud_masking import (
    mask_landsat_c02,
    mask_s2_full,
    mask_s2_simple,
)

LANDSAT_SENSORS = ("l4", "l5", "l7", "l8")


def _landsat_id(sensor: str, sr: bool) -> str:
    if sr:
        return LANDSAT_C02_SR[sensor]
    return LANDSAT_C02_TOA[sensor]


def _t2_id(t1_id: str) -> str:
    """Derive the Tier 2 equivalent of a C02 T1 asset id."""
    return t1_id.replace("/T1_", "/T2_")


def _add_ndvi(sensor: str, sr: bool):
    nir, red = (NDVI_BANDS_SR if sr else NDVI_BANDS_TOA)[sensor]

    def _fn(img: ee.Image) -> ee.Image:
        return img.addBands(img.normalizedDifference([nir, red]).rename("NDVI"))

    return _fn


def _add_count_band(sensor: str, sr: bool):
    band = (COUNT_BAND_SR if sr else COUNT_BAND_TOA)[sensor]

    def _fn(img: ee.Image) -> ee.Image:
        return img.addBands(img.select(band).rename("COUNT"))

    return _fn


def _build_landsat(
    sensor: str,
    aoi,
    start: str,
    end: str,
    sr: bool,
    include_t2: bool,
) -> ee.ImageCollection:
    asset_id = _landsat_id(sensor, sr)
    coll = ee.ImageCollection(asset_id).filterBounds(aoi).filterDate(start, end)

    if include_t2:
        t2 = ee.ImageCollection(_t2_id(asset_id)).filterBounds(aoi).filterDate(start, end)
        coll = coll.merge(t2)

    coll = coll.map(mask_landsat_c02)
    coll = coll.map(_add_ndvi(sensor, sr))
    coll = coll.map(_add_count_band(sensor, sr))
    return coll


def _build_s2(
    aoi,
    start: str,
    end: str,
    sr: bool,
) -> ee.ImageCollection:
    primary_id = S2_SR_ID if sr else S2_TOA_ID

    primary = ee.ImageCollection(primary_id).filterBounds(aoi).filterDate(start, end)
    cloudless = ee.ImageCollection(S2_CLOUD_PROB_ID).filterBounds(aoi).filterDate(start, end)

    joined = ee.ImageCollection(
        ee.Join.saveFirst("s2cloudless").apply(
            primary=primary,
            secondary=cloudless,
            condition=ee.Filter.equals(
                leftField="system:index",
                rightField="system:index",
            ),
        )
    )

    # Full shadow-aware masking when SR (SCL available), simple otherwise.
    coll = joined.map(mask_s2_full if sr else mask_s2_simple)
    coll = coll.map(_add_ndvi("s2", sr))
    coll = coll.map(_add_count_band("s2", sr))
    return coll


def build_collection(
    aoi,
    start: str,
    end: str,
    sensors: list[str] | tuple[str, ...],
    sr: bool,
    include_t2: bool = False,
) -> ee.ImageCollection | None:
    """Build a merged multi-sensor ``ee.ImageCollection`` with NDVI + COUNT bands.

    Args:
        aoi: ``ee.FeatureCollection`` or ``ee.Geometry`` of the AOI.
        start: Inclusive start date ``YYYY-MM-DD``.
        end: Exclusive end date ``YYYY-MM-DD``.
        sensors: Iterable of sensor codes from ``{l4, l5, l7, l8, s2}``.
        sr: ``True`` for Surface Reflectance, ``False`` for TOA.
        include_t2: Merge Tier 2 Landsat data (ignored for S2).

    Returns:
        A merged ``ee.ImageCollection`` with at least bands ``NDVI`` and
        ``COUNT``; or ``None`` if ``sensors`` is empty.
    """
    sensors = list(sensors or [])
    if not sensors:
        return None

    merged: ee.ImageCollection | None = None

    for sensor in LANDSAT_SENSORS:
        if sensor not in sensors:
            continue
        coll = _build_landsat(sensor, aoi, start, end, sr, include_t2)
        merged = coll if merged is None else merged.merge(coll)

    if "s2" in sensors:
        coll = _build_s2(aoi, start, end, sr)
        merged = coll if merged is None else merged.merge(coll)

    return merged


def build_asset_name(
    aoi_name: str,
    start: str,
    end: str,
    sensors: list[str] | tuple[str, ...],
    sr: bool,
) -> str:
    """Standard asset / file name for exports."""
    safe_aoi = (aoi_name or "aoi").replace(" ", "_")
    parts = [f"coverage_{safe_aoi}_{start}_{end}"]
    for sensor in LANDSAT_SENSORS:
        if sensor in sensors:
            parts.append(sensor.upper())
    if "s2" in sensors:
        parts.append("S2")
    parts.append("SR" if sr else "TOA")
    return "_".join(parts)
