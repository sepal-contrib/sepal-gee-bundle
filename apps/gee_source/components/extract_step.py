"""URL input + extract button for the GEE Source app."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.gee_source.scripts import (
    extract_js_source,
    highlight_javascript,
    sanitize_filename,
)

logger = logging.getLogger("sepal_gee_bundle.gee_source")


def _suggest_filename(app_url: str) -> str:
    """Build a filename suggestion from an Earth Engine App URL."""
    tail = urlparse(app_url).path.rstrip("/").rsplit("/", 1)[-1]
    return sanitize_filename(tail or app_url)


@dataclass(frozen=True, slots=True)
class ExtractRequest:
    app_url: str


@solara.component
def ExtractStep(state):
    """Render the URL field + ``Extract`` action.

    On success, ``state.raw_code``, ``state.highlighted_html`` and
    ``state.filename`` are populated. On failure a notification toast is
    shown and state is left empty.
    """
    notifications = use_notifications()
    cancel_reason = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def extract_task(request: ExtractRequest):
        with notifications.track("Extracting Earth Engine App source", total_steps=2) as task:
            task.step("Fetching app page")
            raw = await asyncio.to_thread(extract_js_source, request.app_url)

            task.step("Highlighting source")
            html = highlight_javascript(raw) if raw else ""

        suggested = _suggest_filename(request.app_url)
        return raw, html, suggested

    def _sync():
        if extract_task.pending or extract_task.cancelled:
            return
        if extract_task.error:
            notifications.error(f"Extraction failed: {extract_task.exception}")
            return
        if extract_task.finished and extract_task.value is not None:
            raw, html, suggested = extract_task.value
            state.raw_code.set(raw)
            state.highlighted_html.set(html)
            state.filename.set(suggested)
            state.saved_path.set("")
            state.live_url.set((state.app_url.value or "").strip())
            if not raw:
                notifications.warning(
                    "No JavaScript source was found on that page — is it a public Earth Engine App?"
                )
            else:
                notifications.success("Source extracted.")

    solara.use_effect(
        _sync,
        [
            extract_task.pending,
            extract_task.cancelled,
            extract_task.finished,
            extract_task.error,
        ],
    )

    def _start():
        url = (state.app_url.value or "").strip()
        if not url:
            notifications.warning("Please paste an Earth Engine App URL.")
            return
        if not url.startswith("https://"):
            notifications.warning("URL must start with https://")
            return
        cancel_reason.current = None
        state.raw_code.set("")
        state.highlighted_html.set("")
        state.saved_path.set("")
        extract_task(ExtractRequest(app_url=url))

    btn_props = use_task_button(extract_task, on_start=_start, cancel_reason_ref=cancel_reason)

    def _on_url_change(value):
        new_value = value or ""
        state.app_url.set(new_value)
        if not new_value.strip():
            state.raw_code.set("")
            state.highlighted_html.set("")
            state.filename.set("")
            state.saved_path.set("")
            state.live_url.set("")
            state.view_mode.set("app")

    with solara.Column(gap="8px"):
        rv.TextField(
            v_model=state.app_url.value,
            on_v_model=_on_url_change,
            label="Earth Engine App URL",
            placeholder="https://<user>.users.earthengine.app/view/<app>",
            outlined=True,
            dense=True,
            clearable=True,
            prepend_inner_icon="mdi-link-variant",
        )

        TaskButtonComponent(
            label="Extract source",
            **btn_props,
            external_busy=not (state.app_url.value or "").strip(),
            small=True,
            block=True,
        )
