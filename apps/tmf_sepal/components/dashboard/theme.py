"""Reactive ECharts theme + colour helpers for the TMF dashboard."""

from typing import Literal

from pysepal.solara import use_theme_dark

from apps.tmf_sepal.params import (
    TMF_CHG_TRANSITION_CLASSES,
    TMF_MAX_YEAR,
    TMF_MIN_YEAR,
    TMF_TRANSITION_MAIN_CLASSES,
    TMF_YEAR_PALETTE,
)

Theme = Literal["dark", "light"]

# CHG class code -> hex colour
CHG_CLASS_COLORS: dict[int, str] = {
    code: color for code, _label, color in TMF_CHG_TRANSITION_CLASSES
}
CHG_CLASS_LABELS: dict[int, str] = {
    code: label for code, label, _color in TMF_CHG_TRANSITION_CLASSES
}
MAIN_CLASS_COLORS: dict[int, str] = {
    code: color for code, _label, color in TMF_TRANSITION_MAIN_CLASSES
}
MAIN_CLASS_LABELS: dict[int, str] = {
    code: label for code, label, _color in TMF_TRANSITION_MAIN_CLASSES
}


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _sample_gradient(palette: list[str], t: float) -> str:
    """Sample a 0..1 position from a list of colour stops."""
    if not palette:
        return "#888888"
    if len(palette) == 1:
        return palette[0]
    t = max(0.0, min(1.0, t))
    scaled = t * (len(palette) - 1)
    idx = int(scaled)
    if idx >= len(palette) - 1:
        return palette[-1]
    frac = scaled - idx
    a = _hex_to_rgb(palette[idx])
    b = _hex_to_rgb(palette[idx + 1])
    mixed = tuple(round(a[i] + (b[i] - a[i]) * frac) for i in range(3))
    return _rgb_to_hex(mixed)  # type: ignore[arg-type]


def year_color(year: int, year_start: int | None = None, year_end: int | None = None) -> str:
    """Return a hex colour for a year along the TMF year gradient.

    When ``year_start``/``year_end`` are provided, the gradient is stretched
    over that range so the first/last years map to the palette endpoints.
    Otherwise falls back to the full ``TMF_MIN_YEAR..TMF_MAX_YEAR`` span.
    """
    y0 = year_start if year_start is not None else TMF_MIN_YEAR
    y1 = year_end if year_end is not None else TMF_MAX_YEAR
    if y1 <= y0:
        return TMF_YEAR_PALETTE[0]
    t = (year - y0) / (y1 - y0)
    return _sample_gradient(TMF_YEAR_PALETTE, t)


def use_echarts_theme() -> Theme:
    """Return the active ECharts theme for the current Solara session."""
    return "dark" if use_theme_dark() else "light"
