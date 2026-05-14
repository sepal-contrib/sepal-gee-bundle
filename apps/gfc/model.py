import solara

from apps.gfc.params import GFC_MAX_YEAR


class GfcState:
    """Reactive state for Global Forest Change."""

    def __init__(self):
        self.aoi = solara.reactive(None)
        self.treecover = solara.reactive(30)
        self.year_start = solara.reactive(2001)
        self.year_end = solara.reactive(2000 + GFC_MAX_YEAR)
        self.result_image = solara.reactive(None)
        self.loading = solara.reactive(False)
        self.stats_rows = solara.reactive([])
