"""AOI selection step for the TMF app."""

import solara
from pysepal.solara.components.aoi.aoi_view import AoiView


@solara.component
def AoiStep(state, sepal_map):
    """Area of Interest selection using pysepal AoiView.

    SHAPE and POINTS (local file uploads) are disabled because JRC TMF
    mosaics are only meaningful when clipped by a real region. Drawn shapes
    and GEE-backed methods (admin boundaries, assets) remain available.
    """
    AoiView(
        value=state.aoi,
        methods=["-SHAPE", "-POINTS"],
        gee=True,
        map_=sepal_map,
    )
