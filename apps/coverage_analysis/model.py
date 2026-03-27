import solara


class CoverageState:
    """Reactive state for Satellite Coverage Analysis."""

    def __init__(self):
        self.aoi = solara.reactive(None)
        self.start_date = solara.reactive(None)
        self.end_date = solara.reactive(None)
        self.sensors = solara.reactive([])
        self.surface_reflectance = solara.reactive(True)
        self.include_tier2 = solara.reactive(False)
        self.measure = solara.reactive("pixel_count")
        self.annual = solara.reactive(False)
