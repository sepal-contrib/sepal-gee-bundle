"""Shared GFC (Hansen Global Forest Change) primitives.

Pure constants and pure functions — safe to import from any app.

App-specific label conventions (e.g. snake_case vs spaced) stay in each
app's own `params.py`.
"""

import ee
import numpy as np
from matplotlib import colors as mcolors
from pysepal.solara.components.legend import DiscreteEntry, GradientEntry, LegendData

from apps._commons.datasets import (
    HANSEN_GFC_ID,
    HANSEN_GFC_MAX_LOSS_OFFSET,
)

# --- Dataset ---
# `GFC_MAX_YEAR` is the loss-year offset (year - 2000), not a calendar year.
GFC_DATASET = HANSEN_GFC_ID
GFC_MIN_YEAR = 1
GFC_MAX_YEAR = HANSEN_GFC_MAX_LOSS_OFFSET

# --- Class codes (loss years 1..GFC_MAX_YEAR + categorical 30/40/50/51) ---
GFC_CLASSES = [0, *range(1, GFC_MAX_YEAR + 1), 30, 40, 50, 51]


# --- Colors ---
def color_fader(v: int) -> np.ndarray:
    """Gradient from yellow to darkred across the loss year range."""
    c1 = np.array(mcolors.to_rgb("yellow"))
    c2 = np.array(mcolors.to_rgb("darkred"))
    mix = v / GFC_MAX_YEAR
    return (1 - mix) * c1 + mix * c2


HEX_PALETTE = [mcolors.to_hex(color_fader(i)) for i in range(1, GFC_MAX_YEAR + 1)]
HEX_PALETTE += [
    mcolors.to_hex("lightgrey"),  # 30 non-forest
    mcolors.to_hex("darkgreen"),  # 40 stable forest
    mcolors.to_hex("lightgreen"),  # 50 gain
    mcolors.to_hex("purple"),  # 51 gain + loss
]


# --- SLD styling for map display ---
_CME = '\n<ColorMapEntry color="{color}" quantity="{qty}" label="{label}"/>'


def build_sld() -> str:
    parts = ['<RasterSymbolizer>\n<ColorMap type="intervals" extended="false" >']
    parts.append(_CME.format(color=mcolors.to_hex("black").upper(), qty=0, label="no data"))
    for i in range(1, GFC_MAX_YEAR + 1):
        parts.append(
            _CME.format(
                color=mcolors.to_hex(color_fader(i)).upper(),
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


SLD_INTERVALS = build_sld()


# --- Legend data for LegendComponent ---
GFC_LEGEND = LegendData(
    gradients=[
        GradientEntry(
            colors=[HEX_PALETTE[0], HEX_PALETTE[GFC_MAX_YEAR - 1]],
            labels=[str(2000 + 1), str(2000 + GFC_MAX_YEAR)],
            title="Forest loss year",
        ),
    ],
    items=[
        DiscreteEntry("Non forest", HEX_PALETTE[GFC_MAX_YEAR]),
        DiscreteEntry("Stable forest", HEX_PALETTE[GFC_MAX_YEAR + 1]),
        DiscreteEntry("Gain", HEX_PALETTE[GFC_MAX_YEAR + 2]),
        DiscreteEntry("Gain + loss", HEX_PALETTE[GFC_MAX_YEAR + 3]),
    ],
)


# --- Classification ---
def classify_gfc(
    aoi: ee.FeatureCollection,
    threshold: int,
    start_year: int,
    end_year: int,
    dataset_id: str = GFC_DATASET,
) -> ee.Image:
    """Classify pixels into forest change categories.

    Returns ee.Image with values:
        1..GFC_MAX_YEAR: loss year (year - 2000)
        30: non-forest
        40: stable forest
        50: gain
        51: gain + loss
    """
    start = start_year - 2000
    end = end_year - 2000

    gfc = ee.Image(dataset_id).clip(aoi)
    treecov = gfc.select("treecover2000")
    lossy = gfc.select("lossyear").unmask(0)
    gain = gfc.select("gain")

    classified = (
        ee.Image(0)
        .where(treecov.lte(threshold).And(gain.eq(0)), 30)
        .where(treecov.lte(threshold).And(gain.eq(1)), 50)
        .where(treecov.gt(threshold).And(lossy.lt(start)).And(lossy.gt(0)), 30)
        .where(treecov.gt(threshold).And(lossy.gt(end)), 40)
        .where(
            treecov.gt(threshold).And(gain.eq(1)).And(lossy.gte(start)).And(lossy.lte(end)),
            51,
        )
        .where(treecov.gt(threshold).And(gain.eq(1)).And(lossy.eq(0)), 50)
        .where(
            treecov.gt(threshold).And(gain.eq(0)).And(lossy.gte(start)).And(lossy.lte(end)),
            lossy,
        )
        .where(treecov.gt(threshold).And(gain.eq(0)).And(lossy.eq(0)), 40)
        .selfMask()
    )

    return classified.uint8()
