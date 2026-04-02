import logging

import solara
from pysepal.logger import setup_logging
from pysepal.mapping import SepalMap
from pysepal.sepalwidgets.vue_app import MapApp, ThemeToggle
from pysepal.solara import get_current_gee_interface, setup_theme_colors, with_sepal_sessions

from .model import BasinRiversState

logger = setup_logging(logger_name="sepal_gee_bundle.basin_rivers")
logger.setLevel(logging.DEBUG)
logger.debug("Basin Rivers app initialized")


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.basin_rivers")
def BasinRiversPage():
    """Upstream watershed delineation and forest change statistics."""
    setup_theme_colors()
    theme_toggle = ThemeToggle()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: BasinRiversState(), [])  # noqa: F841
    sepal_map = solara.use_memo(
        lambda: SepalMap(
            gee_interface=gee_interface, fullscreen=True, theme_toggle=theme_toggle
        ),
        [id(gee_interface)],
    )

    steps_data = []

    right_panel_config = {
        "title": "Basin Rivers",
        "icon": "mdi-waves",
        "width": 450,
    }

    right_panel_content = [
        {
            "title": "Select Point",
            "icon": "mdi-map-marker",
            "content": [solara.Text("Point selection")],
        },
        {
            "title": "Basin Parameters",
            "icon": "mdi-tune",
            "content": [solara.Text("Basin level and thresholds")],
        },
        {
            "title": "Results",
            "icon": "mdi-chart-bar",
            "content": [solara.Text("Forest change statistics")],
        },
    ]

    MapApp.element(
        app_title="Basin Rivers",
        app_icon="mdi-waves",
        main_map=[sepal_map],
        steps_data=steps_data,
        right_panel_config=right_panel_config,
        right_panel_content=right_panel_content,
        right_panel_open=True,
        theme_toggle=[theme_toggle],
    )
