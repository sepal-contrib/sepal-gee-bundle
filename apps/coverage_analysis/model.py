"""Reactive state for the Coverage Analysis app."""

import solara

from apps.coverage_analysis.params import (
    DEFAULT_END,
    DEFAULT_MEASURE,
    DEFAULT_START,
)


class CoverageState:
    """Flat reactive state bag for Coverage Analysis."""

    def __init__(self) -> None:
        # AOI
        self.aoi = solara.reactive(None)

        # Selection
        self.start_date = solara.reactive(DEFAULT_START)
        self.end_date = solara.reactive(DEFAULT_END)
        self.sensors = solara.reactive(["l8"])
        self.surface_reflectance = solara.reactive(True)
        self.include_tier2 = solara.reactive(False)

        # Visualization
        self.measure = solara.reactive(DEFAULT_MEASURE)
        self.annual = solara.reactive(False)

        # Export
        self.stats = solara.reactive(["count"])
        self.temps = solara.reactive(["total_exp"])

        # Results
        self.collection = solara.reactive(None)  # ee.ImageCollection
        self.result_image = solara.reactive(None)  # ee.Image (last visualized composite)
        self.result_band_names = solara.reactive([])
        self.loading = solara.reactive(False)

        # Dashboard stats — dict with keys:
        #   per_sensor: list[{"sensor": str, "count": int}]
        #   per_year:   list[{"year": int, "count": int}]
        #   totals:     dict (aoi_area_ha, total_count, date_range, sensors, measure)
        self.dashboard_stats = solara.reactive(None)
