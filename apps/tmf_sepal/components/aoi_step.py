"""AOI selection step for the TMF app."""

import solara
from pysepal.solara.components.aoi.aoi_view import AoiView


@solara.component
def AoiStep(state, sepal_map):
    """Area of Interest selection using pysepal AoiView.

    Shape and point draw methods are disabled because JRC TMF mosaics are only
    meaningful when clipped by an actual region.
    """
    AoiView(
        value=state.aoi,
        methods=["-SHAPE", "-POINTS"],
        gee=True,
        map_=sepal_map,
    )
