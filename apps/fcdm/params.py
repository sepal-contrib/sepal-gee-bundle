"""FCDM dataset constants, sensor band maps, forest mask sources, and viz params."""

from datetime import datetime as _dt

from apps._commons.datasets import (
    HANSEN_GFC_ID,
    JRC_TMF_ANNUAL_CHANGES_ID,
    LANDSAT_PLATFORMS,
    SENTINEL_2_SR_ID,
    SENTINEL_2_TOA_ID,
)

# --- Datasets ---
HANSEN_GFC = HANSEN_GFC_ID
JRC_ROADLESS = JRC_TMF_ANNUAL_CHANGES_ID

# --- Sensors ---
# Asset ids and the Landsat band layouts come from `apps._commons.datasets`.
# The `cloud` band name is a synthetic property added by simpleCloudScore on
# the TOA join, so it is not part of the Landsat schema in the registry.

_SENTINEL_2_BANDS = {
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
}


def _landsat_entry(short: str) -> dict:
    p = LANDSAT_PLATFORMS[short]
    end = p.end_year if p.end_year is not None else _dt.now().year
    bands = {
        **p.bands,
        "cloud": "cloud",  # synthetic band from simpleCloudScore TOA join
        "bright_temp1": p.bands["thermal"],
    }
    return {
        "start": p.start_year,
        "end": end,
        "dataset": {"toa": p.toa, "sr": p.sr},
        "bands": bands,
        "res": 30,
    }


SENSORS: dict = {
    f"landsat {p.short[1:]}": _landsat_entry(p.short) for p in LANDSAT_PLATFORMS.values()
}
SENSORS["sentinel 2"] = {
    "start": 2015,
    "end": _dt.now().year,
    "dataset": {"toa": SENTINEL_2_TOA_ID, "sr": SENTINEL_2_SR_ID},
    "bands": _SENTINEL_2_BANDS,
    "res": 10,
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
FOREST_MAP_MAX_YEAR = 2024

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


def delta_rnbr_legend():
    """Return LegendData for the Delta-rNBR map layer (gradient + forest mask)."""
    from dataclasses import asdict

    from pysepal.solara.components.legend import (
        DiscreteEntry,
        GradientEntry,
        LegendData,
    )

    return asdict(
        LegendData(
            gradients=[
                GradientEntry(
                    title="Delta-rNBR",
                    colors=DELTA_NBR_VIS["palette"],
                    labels=[str(DELTA_NBR_VIS["min"]), str(DELTA_NBR_VIS["max"])],
                )
            ],
            items=[DiscreteEntry(label="Forest mask", color="#006600")],
        )
    )


# Layer name constants (used by components to manage map state)
LAYER_AOI = "AOI"
LAYER_FOREST_MASK = "Forest mask"
LAYER_REFERENCE_RNBR = "Reference rNBR"
LAYER_ANALYSIS_RNBR = "Analysis rNBR"
LAYER_DELTA_RNBR = "Delta-rNBR"
