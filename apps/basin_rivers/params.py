"""Basin Rivers params.

Re-exports shared GFC primitives from apps._commons.gfc plus HydroSHEDS,
dashboard, and snake_case label conventions.
"""

from matplotlib import colors as mcolors

from apps._commons.datasets import HYDROSHEDS_BASINS_TEMPLATE
from apps._commons.gfc import (
    GFC_CLASSES,
    GFC_DATASET,
    GFC_LEGEND,
    GFC_MAX_YEAR,
    GFC_MIN_YEAR,
    HEX_PALETTE,
    SLD_INTERVALS,
)

# --- HydroSHEDS ---
HYBAS_DATASET_TEMPLATE = HYDROSHEDS_BASINS_TEMPLATE
HYBAS_LEVELS = list(range(5, 13))

# --- App-specific labels (snake_case, used as group keys in zonal stats) ---
GFC_LABELS = [f"loss_{2000 + i}" for i in range(1, GFC_MAX_YEAR + 1)] + [
    "non_forest",
    "forest",
    "gain",
    "gain_loss",
]

# Groups: all loss years → "loss", plus the fixed categories
GFC_GROUPS = ["loss"] * GFC_MAX_YEAR + ["non_forest", "forest", "gain", "gain_loss"]
GFC_TRANSLATION = dict(zip([*range(1, GFC_MAX_YEAR + 1), 30, 40, 50, 51], GFC_GROUPS))

GFC_COLORS_DICT = {
    "loss": mcolors.to_hex("darkred"),
    "non_forest": mcolors.to_hex("lightgrey"),
    "forest": mcolors.to_hex("darkgreen"),
    "gain": mcolors.to_hex("lightgreen"),
    "gain_loss": mcolors.to_hex("purple"),
}

LEGEND_DICT = dict(zip(GFC_LABELS, HEX_PALETTE))

# --- Display limits ---
MAX_CATCH_DISPLAY = 10
# If upstream delineation returns more than this, suggest a higher HydroSHEDS level
BASIN_WARN_THRESHOLD = 50

# --- Dashboard palette: blue / teal / cyan family (watersheds = water) ---
CATCH_COLOR_PALETTE = [
    "#0d47a1",  # deep blue
    "#1976d2",  # blue
    "#42a5f5",  # light blue
    "#01579b",  # navy
    "#006064",  # dark teal
    "#00838f",  # teal
    "#00acc1",  # cyan
    "#26c6da",  # light cyan
    "#80deea",  # aqua
    "#0277bd",  # ocean blue
    "#039be5",  # sky blue
    "#4fc3f7",  # pale sky
    "#81d4fa",  # very light blue
    "#3949ab",  # deep indigo
    "#5c6bc0",  # indigo
    "#1e88e5",  # bright blue
    "#00796b",  # dark teal-green
    "#009688",  # teal-green
    "#4db6ac",  # pale teal
    "#4dd0e1",  # pale cyan
]

# --- Dashboard labels + titles ---
VARIABLE_LABELS = {
    "all": "All classes",
    "forest": "Stable forest",
    "loss": "Forest loss",
    "gain": "Forest gain",
    "non_forest": "Non-forest",
    "gain_loss": "Gain + loss",
}

CATCH_PIE_TITLES = {
    "all": "Watershed area ratio",
    "forest": "Forest area by catchment",
    "loss": "Loss area by catchment",
    "gain": "Gain area by catchment",
    "non_forest": "Non-forest area by catchment",
    "gain_loss": "Gain+loss area by catchment",
}

CATCH_BAR_TITLES = {
    "all": "Total area per catchment",
    "forest": "Forest area per catchment",
    "loss": "Loss area by year",
    "gain": "Gain area per catchment",
    "non_forest": "Non-forest area per catchment",
    "gain_loss": "Gain+loss area per catchment",
}

__all__ = [
    "BASIN_WARN_THRESHOLD",
    "CATCH_BAR_TITLES",
    "CATCH_COLOR_PALETTE",
    "CATCH_PIE_TITLES",
    "GFC_CLASSES",
    "GFC_COLORS_DICT",
    "GFC_DATASET",
    "GFC_GROUPS",
    "GFC_LABELS",
    "GFC_LEGEND",
    "GFC_MAX_YEAR",
    "GFC_MIN_YEAR",
    "GFC_TRANSLATION",
    "HEX_PALETTE",
    "HYBAS_DATASET_TEMPLATE",
    "HYBAS_LEVELS",
    "LEGEND_DICT",
    "MAX_CATCH_DISPLAY",
    "SLD_INTERVALS",
    "VARIABLE_LABELS",
]
