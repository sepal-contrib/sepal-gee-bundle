"""Reactive state for the FCDM app."""

from __future__ import annotations

import solara

from apps.fcdm.params import (
    DEFAULT_CLEANING_OFFSET,
    DEFAULT_CLOUD_BUFFER,
    DEFAULT_FILTER_RADIUS,
    DEFAULT_FILTER_THRESHOLD,
    DEFAULT_KERNEL_RADIUS,
    DEFAULT_TREECOVER,
)


class FcdmState:
    """Flat reactive state for Forest Canopy Disturbance Monitoring."""

    def __init__(self):
        # AOI (AoiResult from pysepal AoiView)
        self.aoi = solara.reactive(None)

        # Time ranges (ISO YYYY-MM-DD strings) — default to a recent
        # reference / analysis pair so users see live dates, not blanks.
        self.reference_start = solara.reactive("2024-01-01")
        self.reference_end = solara.reactive("2024-12-31")
        self.analysis_start = solara.reactive("2025-01-01")
        self.analysis_end = solara.reactive("2025-12-31")

        # Sensors (list of sensor keys)
        self.sensors = solara.reactive([])

        # Forest mask config
        self.forest_map = solara.reactive("gfc")
        self.forest_map_year = solara.reactive(2024)
        self.treecover = solara.reactive(DEFAULT_TREECOVER)
        self.forest_map_asset = solara.reactive("")  # custom binary asset id

        # Algorithm params
        self.cloud_buffer = solara.reactive(DEFAULT_CLOUD_BUFFER)
        self.kernel_radius = solara.reactive(DEFAULT_KERNEL_RADIUS)
        self.filter_threshold = solara.reactive(DEFAULT_FILTER_THRESHOLD)
        self.filter_radius = solara.reactive(DEFAULT_FILTER_RADIUS)
        self.cleaning_offset = solara.reactive(DEFAULT_CLEANING_OFFSET)

        # Result (FcdmResult instance) and loading flag
        self.result = solara.reactive(None)
        self.loading = solara.reactive(False)
