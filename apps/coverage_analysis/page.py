"""Coverage Analysis — satellite coverage and NDVI statistics."""

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

from .components import AoiStep, DashboardStep, ExportStep, VisualizeStep
from .model import CoverageState

logger = setup_logging(logger_name="sepal_gee_bundle.coverage_analysis")
logger.setLevel(logging.DEBUG)
logger.debug("Coverage Analysis app initialized")

ABOUT_TEXT = """\
## Satellite Coverage Analysis

Analyze satellite imagery availability and NDVI statistics over an AOI.

### Workflow

1. Select an AOI.
2. Pick sensors (Landsat 4/5/7/8, Sentinel-2), a date range,
   SR/TOA, Tier 2 option, a measure (cloud-free pixel count,
   total scene count, NDVI median or std. dev.) and whether to
   split per year, then click **Show on map**.
3. Export the composite to an EE asset, Google Drive, or SEPAL.

### Datasets

- Landsat C02 (``T1_L2`` for SR, ``T1_TOA`` for TOA) for L4/L5/L7/L8.
- Sentinel-2 harmonized (``COPERNICUS/S2_SR_HARMONIZED`` or
  ``COPERNICUS/S2_HARMONIZED``) joined with ``COPERNICUS/S2_CLOUD_PROBABILITY``.
"""


@solara.component
def AboutContent():
    solara.Markdown(ABOUT_TEXT)


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.coverage_analysis")
def CoverageAnalysisPage():
    """Satellite coverage and NDVI analysis."""
    setup_theme_colors()
    NotificationProvider()
    theme_state = get_current_theme_state()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: CoverageState(), [])
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

    steps_data = [
        {
            "id": 1,
            "name": "About",
            "icon": "mdi-information-outline",
            "display": "dialog",
            "content": AboutContent(),
            "content_enabled": True,
            "width": 900,
        },
    ]

    right_panel_config = {
        "title": "Coverage Analysis",
        "icon": "mdi-satellite-uplink",
        "width": 450,
    }

    right_panel_content = [
        {
            "title": "Area of Interest",
            "icon": "mdi-map-marker-check",
            "content": [AoiStep(state, sepal_map)],
        },
        {
            "title": "Sensors & view",
            "icon": "mdi-satellite-variant",
            "content": [
                VisualizeStep(
                    state, sepal_map, gee_interface, legend_data, legend_visible
                )
            ],
        },
        {
            "title": "Dashboard",
            "icon": "mdi-view-dashboard",
            "content": [
                DashboardStep(state, legend_visible=legend_visible, sepal_map=sepal_map)
            ],
        },
        {
            "title": "Export",
            "icon": "mdi-download",
            "content": [ExportStep(state, gee_interface)],
        },
    ]

    MapApp.element(
        app_title="Satellite Coverage Analysis",
        app_icon="mdi-satellite-uplink",
        main_map=[sepal_map],
        steps_data=steps_data,
        initial_step=1,
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
