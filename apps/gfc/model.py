import solara


class GfcState:
    """Reactive state for Global Forest Change."""

    def __init__(self):
        self.aoi = solara.reactive(None)
        self.treecover = solara.reactive(30)
        self.year_start = solara.reactive(2001)
        self.year_end = solara.reactive(2024)
        self.result_image = solara.reactive(None)
