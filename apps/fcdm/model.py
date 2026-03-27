import solara


class FcdmState:
    """Reactive state for Forest Canopy Disturbance Monitoring."""

    def __init__(self):
        self.aoi = solara.reactive(None)
        self.reference_start = solara.reactive(None)
        self.reference_end = solara.reactive(None)
        self.analysis_start = solara.reactive(None)
        self.analysis_end = solara.reactive(None)
        self.sensors = solara.reactive([])
        self.cloud_buffer = solara.reactive(500)
        self.forest_map = solara.reactive("gfc")
        self.treecover = solara.reactive(70)
        self.kernel_radius = solara.reactive(150)
        self.filter_threshold = solara.reactive(0.035)
        self.filter_radius = solara.reactive(80)
        self.cleaning_offset = solara.reactive(3)
