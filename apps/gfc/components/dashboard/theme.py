"""Reactive ECharts theme + per-class colour helpers for the GFC dashboard."""

from typing import Literal

from pysepal.solara import use_theme_dark

from apps.gfc.params import GFC_MAX_YEAR, HEX_PALETTE

Theme = Literal["dark", "light"]

# Top-level class colour mapping (matches params.HEX_PALETTE tail).
# HEX_PALETTE layout: [loss_y1 .. loss_yN, non_forest, forest, gains, gain+loss]
CLASS_COLORS = {
    "forest": HEX_PALETTE[GFC_MAX_YEAR + 1],  # darkgreen
    "non_forest": HEX_PALETTE[GFC_MAX_YEAR],  # lightgrey
    "gains": HEX_PALETTE[GFC_MAX_YEAR + 2],  # lightgreen
    "gain_loss": HEX_PALETTE[GFC_MAX_YEAR + 3],  # purple
    "loss": HEX_PALETTE[GFC_MAX_YEAR - 1],  # darkred end of gradient
}


def loss_year_color(code: int) -> str:
    """Return the hex colour for a 1..GFC_MAX_YEAR loss code."""
    idx = max(1, min(GFC_MAX_YEAR, code)) - 1
    return HEX_PALETTE[idx]


def use_echarts_theme() -> Theme:
    """Return the active ECharts theme for the current Solara session."""
    return "dark" if use_theme_dark() else "light"
