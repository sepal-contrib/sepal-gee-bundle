"""Basin Rivers — Upstream Watershed Delineation & Forest Change Stats."""

import logging

import solara
from pysepal.logger import setup_logging
from pysepal.mapping import SepalMap
from pysepal.sepalwidgets.vue_app import MapApp
from pysepal.solara import (
    get_current_gee_interface,
    get_current_theme_state,
    setup_theme_colors,
    with_sepal_sessions,
)
from pysepal.solara.components.legend import LegendComponent
from pysepal.solara.notifications import NotificationProvider

from .components import DelineationStep, ParamsStep, PointStep
from .model import BasinRiversState

logger = setup_logging(logger_name="sepal_gee_bundle.basin_rivers")
logger.setLevel(logging.DEBUG)
logger.debug("Basin Rivers app initialized")


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.basin_rivers")
def BasinRiversPage():
    """Upstream watershed delineation and forest change statistics."""
    setup_theme_colors()
    NotificationProvider()
    theme_state = get_current_theme_state()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: BasinRiversState(), [])
    sepal_map = solara.use_memo(
        lambda: SepalMap(
            gee_interface=gee_interface,
            fullscreen=True,
            theme_state=theme_state,
            min_zoom=3,
        ),
        [id(gee_interface)],
    )

    legend_data = solara.use_reactive({})
    legend_visible = solara.use_reactive(False)

    steps_data = []

    right_panel_config = {
        "title": "Basin Rivers",
        "icon": "mdi-waves",
        "width": 450,
    }

    right_panel_content = [
        {
            "title": "Outlet",
            "icon": "mdi-map-marker",
            "content": [PointStep(state, sepal_map)],
        },
        {
            "title": "Parameters",
            "icon": "mdi-tune",
            "content": [ParamsStep(state)],
        },
        {
            "title": "Delineation & Stats",
            "icon": "mdi-source-branch",
            "content": [
                DelineationStep(
                    state,
                    sepal_map,
                    gee_interface,
                    legend_data,
                    legend_visible,
                )
            ],
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
        is_pinned=False,
        theme_state=theme_state,
    )

    LegendComponent(
        legend_data=legend_data.value,
        visible=legend_visible.value,
    )
