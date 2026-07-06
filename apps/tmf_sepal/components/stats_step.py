"""Area statistics step for the TMF app.

Computes class-wise / year-wise area (ha) for the visualized TMF image and
renders a compact data table. The charts live in the dashboard modal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.tmf_sepal.scripts import compute_area_stats, parse_area_stats

from .dashboard_step import DashboardStep

logger = logging.getLogger("sepal_gee_bundle.tmf_sepal")


@dataclass(frozen=True, slots=True)
class StatsRequest:
    result_image: object  # ee.Image
    aoi_fc: object  # ee.FeatureCollection
    tmf_type: str
    year_end: int
    scale: int


@solara.component
def StatsStep(state, gee_interface, legend_visible=None, sepal_map=None):
    """Compute area statistics + render a data table (charts live in the dashboard)."""
    notifications = use_notifications()
    cancel_ref = solara.use_ref(None)
    stats_rows = state.stats_rows.value

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def compute_task(request: StatsRequest):
        with notifications.track("Computing TMF area statistics", total_steps=2) as task:
            task.step("Running reduceRegion on GEE")
            stats_obj = compute_area_stats(
                request.result_image,
                request.aoi_fc,
                request.tmf_type,
                request.year_end,
                scale=request.scale,
            )
            raw = await gee_interface.get_info_async(stats_obj)
            task.step("Parsing results")
            return parse_area_stats(raw, request.tmf_type)

    def _sync_compute():
        if compute_task.pending or compute_task.cancelled:
            return
        if compute_task.error:
            notifications.error(f"Statistics failed: {compute_task.exception}")
            return
        if compute_task.finished and compute_task.value is not None:
            state.stats_rows.set(compute_task.value)
            logger.info("TMF area statistics computed: %d rows", len(compute_task.value))
            notifications.success(f"Area statistics computed ({len(compute_task.value)} classes)")

    solara.use_effect(
        _sync_compute,
        [compute_task.pending, compute_task.cancelled, compute_task.finished, compute_task.error],
    )

    def _start_compute():
        if state.result_image.value is None or state.aoi.value is None:
            notifications.warning("Visualize a TMF layer first.")
            return
        cancel_ref.current = None
        state.stats_rows.set([])
        compute_task(
            StatsRequest(
                result_image=state.result_image.value,
                aoi_fc=state.aoi.value.feature_collection,
                tmf_type=state.tmf_type.value,
                year_end=state.year_end.value,
                scale=state.scale.value,
            )
        )

    btn_props = use_task_button(compute_task, on_start=_start_compute, cancel_reason_ref=cancel_ref)

    with solara.Column():
        TaskButtonComponent(
            label="Compute area statistics",
            **btn_props,
            external_busy=state.result_image.value is None,
            small=True,
            block=True,
        )

        if stats_rows:
            _StatsTable(stats_rows, state.tmf_type.value)

        DashboardStep(state, legend_visible=legend_visible, sepal_map=sepal_map)


@solara.component
def _StatsTable(rows: list, tmf_type: str):
    """Data table of raw area numbers."""
    col_header = "Class" if tmf_type == "CHG" else "Year"
    headers = [
        {"text": col_header, "value": "label", "align": "start"},
        {"text": "Area (ha)", "value": "area_ha"},
    ]
    items = [{"label": r["label"], "area_ha": f"{r['area_ha']:,.0f}"} for r in rows]
    rv.DataTable(
        headers=headers,
        items=items,
        dense=True,
        disable_filtering=True,
        disable_sort=True,
        hide_default_footer=True,
        class_="mt-2",
    )
