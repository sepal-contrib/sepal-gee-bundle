"""AOI selection for the Coverage Analysis app."""

import solara
from pysepal.solara.components.aoi.aoi_view import AoiView


@solara.component
def AoiStep(state, sepal_map):
    """Area of interest selection. Excludes SHAPE/POINTS (container/GEE app)."""
    AoiView(
        value=state.aoi,
        methods=["-SHAPE", "-POINTS"],
        gee=True,
        map_=sepal_map,
    )
