import solara

from apps.basin_rivers.params import GFC_MAX_YEAR

_DEFAULT_YEAR_START = 2010
_DEFAULT_YEAR_END = 2000 + GFC_MAX_YEAR


class BasinRiversState:
    """Reactive state for Upstream Watershed & Forest Stats."""

    def __init__(self):
        # --- Outlet ---
        self.lat = solara.reactive(None)
        self.lon = solara.reactive(None)
        self.manual_coords = solara.reactive(False)

        # --- Basin parameters ---
        self.level = solara.reactive(8)
        self.year_start = solara.reactive(_DEFAULT_YEAR_START)
        self.year_end = solara.reactive(_DEFAULT_YEAR_END)
        self.treecover = solara.reactive(80)

        # --- Delineation results ---
        self.hybasin_list = solara.reactive([])
        self.method = solara.reactive("all")
        self.selected_basins = solara.reactive([])

        # --- GEE objects (held in memory, not serializable) ---
        self.upstream_fc = solara.reactive(None)
        self.forest_change = solara.reactive(None)

        # --- Statistics ---
        self.zonal_df = solara.reactive(None)

        # --- Task state ---
        self.loading = solara.reactive(False)

        # --- Dashboard state ---
        self.selected_var = solara.reactive("all")
        self.selected_hybasid_chart = solara.reactive([])
        self.sett_timespan = solara.reactive((_DEFAULT_YEAR_START, _DEFAULT_YEAR_END))
