"""Coverage Analysis dataset IDs, defaults, palettes, and option lists.

All Landsat collections migrated from C01 (deprecated) to C02. Surface
Reflectance uses Level 2 (``T1_L2``) and TOA uses the C02 T1 collections.
"""

from __future__ import annotations

from apps._commons.datasets import (
    SENTINEL_2_CLOUD_PROBABILITY_ID,
    SENTINEL_2_SR_ID,
    SENTINEL_2_TOA_ID,
    landsat_c02_sr,
    landsat_c02_toa,
)

# --- Sensor options (UI) ---
SENSOR_ITEMS: list[dict] = [
    {"text": "Landsat 9", "value": "l9"},
    {"text": "Landsat 8", "value": "l8"},
    {"text": "Landsat 7", "value": "l7"},
    {"text": "Landsat 5", "value": "l5"},
    {"text": "Landsat 4", "value": "l4"},
    {"text": "Sentinel 2", "value": "s2"},
]

# --- Measure options (UI) ---
MEASURE_ITEMS: list[dict] = [
    {"text": "Cloud-free pixel count", "value": "pixel_count"},
    {"text": "Total pixel count (scene coverage)", "value": "pixel_count_all"},
    {"text": "NDVI Median", "value": "ndvi_median"},
    {"text": "NDVI Std. Dev.", "value": "ndvi_stdDev"},
]

# --- Export stats / temps ---
STATS_ITEMS: list[dict] = [
    {"text": "Count of cloud-free observations per pixel", "value": "count"},
    {"text": "NDVI median of cloud-free observations", "value": "ndvi_median"},
    {"text": "NDVI std. dev. of cloud-free observations", "value": "ndvi_stdDev"},
    {"text": "Count of all observations per pixel", "value": "all"},
]

TEMP_ITEMS: list[dict] = [
    {"text": "Full timespan (total)", "value": "total_exp"},
    {"text": "Annual", "value": "annual_exp"},
]

# --- Dataset IDs (C02) ---
# Landsat C02 ids come from the bundle-wide registry.  L9 inherits L8's band
# layout (OLI-2 + TIRS-2).
LANDSAT_C02_SR: dict[str, str] = landsat_c02_sr()
LANDSAT_C02_TOA: dict[str, str] = landsat_c02_toa()

# Sentinel-2
S2_SR_ID = SENTINEL_2_SR_ID
S2_TOA_ID = SENTINEL_2_TOA_ID
S2_CLOUD_PROB_ID = SENTINEL_2_CLOUD_PROBABILITY_ID

# Per-sensor NIR/Red band names to compute NDVI (depends on SR/TOA).
# For C02 L2, SR bands are prefixed with SR_B*.
NDVI_BANDS_SR: dict[str, tuple[str, str]] = {
    "l4": ("SR_B4", "SR_B3"),  # NIR, RED
    "l5": ("SR_B4", "SR_B3"),
    "l7": ("SR_B4", "SR_B3"),
    "l8": ("SR_B5", "SR_B4"),
    "l9": ("SR_B5", "SR_B4"),
    "s2": ("B8", "B4"),
}

NDVI_BANDS_TOA: dict[str, tuple[str, str]] = {
    "l4": ("B4", "B3"),
    "l5": ("B4", "B3"),
    "l7": ("B4", "B3"),
    "l8": ("B5", "B4"),
    "l9": ("B5", "B4"),
    "s2": ("B8", "B4"),
}

# "Green"/reference band used for counting observations (pixel_count).
COUNT_BAND_SR: dict[str, str] = {
    "l4": "SR_B2",
    "l5": "SR_B2",
    "l7": "SR_B2",
    "l8": "SR_B3",
    "l9": "SR_B3",
    "s2": "B3",
}

COUNT_BAND_TOA: dict[str, str] = {
    "l4": "B2",
    "l5": "B2",
    "l7": "B2",
    "l8": "B3",
    "l9": "B3",
    "s2": "B3",
}

# Cloud masking
S2_CLOUD_PROB_THRESH = 30
S2_NIR_DARK_THRESH = 0.15
S2_CLOUD_PROJ_DIST = 1
S2_SHADOW_BUFFER = 50

# --- Visualization palettes ---
VIS_NDVI_MEAN = {
    "min": 0,
    "max": 1,
    "palette": ["white", "brown", "orange", "lightgreen", "green", "darkgreen"],
}

VIS_NDVI_STDDEV = {
    "min": 0,
    "max": 1,
    "palette": ["white", "orange", "red", "brown"],
}

VIS_COUNT = {
    "min": 0,
    "max": 100,
    "palette": [
        "purple",
        "red",
        "orange",
        "white",
        "lightgreen",
        "green",
        "darkgreen",
    ],
}

# --- Defaults ---
DEFAULT_START = "2020-01-01"
DEFAULT_END = "2020-12-31"
DEFAULT_SCALE = 30
DEFAULT_MEASURE = "pixel_count"
