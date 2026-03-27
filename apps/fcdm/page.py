import solara
from pysepal.mapping import SepalMap
from pysepal.sepalwidgets.vue_app import MapApp, ThemeToggle
from pysepal.solara import get_current_gee_interface, setup_theme_colors, with_sepal_sessions

from .model import FcdmState


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.fcdm")
def FcdmPage():
    """Forest Canopy Disturbance Monitoring application."""
    setup_theme_colors()
    theme_toggle = ThemeToggle()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: FcdmState(), [])
    sepal_map = solara.use_memo(
        lambda: SepalMap(gee_interface=gee_interface), [id(gee_interface)]
    )

    steps_data = []

    right_panel_config = {
        "title": "FCDM",
        "icon": "mdi-tree-outline",
        "width": 450,
    }

    right_panel_content = [
        {
            "title": "Area of Interest",
            "icon": "mdi-map-marker-check",
            "content": [solara.Text("AOI selection")],
        },
        {
            "title": "Dates & Sensors",
            "icon": "mdi-satellite-variant",
            "content": [solara.Text("Date and sensor configuration")],
        },
        {
            "title": "Forest Mask",
            "icon": "mdi-tree",
            "content": [solara.Text("Forest mask selection")],
        },
        {
            "title": "Parameters",
            "icon": "mdi-tune",
            "content": [solara.Text("Algorithm parameters")],
        },
        {
            "title": "Run & Export",
            "icon": "mdi-play-circle",
            "content": [solara.Text("Run analysis and export")],
        },
    ]

    MapApp.element(
        app_title="Forest Canopy Disturbance Monitoring",
        app_icon="mdi-tree-outline",
        main_map=[sepal_map],
        steps_data=steps_data,
        right_panel_config=right_panel_config,
        right_panel_content=right_panel_content,
        right_panel_open=True,
        theme_toggle=[theme_toggle],
    )
