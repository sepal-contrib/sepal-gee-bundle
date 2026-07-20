"""AOI selection step for GFC app."""

import solara
from pysepal.solara.components.aoi.aoi_view import AoiView


@solara.component
def AoiStep(state, sepal_map):
    """Area of interest selection using pysepal AoiView.

    SHAPE and POINTS (local file uploads) are disabled because this is a
    multi-user GEE/container app. Admin boundaries, GEE assets, and drawn
    shapes remain available.
    """
    AoiView(
        value=state.aoi,
        methods=["-SHAPE", "-POINTS"],
        gee=True,
        map_=sepal_map,
    )
