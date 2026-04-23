"""FCDM dataset constants, sensor band maps, forest mask sources, and viz params."""

from datetime import datetime as _dt

# --- Datasets ---
HANSEN_GFC = "UMD/hansen/global_forest_change_2024_v1_12"
JRC_ROADLESS = "projects/JRC/TMF/v1_2024/AnnualChanges"

# --- Sensors ---
# Migrated to Landsat C02. Sentinel-2 TOA is COPERNICUS/S2_HARMONIZED (same band names).
# Notes:
#   - L4/L5/L7 C02 SR band names differ from C01 (SR_B1..7, QA_PIXEL, ST_B6/ST_B10)
#   - The legacy algorithm relied on `pixel_qa`, `sr_cloud_qa`, `cloud` (from
#     simpleCloudScore) and `bright_temp1`. In C02 the equivalents are
#     `QA_PIXEL`, `SR_QA_AEROSOL` (no `sr_cloud_qa`), and thermal `ST_B6`/`ST_B10`.
#   - The pipeline has been simplified to the QA_PIXEL bit-mask scheme. The
#     `unsure_clouds` / `bright_temp1` branch is preserved for compatibility but
#     reads thermal from C02 names when available.

SENSORS = {
    "landsat 4": {
        "start": 1982,
        "end": 1993,
        "dataset": {
            "toa": "LANDSAT/LT04/C02/T1_TOA",
            "sr": "LANDSAT/LT04/C02/T1_L2",
        },
        "bands": {
            "blue": "SR_B1",
            "green": "SR_B2",
            "red": "SR_B3",
            "nir": "SR_B4",
            "swir1": "SR_B5",
            "swir2": "SR_B7",
            "pixel_qa": "QA_PIXEL",
            "cloud": "cloud",
            "bright_temp1": "ST_B6",
        },
        "res": 30,
    },
    "landsat 5": {
        "start": 1984,
        "end": 2013,
        "dataset": {
            "toa": "LANDSAT/LT05/C02/T1_TOA",
            "sr": "LANDSAT/LT05/C02/T1_L2",
        },
        "bands": {
            "blue": "SR_B1",
            "green": "SR_B2",
            "red": "SR_B3",
            "nir": "SR_B4",
            "swir1": "SR_B5",
            "swir2": "SR_B7",
            "pixel_qa": "QA_PIXEL",
            "cloud": "cloud",
            "bright_temp1": "ST_B6",
        },
        "res": 30,
    },
    "landsat 7": {
        "start": 1999,
        "end": _dt.now().year,
        "dataset": {
            "toa": "LANDSAT/LE07/C02/T1_TOA",
            "sr": "LANDSAT/LE07/C02/T1_L2",
        },
        "bands": {
            "blue": "SR_B1",
            "green": "SR_B2",
            "red": "SR_B3",
            "nir": "SR_B4",
            "swir1": "SR_B5",
            "swir2": "SR_B7",
            "pixel_qa": "QA_PIXEL",
            "cloud": "cloud",
            "bright_temp1": "ST_B6",
        },
        "res": 30,
    },
    "landsat 8": {
        "start": 2013,
        "end": _dt.now().year,
        "dataset": {
            "toa": "LANDSAT/LC08/C02/T1_TOA",
            "sr": "LANDSAT/LC08/C02/T1_L2",
        },
        "bands": {
            "blue": "SR_B2",
            "green": "SR_B3",
            "red": "SR_B4",
            "nir": "SR_B5",
            "swir1": "SR_B6",
            "swir2": "SR_B7",
            "pixel_qa": "QA_PIXEL",
            "cloud": "cloud",
            "bright_temp1": "ST_B10",
        },
        "res": 30,
    },
    "sentinel 2": {
        "start": 2015,
        "end": _dt.now().year,
        "dataset": {
            "toa": "COPERNICUS/S2_HARMONIZED",
            "sr": "COPERNICUS/S2_SR_HARMONIZED",
        },
        "bands": {
            "blue": "B2",
            "green": "B3",
            "red": "B4",
            "nir": "B8",
            "swir1": "B11",
            "swir2": "B12",
            "qa60": "QA60",
            "aerosol": "B1",
            "water_vapor": "B9",
            "red_edge_3": "B7",
            "red_edge_4": "B8A",
            "red_edge_2": "B6",
            "scl": "SCL",
        },
        "res": 10,
    },
}

SENSOR_ITEMS = [{"text": name, "value": name} for name in SENSORS]

# --- Forest mask ---
FOREST_MAP_ITEMS = [
    {"text": "Hansen GFC (tree cover)", "value": "gfc"},
    {"text": "JRC TMF Roadless", "value": "roadless"},
    {"text": "No forest mask", "value": "no_map"},
    {"text": "Custom GEE asset (binary 0/1)", "value": "custom"},
]

FOREST_MAP_MIN_YEAR = 2000
FOREST_MAP_MAX_YEAR = 2023

# --- Algorithm defaults & bounds ---
DEFAULT_TREECOVER = 70
DEFAULT_CLOUD_BUFFER = 500
DEFAULT_KERNEL_RADIUS = 150
DEFAULT_FILTER_THRESHOLD = 0.035
DEFAULT_FILTER_RADIUS = 80
DEFAULT_CLEANING_OFFSET = 3

MAX_KERNEL_RADIUS = 1000
MIN_FILTER_RADIUS = 10
MAX_FILTER_RADIUS = 500
MAX_CLEANING_OFFSET = 50


# --- Visualization ---
def viz_forest_mask(key: str) -> dict:
    """Return ee.Image.visualize() params for the chosen forest mask source."""
    mask = {
        "roadless": {
            "min": 1,
            "max": 15,
            "palette": [
                "#005000",
                "#336333",
                "#9b503c",
                "#87732d",
                "#648723",
                "#ff1400",
                "#ffff9b",
                "#98e600",
                "#32a000",
                "#ffffff",
                "#004da8",
                "#009dc8",
                "#005000",
                "#005000",
                "#ffffff",
            ],
        },
        "gfc": {"min": 0, "max": 1, "palette": ["#ffffcc", "#006600"]},
        "no_map": {"min": 0, "max": 1, "palette": ["#ffffcc", "#006600"]},
    }
    return mask.get(key, mask["gfc"])


# Delta-rNBR visualization (legacy: grey -> red across [0, 0.3])
DELTA_NBR_VIS = {"min": 0, "max": 0.3, "palette": ["#D3D3D3", "#Ce0f0f"]}

# Layer name constants (used by components to manage map state)
LAYER_AOI = "AOI"
LAYER_FOREST_MASK = "Forest mask"
LAYER_REFERENCE_RNBR = "Reference rNBR"
LAYER_ANALYSIS_RNBR = "Analysis rNBR"
LAYER_DELTA_RNBR = "Delta-rNBR"
