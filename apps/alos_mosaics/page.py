"""ALOS mosaics — JAXA ALOS PALSAR / PALSAR-2 yearly mosaics + FNF.

Ported from https://github.com/sepal-contrib/alos_mosaics. Only the GEE
algorithms and parameters are preserved; all sepal_ui / traitlets UI code has
been replaced with pysepal + Solara primitives.
"""

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

from apps._widgets import AboutOnceDialog

from .components import AoiStep, ExportStep, VizStep
from .model import AlosMosaicsState

logger = setup_logging(logger_name="sepal_gee_bundle.alos_mosaics")
logger.setLevel(logging.DEBUG)
logger.debug("ALOS mosaics app initialized")

ABOUT_TEXT = """\
## JAXA ALOS PALSAR / PALSAR-2 yearly mosaics

Browse, visualize and export the JAXA ALOS PALSAR (2007-2010) and ALOS-2
PALSAR-2 (2015+) yearly SAR mosaics at 25 m resolution, with optional speckle
filtering (Quegan or Refined Lee), layover / shadow masking and dB scaling.

### Workflow

1. Pick an **Area of Interest**.
2. Choose a **year**, optional speckle filter, LS mask, dB toggle and the
   display layer (RGB backscatter, RFDI or Forest / Non-Forest — only for
   years <= 2017), then press **Add layer to map**. The mosaic is built
   server-side (GEE) and rendered on the map in one step.
3. **Export** the selected bands (backscatter, RFDI, texture, auxiliary, FNF)
   to a GEE asset, Google Drive or SEPAL.

### GEE datasets

- `JAXA/ALOS/PALSAR/YEARLY/SAR` — yearly HH / HV backscatter mosaics
- `JAXA/ALOS/PALSAR/YEARLY/FNF` — yearly Forest / Non-Forest classification
  (1990-2017)

### References

- [Shimada, M. et al. 2014. "New global forest/non-forest maps from ALOS
  PALSAR data (2007-2010)."](https://doi.org/10.1016/j.rse.2014.04.014)
- [JAXA PALSAR mosaics portal](https://www.eorc.jaxa.jp/ALOS/en/dataset/fnf_e.htm)
- Legacy SEPAL module: https://github.com/sepal-contrib/alos_mosaics
"""


@solara.component
def AboutContent():
    solara.Markdown(ABOUT_TEXT)


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.alos_mosaics")
def AlosMosaicsPage():
    """ALOS PALSAR yearly mosaics visualization and export."""
    solara.Title("ALOS PALSAR Mosaics")
    setup_theme_colors()
    NotificationProvider()
    theme_state = get_current_theme_state()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: AlosMosaicsState(), [])
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
        "title": "ALOS mosaics",
        "icon": "mdi-satellite-variant",
        "width": 460,
    }

    right_panel_content = [
        {
            "title": "Area of Interest",
            "icon": "mdi-map-marker-check",
            "content": [AoiStep(state, sepal_map)],
        },
        {
            "title": "Visualization",
            "icon": "mdi-map",
            "content": [
                VizStep(state, sepal_map, gee_interface, legend_data, legend_visible)
            ],
        },
        {
            "title": "Export",
            "icon": "mdi-download",
            "content": [ExportStep(state, gee_interface)],
        },
    ]

    MapApp.element(
        app_title="ALOS mosaics",
        repo_url="https://github.com/sepal-contrib/sepal-gee-bundle/tree/main/apps/alos_mosaics",
        app_icon="mdi-satellite-variant",
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
        storage_key="sepal-gee-bundle:alos-mosaics:about-dismissed",
        title="ALOS PALSAR Mosaics",
        markdown_text=ABOUT_TEXT,
    )
