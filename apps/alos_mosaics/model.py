"""Reactive state for the ALOS mosaics app."""

import solara

from .params import SPECKLE_NONE, VIZ_RGB


class AlosMosaicsState:
    """Flat reactive state for ALOS PALSAR / PALSAR-2 yearly mosaics."""

    def __init__(self):
        # AOI
        self.aoi = solara.reactive(None)

        # Processing parameters
        self.year = solara.reactive(2020)
        self.speckle_filter = solara.reactive(SPECKLE_NONE)
        self.ls_mask = solara.reactive(True)
        self.db = solara.reactive(True)

        # Visualization selector
        self.viz_layer = solara.reactive(VIZ_RGB)

        # Export toggles
        self.export_backscatter = solara.reactive(True)
        self.export_rfdi = solara.reactive(True)
        self.export_texture = solara.reactive(False)
        self.export_aux = solara.reactive(False)
        self.export_fnf = solara.reactive(False)

        # Outputs
        self.result_image = solara.reactive(None)  # ee.Image from build_alos_mosaic
        self.loading = solara.reactive(False)
