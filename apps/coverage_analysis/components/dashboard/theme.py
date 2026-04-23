"""Reactive ECharts theme + per-sensor colour helpers for Coverage Analysis."""

from typing import Literal

from pysepal.solara import use_theme_dark

Theme = Literal["dark", "light"]

# Deterministic blue -> teal cycle matched to SENSOR_ITEMS order.
# Landsat shades of blue, Sentinel teal/green for contrast.
SENSOR_COLORS: dict[str, str] = {
    "l4": "#1f4e79",  # darkest blue
    "l5": "#2e75b6",
    "l7": "#4a90d9",
    "l8": "#6fb1e3",  # light blue
    "s2": "#2ca58d",  # teal-green
}

SENSOR_LABELS: dict[str, str] = {
    "l4": "Landsat 4",
    "l5": "Landsat 5",
    "l7": "Landsat 7",
    "l8": "Landsat 8",
    "s2": "Sentinel-2",
}


def sensor_color(sensor: str) -> str:
    """Return the hex colour for a sensor code."""
    return SENSOR_COLORS.get(sensor, "#888888")


def use_echarts_theme() -> Theme:
    """Return the active ECharts theme for the current Solara session."""
    return "dark" if use_theme_dark() else "light"
