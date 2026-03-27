import solara


class BasinRiversState:
    """Reactive state for Upstream Watershed & Forest Stats."""

    def __init__(self):
        self.aoi = solara.reactive(None)
        self.lat = solara.reactive(None)
        self.lon = solara.reactive(None)
        self.level = solara.reactive(8)
        self.year_start = solara.reactive(2010)
        self.year_end = solara.reactive(2020)
        self.treecover = solara.reactive(80)
        self.selected_basins = solara.reactive([])
