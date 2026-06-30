"""FCDM — Forest Canopy Disturbance Monitoring (Delta-rNBR)."""

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

from apps._widgets import AboutOnceDialog, MarkdownNewTab, add_satellite_basemap

from .components import AoiStep, ForestStep, ParamsStep, RunStep
from .model import FcdmState
from .params import delta_rnbr_legend

logger = setup_logging(logger_name="sepal_gee_bundle.fcdm")
logger.setLevel(logging.DEBUG)
logger.debug("FCDM app initialized")


ABOUT_TEXT = """\
## Forest Canopy Disturbance Monitoring (FCDM)

Detect forest canopy disturbance using Delta relative Normalized Burn Ratio \
(Delta-rNBR) spectral change detection between a reference period and an \
analysis period.

### Workflow

1. Select an **Area of Interest**.
2. Choose a **forest mask source** (Hansen GFC, JRC TMF Roadless, or none) \
and pick one or more **sensors** (Landsat 4/5/7/8, Sentinel-2).
3. Set **reference** and **analysis** date ranges and the algorithm \
parameters (adjustment kernel, DDR filter).
4. Run the analysis and export layers to GEE asset, Google Drive or SEPAL.

### References

- [SEPAL documentation](https://docs.sepal.io/)
- [Original sepal_ui module](https://github.com/sepal-contrib/fcdm)
- Sentinel-2 cloud masking: Dario Simonetti (JRC) — IFORCE / PINO.
"""


@solara.component
def AboutContent():
    MarkdownNewTab(ABOUT_TEXT)


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.fcdm")
def FcdmPage():
    """Forest Canopy Disturbance Monitoring application."""
    solara.Title("Forest Canopy Disturbance Monitoring")
    setup_theme_colors()
    NotificationProvider()
    theme_state = get_current_theme_state()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: FcdmState(), [])
    legend_data = solara.use_reactive(delta_rnbr_legend())
    legend_visible = solara.use_reactive(False)
    sepal_map = solara.use_memo(
        lambda: add_satellite_basemap(
            SepalMap(
                gee_interface=gee_interface,
                fullscreen=True,
                theme_state=theme_state,
                min_zoom=3,
            )
        ),
        [id(gee_interface)],
    )

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
        "title": "FCDM",
        "icon": "mdi-tree-outline",
        "width": 460,
    }

    right_panel_content = [
        {
            "title": "Area of Interest",
            "icon": "mdi-map-marker-check",
            "content": [AoiStep(state, sepal_map)],
        },
        {
            "title": "Forest mask & sensors",
            "icon": "mdi-tree",
            "content": [ForestStep(state, gee_interface=gee_interface)],
        },
        {
            "title": "Dates & parameters",
            "icon": "mdi-tune",
            "content": [ParamsStep(state)],
        },
        {
            "title": "Run & export",
            "icon": "mdi-play-circle",
            "content": [RunStep(state, sepal_map, gee_interface, legend_visible)],
        },
    ]

    MapApp.element(
        app_title="Forest Canopy Disturbance Monitoring",
        repo_url="https://github.com/sepal-contrib/sepal-gee-bundle",
        docs_url="https://github.com/sepal-contrib/sepal-gee-bundle/tree/main/apps/fcdm",
        app_icon="mdi-tree-outline",
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

    AboutOnceDialog(
        storage_key="sepal-gee-bundle:fcdm:about-dismissed",
        title="Forest Canopy Disturbance Monitoring",
        markdown_text=ABOUT_TEXT,
    )
