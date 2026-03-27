import solara


class GfcState:
    """Reactive state for Global Forest Change."""

    def __init__(self):
        self.aoi = solara.reactive(None)
        self.treecover = solara.reactive(70)
        self.year = solara.reactive(2020)
        self.forest_map_asset = solara.reactive(None)
