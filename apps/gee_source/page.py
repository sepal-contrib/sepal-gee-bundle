"""GEE Source — extract JavaScript from Earth Engine Apps URLs."""

import logging

import solara
from pysepal.logger import setup_logging
from pysepal.solara import setup_theme_colors, with_sepal_sessions
from pysepal.solara.notifications import NotificationProvider

from .components import ExtractStep, SaveControls, SourcePreview
from .model import GeeSourceState

logger = setup_logging(logger_name="sepal_gee_bundle.gee_source")
logger.setLevel(logging.DEBUG)
logger.debug("GEE Source app initialized")


@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.gee_source")
def GeeSourcePage():
    """GEE Source — extract JavaScript from Earth Engine Apps URLs."""
    setup_theme_colors()
    NotificationProvider()

    state = solara.use_memo(lambda: GeeSourceState(), [])

    with solara.Column(
        style={"padding": "24px", "max-width": "960px", "margin": "0 auto"},
        gap="16px",
    ):
        solara.Markdown(
            "## GEE Source\n"
            "Paste a public Earth Engine App URL "
            "(`https://<user>.users.earthengine.app/view/<app>`) "
            "to extract its JavaScript source."
        )

        ExtractStep(state)

        if state.raw_code.value:
            SaveControls(state)
            SourcePreview(state)
