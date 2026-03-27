import solara
from pysepal.mapping import SepalMap
from pysepal.sepalwidgets.vue_app import MapApp, ThemeToggle
from pysepal.solara import get_current_gee_interface, setup_theme_colors, with_sepal_sessions

from .model import GfcState


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.gfc")
def GfcPage():
    """Global Forest Change mask visualization and export."""
    setup_theme_colors()
    theme_toggle = ThemeToggle()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: GfcState(), [])
    sepal_map = solara.use_memo(
        lambda: SepalMap(gee_interface=gee_interface), [id(gee_interface)]
    )

    steps_data = []

    right_panel_config = {
        "title": "GFC",
        "icon": "mdi-forest",
        "width": 450,
    }

    right_panel_content = [
        {
            "title": "Area of Interest",
            "icon": "mdi-map-marker-check",
            "content": [solara.Text("AOI selection")],
        },
        {
            "title": "Forest Mask",
            "icon": "mdi-tree",
            "content": [solara.Text("Forest mask configuration")],
        },
        {
            "title": "Visualize & Export",
            "icon": "mdi-eye",
            "content": [solara.Text("Visualization and export")],
        },
    ]

    MapApp.element(
        app_title="Global Forest Change",
        app_icon="mdi-forest",
        main_map=[sepal_map],
        steps_data=steps_data,
        right_panel_config=right_panel_config,
        right_panel_content=right_panel_content,
        right_panel_open=True,
        theme_toggle=[theme_toggle],
    )
