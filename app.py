import logging

import solara
from pysepal.logger import setup_logging
from pysepal.solara import setup_sessions, setup_solara_server

from apps.basin_rivers.page import BasinRiversPage
from apps.coverage_analysis.page import CoverageAnalysisPage
from apps.fcdm.page import FcdmPage
from apps.gfc.page import GfcPage

logger = setup_logging(logger_name="sepal_gee_bundle")
logger.setLevel(logging.DEBUG)
logger.debug("sepal-gee-bundle initialized")
logger.debug("Solara version: %s", solara.__version__)

setup_solara_server()


@solara.lab.on_kernel_start
def on_kernel_start():
    return setup_sessions()


routes = [
    solara.Route(path="fcdm", component=FcdmPage, label="FCDM"),
    solara.Route(path="basin-rivers", component=BasinRiversPage, label="Basin Rivers"),
    solara.Route(path="gfc", component=GfcPage, label="GFC"),
    solara.Route(
        path="coverage-analysis",
        component=CoverageAnalysisPage,
        label="Coverage Analysis",
    ),
]
