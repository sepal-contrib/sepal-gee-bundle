"""GEE Source — extract JavaScript from Earth Engine Apps URLs."""

import logging

import solara
from pysepal.logger import setup_logging
from pysepal.sepalwidgets.vue_app import MapApp
from pysepal.solara import (
    get_current_theme_state,
    setup_theme_colors,
    with_sepal_sessions,
)
from pysepal.solara.notifications import NotificationProvider

from .components import (
    ExtractStep,
    SaveControls,
    SourceIframe,
    ViewModeToggle,
    build_source_srcdoc,
)
from .components.source_iframe import SourceIframe as _SourceIframeWidget
from .model import GeeSourceState
from .scripts.highlight import highlight_css

logger = setup_logging(logger_name="sepal_gee_bundle.gee_source")
logger.setLevel(logging.DEBUG)
logger.debug("GEE Source app initialized")

ABOUT_TEXT = """\
## GEE Source

Paste a public **Earth Engine App** URL and the app will:

1. Open the live app in the central frame.
2. Scrape its JavaScript source from the embedded `init(...)` payload.
3. Let you toggle between **Live app** and **Source** views, save the
   `.js` to your SEPAL workspace, or copy it to the clipboard.

Only public Earth Engine Apps render — apps gated behind Google sign-in
will produce an empty source result.

> **Attribution:** the extracted JavaScript belongs to its original
> author. Respect their license and copyright before reusing,
> redistributing, or republishing the code.
"""


@solara.component
def AboutContent():
    """About content rendered inside the MapApp dialog step."""
    solara.Markdown(ABOUT_TEXT)


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.gee_source")
def GeeSourcePage():
    """GEE Source — extract JavaScript from Earth Engine Apps URLs."""
    setup_theme_colors()
    NotificationProvider()
    theme_state = get_current_theme_state()

    state = solara.use_memo(lambda: GeeSourceState(), [])
    iframe_widget: _SourceIframeWidget = solara.use_memo(lambda: SourceIframe(), [])

    def _sync_iframe():
        iframe_widget.app_url = state.live_url.value
        iframe_widget.srcdoc = build_source_srcdoc(
            state.highlighted_html.value, highlight_css()
        )
        iframe_widget.mode = state.view_mode.value

    solara.use_effect(
        _sync_iframe,
        [
            state.live_url.value,
            state.highlighted_html.value,
            state.view_mode.value,
        ],
    )

    steps_data = [
        {
            "id": 1,
            "name": "About",
            "icon": "mdi-information-outline",
            "display": "dialog",
            "content": AboutContent(),
            "content_enabled": True,
            "width": 800,
        },
    ]

    right_panel_config = {
        "title": "GEE Source",
        "icon": "mdi-code-tags",
        "width": 420,
    }

    right_panel_content = [
        {
            "title": "Extract",
            "icon": "mdi-link-variant",
            "content": [ExtractStep(state), ViewModeToggle(state)],
        },
        {
            "title": "Save & Copy",
            "icon": "mdi-content-save",
            "content": [SaveControls(state)],
        },
    ]

    MapApp.element(
        app_title="GEE Source",
        repo_url="https://github.com/sepal-contrib/sepal-gee-bundle/tree/main/apps/gee_source",
        app_icon="mdi-code-tags",
        main_map=[iframe_widget],
        steps_data=steps_data,
        right_panel_config=right_panel_config,
        right_panel_content=right_panel_content,
        right_panel_open=True,
        is_pinned=False,
        theme_state=theme_state,
    )
