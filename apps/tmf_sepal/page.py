"""TMF SEPAL — JRC Tropical Moist Forests visualization and export."""

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

from .components import AoiStep, ExportStep, ParamsStep, StatsStep
from .model import TmfSepalState
from .params import TMF_VERSION_YEAR

logger = setup_logging(logger_name="sepal_gee_bundle.tmf_sepal")
logger.setLevel(logging.DEBUG)
logger.debug("TMF app initialized")

ABOUT_TEXT = f"""\
## JRC Tropical Moist Forests (TMF)

Visualize and export the JRC Tropical Moist Forests dataset for a given area of
interest and year range.

### Workflow

1. Select an **Area of Interest**.
2. Pick a **TMF layer** (Degradation year, Deforestation year, or Annual
   change) and a **year range** in 1990-{TMF_VERSION_YEAR}.
3. Click **Add layer** to render the TMF image on the map.
4. Use the **Export** step to send the image to a GEE asset, Google Drive, or
   SEPAL.

### Dataset

- JRC/TMF/v1_{TMF_VERSION_YEAR}/DegradationYear
- JRC/TMF/v1_{TMF_VERSION_YEAR}/DeforestationYear
- JRC/TMF/v1_{TMF_VERSION_YEAR}/AnnualChanges

### References

- [Vancutsem, C. et al. 2021. "Long-term (1990-2019) monitoring of forest cover
  changes in the humid tropics." *Science Advances* 7, eabe1603.]\
(https://www.science.org/doi/10.1126/sciadv.abe1603)
- [JRC TMF dataset portal](https://forobs.jrc.ec.europa.eu/TMF/)
- Legacy SEPAL module: https://github.com/sepal-contrib/tmf_sepal
"""


@solara.component
def AboutContent():
    solara.Markdown(ABOUT_TEXT)


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.tmf_sepal")
def TmfSepalPage():
    """Tropical Moist Forests visualization and export."""
    setup_theme_colors()
    NotificationProvider()
    theme_state = get_current_theme_state()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: TmfSepalState(), [])
    sepal_map = solara.use_memo(
        lambda: SepalMap(gee_interface=gee_interface, fullscreen=True, theme_state=theme_state),
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
        "title": "TMF",
        "icon": "mdi-tree",
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
            "title": "Statistics",
            "icon": "mdi-chart-pie",
            "content": [StatsStep(state, gee_interface, legend_visible, sepal_map)],
        },
        {
            "title": "Export",
            "icon": "mdi-download",
            "content": [ExportStep(state, gee_interface)],
        },
    ]

    MapApp.element(
        app_title="Tropical Moist Forests",
        app_icon="mdi-tree",
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
