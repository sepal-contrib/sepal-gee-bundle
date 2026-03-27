import solara
from pysepal.mapping import SepalMap
from pysepal.sepalwidgets.vue_app import MapApp, ThemeToggle
from pysepal.solara import get_current_gee_interface, setup_theme_colors, with_sepal_sessions

from .model import CoverageState


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.coverage_analysis")
def CoverageAnalysisPage():
    """Satellite coverage and NDVI analysis."""
    setup_theme_colors()
    theme_toggle = ThemeToggle()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: CoverageState(), [])
    sepal_map = solara.use_memo(
        lambda: SepalMap(gee_interface=gee_interface), [id(gee_interface)]
    )

    steps_data = []

    right_panel_config = {
        "title": "Coverage Analysis",
        "icon": "mdi-satellite-uplink",
        "width": 450,
    }

    right_panel_content = [
        {
            "title": "Area of Interest",
            "icon": "mdi-map-marker-check",
            "content": [solara.Text("AOI selection")],
        },
        {
            "title": "Sensors & Dates",
            "icon": "mdi-satellite-variant",
            "content": [solara.Text("Sensor and date configuration")],
        },
        {
            "title": "Visualization",
            "icon": "mdi-map",
            "content": [solara.Text("Coverage visualization")],
        },
        {
            "title": "Export",
            "icon": "mdi-download",
            "content": [solara.Text("Export results")],
        },
    ]

    MapApp.element(
        app_title="Satellite Coverage Analysis",
        app_icon="mdi-satellite-uplink",
        main_map=[sepal_map],
        steps_data=steps_data,
        right_panel_config=right_panel_config,
        right_panel_content=right_panel_content,
        right_panel_open=True,
        theme_toggle=[theme_toggle],
    )
