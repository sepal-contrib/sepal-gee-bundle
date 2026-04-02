"""GFC dataset constants, class codes, colors, and visualization parameters."""

import numpy as np
from matplotlib import colors as mcolors

# --- Dataset ---
GFC_DATASET = "UMD/hansen/global_forest_change_2024_v1_12"
GFC_MIN_YEAR = 1
GFC_MAX_YEAR = 24

# --- Class codes ---
# Loss years are encoded as 1..GFC_MAX_YEAR, special classes as 30/40/50/51
GFC_CLASSES = [0, *range(1, GFC_MAX_YEAR + 1), 30, 40, 50, 51]

GFC_LABELS = [f"loss {2000 + i}" for i in range(1, GFC_MAX_YEAR + 1)] + [
    "non forest",
    "forest",
    "gains",
    "gain + loss",
]


# --- Colors ---
def _color_fader(v: int) -> np.ndarray:
    """Gradient from yellow to darkred across the loss year range."""
    c1 = np.array(mcolors.to_rgb("yellow"))
    c2 = np.array(mcolors.to_rgb("darkred"))
    mix = v / GFC_MAX_YEAR
    return (1 - mix) * c1 + mix * c2


# Hex palette for loss years + special classes
HEX_PALETTE = [mcolors.to_hex(_color_fader(i)) for i in range(1, GFC_MAX_YEAR + 1)]
HEX_PALETTE += [
    mcolors.to_hex("lightgrey"),  # non forest
    mcolors.to_hex("darkgreen"),  # forest
    mcolors.to_hex("lightgreen"),  # gains
    mcolors.to_hex("purple"),  # gain + loss
]

# Legend dict: label -> hex color
LEGEND_DICT = dict(zip(GFC_LABELS, HEX_PALETTE))

# --- SLD styling for map display ---
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
