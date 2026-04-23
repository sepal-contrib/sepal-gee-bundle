import logging

import solara
from pysepal.logger import setup_logging
from pysepal.solara import setup_sessions, setup_solara_server

from apps.alos_mosaics.page import AlosMosaicsPage
from apps.basin_rivers.page import BasinRiversPage
from apps.coverage_analysis.page import CoverageAnalysisPage
from apps.fcdm.page import FcdmPage
from apps.gee_source.page import GeeSourcePage
from apps.gfc.page import GfcPage
from apps.tmf_sepal.page import TmfSepalPage

logger = setup_logging(logger_name="sepal_gee_bundle")
logger.setLevel(logging.DEBUG)
logger.debug("sepal-gee-bundle initialized")
logger.debug("Solara version: %s", solara.__version__)

setup_solara_server()


@solara.lab.on_kernel_start
def on_kernel_start():
    return setup_sessions()


@solara.component
def NoNavLayout(children=[]):
    """Render children directly — no navigation bar, no tabs."""
    solara.Column(children=children, style={"padding": "0", "margin": "0"})


APPS = [
    ("gfc", "Global Forest Change", "Hansen forest mask visualization and export"),
    ("basin-rivers", "Basin Rivers", "Upstream watershed delineation + per-basin forest change stats"),
    ("fcdm", "Forest Canopy Disturbance Monitoring", "Delta-NBR spectral change detection"),
    ("coverage-analysis", "Coverage Analysis", "Landsat / Sentinel-2 coverage and NDVI statistics"),
    ("tmf-sepal", "Tropical Moist Forests", "JRC TMF degradation / deforestation / annual change"),
    ("alos-mosaics", "ALOS Mosaics", "ALOS PALSAR yearly mosaics and forest / non-forest"),
    ("gee-source", "GEE Source", "Extract JavaScript source from a public Earth Engine App"),
]


@solara.component
def IndexPage():
    with solara.Column(style={"padding": "32px", "max-width": "720px"}):
        solara.Markdown("# sepal-gee-bundle")
        solara.Markdown("Pick an app:")
        for path, name, description in APPS:
            with solara.Row(style={"gap": "8px", "align-items": "baseline"}):
                solara.Markdown(f"- [**{name}**]({path})")
                solara.Markdown(f"— {description}")


routes = [
    solara.Route(path="/", component=IndexPage, layout=NoNavLayout),
    solara.Route(path="fcdm", component=FcdmPage, layout=NoNavLayout),
    solara.Route(path="basin-rivers", component=BasinRiversPage, layout=NoNavLayout),
    solara.Route(path="gfc", component=GfcPage, layout=NoNavLayout),
    solara.Route(path="coverage-analysis", component=CoverageAnalysisPage, layout=NoNavLayout),
    solara.Route(path="tmf-sepal", component=TmfSepalPage, layout=NoNavLayout),
    solara.Route(path="gee-source", component=GeeSourcePage, layout=NoNavLayout),
    solara.Route(path="alos-mosaics", component=AlosMosaicsPage, layout=NoNavLayout),
]
