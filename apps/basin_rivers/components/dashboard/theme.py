"""Reactive ECharts theme tied to pysepal ThemeToggle."""

from typing import Literal

import solara

Theme = Literal["dark", "light"]


def use_echarts_theme(theme_toggle) -> Theme:
    """Return "dark" or "light" and track changes on ThemeToggle.dark."""
    theme, set_theme = solara.use_state("dark" if getattr(theme_toggle, "dark", False) else "light")

    def _observe():
        def handler(change):
            set_theme("dark" if change["new"] else "light")

        theme_toggle.observe(handler, "dark")
        return lambda: theme_toggle.unobserve(handler, "dark")

    solara.use_effect(_observe, [id(theme_toggle)])
    return theme
