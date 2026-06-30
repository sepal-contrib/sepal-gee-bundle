"""View-mode toggle: switch the central iframe between live app and source."""

from __future__ import annotations

import solara


@solara.component
def ViewModeToggle(state):
    """Two-button 50/50 toggle bound to ``state.view_mode``.

    Disabled until an extract has produced a live URL or source HTML.
    """
    has_app = bool(state.live_url.value)
    has_source = bool(state.highlighted_html.value)

    def _set(value):
        if value:
            state.view_mode.set(value)

    with solara.Div(style={"width": "100%", "display": "flex", "justify-content": "center"}):
        with solara.ToggleButtonsSingle(
            value=state.view_mode.value,
            on_value=_set,
            mandatory=True,
            dense=True,
            style={"width": "100%", "display": "flex"},
        ):
            solara.Button(
                label="Live app",
                value="app",
                small=True,
                disabled=not has_app,
                style={"flex": "1 1 0"},
            )
            solara.Button(
                label="Source",
                value="source",
                small=True,
                disabled=not has_source,
                style={"flex": "1 1 0"},
            )
