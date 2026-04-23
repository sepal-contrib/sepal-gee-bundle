"""Reactive state for the JRC TMF app."""

import solara

from .params import TMF_MAX_YEAR, TMF_MIN_YEAR, TMF_TYPES


class TmfSepalState:
    """Flat reactive state for Tropical Moist Forests visualization."""

    def __init__(self):
        # Inputs
        self.aoi = solara.reactive(None)
        self.tmf_type = solara.reactive(TMF_TYPES[0]["value"])  # "DEG"
        self.year_start = solara.reactive(TMF_MIN_YEAR)
        self.year_end = solara.reactive(TMF_MAX_YEAR)
        self.scale = solara.reactive(30)

        # Outputs
        self.result_image = solara.reactive(None)
        self.loading = solara.reactive(False)
        self.stats_rows = solara.reactive([])
