"""GFC app params.

Re-exports shared GFC primitives from apps._commons.gfc plus app-specific
labels/legend dict.
"""

from apps._commons.gfc import (
    GFC_CLASSES,
    GFC_DATASET,
    GFC_LEGEND,
    GFC_MAX_YEAR,
    GFC_MIN_YEAR,
    HEX_PALETTE,
    SLD_INTERVALS,
    build_sld,
    color_fader,
)

__all__ = [
    "GFC_CLASSES",
    "GFC_DATASET",
    "GFC_LABELS",
    "GFC_LEGEND",
    "GFC_MAX_YEAR",
    "GFC_MIN_YEAR",
    "HEX_PALETTE",
    "LEGEND_DICT",
    "SLD_INTERVALS",
    "build_sld",
    "color_fader",
]

# --- App-specific labels (spaced form, used by GFC dashboard/table) ---
GFC_LABELS = [f"loss {2000 + i}" for i in range(1, GFC_MAX_YEAR + 1)] + [
    "non forest",
    "forest",
    "gains",
    "gain + loss",
]

LEGEND_DICT = dict(zip(GFC_LABELS, HEX_PALETTE))
