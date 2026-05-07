"""AOI selection step for FCDM."""

import solara
from pysepal.solara.components.aoi.aoi_view import AoiView


@solara.component
def AoiStep(state, sepal_map):
    """Area of interest selection. SHAPE/POINTS are excluded (container app)."""
    AoiView(
        value=state.aoi,
        methods=["-SHAPE", "-POINTS", "-DRAW"],
        gee=True,
        map_=sepal_map,
    )
