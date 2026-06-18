"""Save-to-disk controls and syntax-highlighted source preview."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import ipyvuetify as v
import reacton.ipyvuetify as rv
import solara
import traitlets
from pysepal.solara import get_current_sepal_client
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.gee_source.scripts import sanitize_filename, save_code
from apps.gee_source.scripts.highlight import highlight_css


class _ClipboardCopier(v.VuetifyTemplate):
    """Invisible widget that copies `payload` to the browser clipboard.

    Incrementing ``nonce`` re-triggers the copy even if ``payload`` is unchanged.
    """

    payload = traitlets.Unicode("").tag(sync=True)
    nonce = traitlets.Int(0).tag(sync=True)
    template = traitlets.Unicode(
        """
<template>
  <span style="display:none"></span>
</template>

<script>
module.exports = {
  watch: {
    nonce: function () {
      var text = this.payload || "";
      if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).catch(function () {});
        return;
      }
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "absolute";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      } catch (e) {}
    },
  },
};
</script>
        """
    ).tag(sync=True)


logger = logging.getLogger("sepal_gee_bundle.gee_source")


@dataclass(frozen=True, slots=True)
class SaveRequest:
    code: str
    filename: str


@solara.component
def SaveControls(state):
    """Filename field + Save/Copy buttons. Intended for the inputs column."""
    notifications = use_notifications()
    cancel_reason = solara.use_ref(None)
    has_code = bool(state.raw_code.value)
    clipboard = solara.use_memo(lambda: _ClipboardCopier(), [])
    sepal_client = get_current_sepal_client()
    result_path = getattr(sepal_client, "results_path", "your SEPAL module results folder")

    def _copy_to_clipboard():
        if not has_code:
            notifications.warning("Nothing to copy — extract a source first.")
            return
        clipboard.payload = state.raw_code.value
        clipboard.nonce = clipboard.nonce + 1
        notifications.success("JavaScript copied to clipboard.")

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def save_task(request: SaveRequest):
        path = await asyncio.to_thread(
            save_code, request.code, request.filename, sepal_client=sepal_client
        )
        return str(path)

    def _sync():
        if save_task.pending or save_task.cancelled:
            return
        if save_task.error:
            notifications.error(f"Could not save file: {save_task.exception}")
            return
        if save_task.finished and save_task.value is not None:
            state.saved_path.set(save_task.value)
            notifications.success(f"Saved to {save_task.value}")

    solara.use_effect(
        _sync,
        [save_task.pending, save_task.cancelled, save_task.finished, save_task.error],
    )

    def _start_save():
        if not has_code:
            notifications.warning("Nothing to save — extract a source first.")
            return
        if sepal_client is None:
            notifications.error("SEPAL session is not available; cannot save user files.")
            return
        cleaned = sanitize_filename(state.filename.value or "")
        state.filename.set(cleaned)
        cancel_reason.current = None
        save_task(SaveRequest(code=state.raw_code.value, filename=cleaned))

    btn_props = use_task_button(save_task, on_start=_start_save, cancel_reason_ref=cancel_reason)

    with solara.Column(gap="8px"):
        rv.TextField(
            v_model=state.filename.value,
            on_v_model=state.filename.set,
            label="Filename (no extension)",
            hint=f"Will be saved as <name>.js under {result_path}",
            persistent_hint=True,
            outlined=True,
            dense=True,
            disabled=not has_code,
            prepend_inner_icon="mdi-file-document-outline",
        )

        TaskButtonComponent(
            label="Save to SEPAL",
            **btn_props,
            external_busy=not has_code,
            small=True,
            block=True,
        )

        solara.Button(
            label="Copy to clipboard",
            on_click=_copy_to_clipboard,
            disabled=not has_code,
            color="primary",
            outlined=True,
            small=True,
            block=True,
        )

        # Invisible widget that actually performs the JS clipboard call.
        rv.Html(tag="span", children=[clipboard])


@solara.component
def SourcePreview(state):
    """Render the pygments-highlighted source.

    Empty-state messaging is handled by the central iframe placeholder, so
    this component renders nothing when there is no extracted code.
    """
    if not state.raw_code.value:
        return
    with solara.Column():
        solara.HTML(tag="style", unsafe_innerHTML=highlight_css())
        solara.HTML(tag="div", unsafe_innerHTML=state.highlighted_html.value)


@solara.component
def OutputStep(state):
    """Backward-compatible shim: renders save controls followed by the preview."""
    SaveControls(state)
    SourcePreview(state)
