"""GFC — Global Forest Change visualization and export."""

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

from .components import AoiStep, ParamsStep, ResultsStep
from .model import GfcState

logger = setup_logging(logger_name="sepal_gee_bundle.gfc")
logger.setLevel(logging.DEBUG)
logger.debug("GFC app initialized")

ABOUT_TEXT = """\
## Global Forest Change

This application allows the user to:

- Define an area of interest
- Retrieve tree cover change data from the Hansen et al. (2013) dataset
- Combine the layers to produce a forest change map for a given canopy cover \
threshold

### Background

GFC provides global layers of information on tree cover and tree cover change \
since 2000, at 30 m spatial resolution:

- **Tree canopy cover** for the year 2000 (treecover2000)
- **Global forest cover gain** 2000-2012 (gain)
- **Year of gross forest cover loss** event (lossyear)

### References

- [Hansen, M. C. et al. 2013. "High-Resolution Global Maps of 21st-Century \
Forest Cover Change." *Science* 342: 850-53.]\
(https://science.sciencemag.org/content/342/6160/850)
- [University of Maryland GFC dataset]\
(http://earthenginepartners.appspot.com/science-2013-global-forest)
- [SEPAL documentation]\
(https://docs.sepal.io/en/latest/modules/dwn/gfc_wrapper_python.html)

![gfc](https://earthengine.google.com/static/images/hansen.jpg)
"""


@solara.component
def AboutContent():
    """About content rendered inside the MapApp dialog step."""
    MarkdownNewTab(
        ABOUT_TEXT,
        style="img { width: 70%; display: block; margin: 16px auto 0; border-radius: 8px; }",
    )


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.gfc")
def GfcPage():
    """Global Forest Change mask visualization and export."""
    solara.Title("Global Forest Change")
    setup_theme_colors()
    NotificationProvider()
    theme_state = get_current_theme_state()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: GfcState(), [])
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

    legend_data = solara.use_reactive({})
    legend_visible = solara.use_reactive(False)
    legend_collapsed = solara.use_reactive(False)

    steps_data = [
        {
            "id": 1,
            "name": "About",
            "icon": "mdi-information-outline",
            "display": "dialog",
            "content": AboutContent(),
            "content_enabled": True,
            "width": 1100,
        },
    ]

    right_panel_config = {
        "title": "GFC",
        "icon": "mdi-forest",
        "width": 450,
    }

    right_panel_content = [
        {
            "title": "Area of Interest",
            "icon": "mdi-map-marker-check",
            "content": [AoiStep(state, sepal_map)],
        },
        {
            "title": "Parameters",
            "icon": "mdi-tune",
            "content": [ParamsStep(state, sepal_map, gee_interface, legend_data, legend_visible)],
        },
        {
            "title": "Results & Export",
            "icon": "mdi-chart-bar",
            "content": [ResultsStep(state, sepal_map, gee_interface, legend_visible)],
        },
    ]

    MapApp.element(
        app_title="Global Forest Change",
        repo_url="https://github.com/sepal-contrib/sepal-gee-bundle",
        docs_url="https://github.com/sepal-contrib/sepal-gee-bundle/tree/main/apps/gfc",
        app_icon="mdi-forest",
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
        collapsed=legend_collapsed.value,
        event_set_collapsed=legend_collapsed.set,
    )

    AboutOnceDialog(
        storage_key="sepal-gee-bundle:gfc:about-dismissed",
        title="Global Forest Change",
        markdown_text=ABOUT_TEXT,
    )
