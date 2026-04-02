"""AOI selection step for GFC app."""

import solara
from pysepal.solara.components.aoi.aoi_view import AoiView


@solara.component
def AoiStep(state, sepal_map):
    """Area of interest selection using pysepal AoiView."""
    AoiView(
        value=state.aoi,
        methods="ALL",
        gee=True,
        map_=sepal_map,
    )
