"""AOI selection step for the ALOS mosaics app."""

import solara
from pysepal.solara.components.aoi.aoi_view import AoiView


@solara.component
def AoiStep(state, sepal_map):
    """AOI picker using pysepal AoiView.

    SHAPE and POINTS methods are disabled because the ALOS mosaic is only
    meaningful when clipped by a real region.
    """
    AoiView(
        value=state.aoi,
        methods=["-SHAPE", "-POINTS"],
        gee=True,
        map_=sepal_map,
    )
