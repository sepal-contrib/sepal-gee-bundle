"""Reactive ECharts theme tied to the pysepal session theme state."""

from typing import Literal

from pysepal.solara import use_theme_dark

Theme = Literal["dark", "light"]


def use_echarts_theme() -> Theme:
    """Return the active ECharts theme for the current Solara session."""
    return "dark" if use_theme_dark() else "light"
