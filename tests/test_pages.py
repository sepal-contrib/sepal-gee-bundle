"""Smoke test: every app's Page renders the native MapApp shell headless."""

import importlib
import sys
from unittest.mock import MagicMock, patch

import ipyvuetify as v
import pytest
import solara
from pysepal.solara.session_manager import SessionManager

PAGES = [
    ("alos_mosaics", "AlosMosaicsPage"),
    ("basin_rivers", "BasinRiversPage"),
    ("coverage_analysis", "CoverageAnalysisPage"),
    ("fcdm", "FcdmPage"),
    ("gee_source", "GeeSourcePage"),
    ("gfc", "GfcPage"),
    ("tmf_sepal", "TmfSepalPage"),
]


def _walk(widget):
    yield widget
    children = list(getattr(widget, "children", ()) or ())
    for slot in getattr(widget, "v_slots", None) or []:
        slot_children = slot.get("children")
        children += slot_children if isinstance(slot_children, list) else [slot_children]
    for child in children:
        if child is not None and not isinstance(child, str):
            yield from _walk(child)


@pytest.fixture
def session(mock_gee_interface, monkeypatch):
    # test_asgi imports solara.server.starlette, and solara then takes the whole
    # process for a server whose renders need a kernel context.
    monkeypatch.delitem(sys.modules, "solara.server.starlette", raising=False)
    with (
        patch.object(SessionManager, "create_session"),
        patch.object(SessionManager, "get_gee_interface", return_value=mock_gee_interface),
        patch.object(SessionManager, "get_sepal_client", return_value=None),
        patch.object(SessionManager, "get_drive_interface", return_value=MagicMock()),
    ):
        yield


# Async so the components' use_task finds a running loop.
@pytest.mark.asyncio
@pytest.mark.parametrize(("app", "page_name"), PAGES)
async def test_page_renders_the_map_app(session, app, page_name):
    page = getattr(importlib.import_module(f"apps.{app}.page"), page_name)

    box, rc = solara.render(page(), handle_error=False)
    try:
        tree = list(_walk(box))
        # with_sepal_sessions turns a render error into an error alert.
        errors = [w for w in tree if isinstance(w, v.Alert) and w.type == "error"]
        assert not errors
        assert any("sepal-mapapp" in (getattr(w, "class_", None) or "").split() for w in tree)
    finally:
        rc.close()
