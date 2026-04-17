"""Basin Rivers constants: HydroSHEDS, GFC dataset, class codes, colors."""

import numpy as np
from matplotlib import colors as mcolors

# --- GFC Dataset ---
GFC_DATASET = "UMD/hansen/global_forest_change_2024_v1_12"
GFC_MIN_YEAR = 1
GFC_MAX_YEAR = 24

# --- HydroSHEDS ---
HYBAS_DATASET_TEMPLATE = "WWF/HydroSHEDS/v1/Basins/hybas_{level}"
HYBAS_LEVELS = list(range(5, 13))

# --- GFC Class codes ---
GFC_CLASSES = [0, *range(1, GFC_MAX_YEAR + 1), 30, 40, 50, 51]

GFC_LABELS = [f"loss_{2000 + i}" for i in range(1, GFC_MAX_YEAR + 1)] + [
    "non_forest",
    "forest",
    "gain",
    "gain_loss",
]

# Groups: all loss years → "loss", plus the fixed categories
GFC_GROUPS = ["loss"] * GFC_MAX_YEAR + ["non_forest", "forest", "gain", "gain_loss"]
GFC_TRANSLATION = dict(zip([*range(1, GFC_MAX_YEAR + 1), 30, 40, 50, 51], GFC_GROUPS))


# --- Colors ---
def _color_fader(v: int) -> np.ndarray:
    c1 = np.array(mcolors.to_rgb("yellow"))
    c2 = np.array(mcolors.to_rgb("darkred"))
    mix = v / GFC_MAX_YEAR
    return (1 - mix) * c1 + mix * c2


HEX_PALETTE = [mcolors.to_hex(_color_fader(i)) for i in range(1, GFC_MAX_YEAR + 1)]
HEX_PALETTE += [
    mcolors.to_hex("lightgrey"),
    mcolors.to_hex("darkgreen"),
    mcolors.to_hex("lightgreen"),
    mcolors.to_hex("purple"),
]

GFC_COLORS_DICT = {
    "loss": mcolors.to_hex("darkred"),
    "non_forest": mcolors.to_hex("lightgrey"),
    "forest": mcolors.to_hex("darkgreen"),
    "gain": mcolors.to_hex("lightgreen"),
    "gain_loss": mcolors.to_hex("purple"),
}

LEGEND_DICT = dict(zip(GFC_LABELS, HEX_PALETTE))

# --- SLD styling ---
_CME = '\n<ColorMapEntry color="{color}" quantity="{qty}" label="{label}"/>'


def _build_sld() -> str:
    parts = ['<RasterSymbolizer>\n<ColorMap type="intervals" extended="false" >']
    parts.append(_CME.format(color=mcolors.to_hex("black").upper(), qty=0, label="no data"))
    for i in range(1, GFC_MAX_YEAR + 1):
        parts.append(
            _CME.format(
                color=mcolors.to_hex(_color_fader(i)).upper(),
                qty=i,
                label=f"loss {2000 + i}",
            )
        )
    parts.append(_CME.format(color=mcolors.to_hex("lightgrey").upper(), qty=30, label="non forest"))
    parts.append(
        _CME.format(color=mcolors.to_hex("darkgreen").upper(), qty=40, label="stable forest")
    )
    parts.append(_CME.format(color=mcolors.to_hex("lightgreen").upper(), qty=50, label="gain"))
    parts.append(_CME.format(color=mcolors.to_hex("purple").upper(), qty=51, label="gain + loss"))
    parts.append("\n</ColorMap>\n</RasterSymbolizer>")
    return "".join(parts)


SLD_INTERVALS = _build_sld()

# --- Display limits ---
MAX_CATCH_DISPLAY = 10

# --- Dashboard palette (deterministic, hls-like) ---
CATCH_COLOR_PALETTE = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000",
    "#aaffc3", "#808000", "#ffd8b1", "#000075", "#808080",
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
