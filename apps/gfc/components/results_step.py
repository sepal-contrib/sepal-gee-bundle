"""Results display and export step for GFC app."""

import logging
from dataclasses import dataclass

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.export import (
    ExportLauncher,
    ExportSource,
    ResolvedExport,
)
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.gfc.params import GFC_MAX_YEAR
from apps.gfc.scripts import compute_area_stats, parse_area_stats

from .dashboard_step import DashboardStep

logger = logging.getLogger("sepal_gee_bundle.gfc")


@dataclass(frozen=True, slots=True)
class StatsRequest:
    result_image: object  # ee.Image
    aoi_fc: object  # ee.FeatureCollection


@solara.component
def ResultsStep(state, sepal_map, gee_interface, legend_visible=None):
    """Area statistics, dashboard, and export controls."""
    notifications = use_notifications()
    stats_rows = state.stats_rows.value
    compute_cancel = solara.use_ref(None)

    # --- Compute stats task ---
    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def compute_task(request: StatsRequest):
        with notifications.track("Computing area statistics", total_steps=2) as task:
            task.step("Running reduceRegion on GEE")
            stats_obj = compute_area_stats(request.result_image, request.aoi_fc)
            raw = await gee_interface.get_info_async(stats_obj)
            task.step("Parsing results")
            return parse_area_stats(raw)

    def _sync_compute():
        if compute_task.pending or compute_task.cancelled:
            return
        if compute_task.error:
            notifications.error(f"Statistics failed: {compute_task.exception}")
            return
        if compute_task.finished and compute_task.value is not None:
            state.stats_rows.set(compute_task.value)
            logger.info("Area statistics computed: %d classes", len(compute_task.value))
            notifications.success(f"Area statistics computed ({len(compute_task.value)} classes)")

    solara.use_effect(
        _sync_compute,
        [compute_task.pending, compute_task.cancelled, compute_task.finished, compute_task.error],
    )

    def _start_compute():
        if state.result_image.value is None or state.aoi.value is None:
            notifications.warning("Run visualization first.")
            return
        compute_cancel.current = None
        state.stats_rows.set([])
        compute_task(
            StatsRequest(
                result_image=state.result_image.value,
                aoi_fc=state.aoi.value.feature_collection,
            )
        )

    compute_btn = use_task_button(
        compute_task, on_start=_start_compute, cancel_reason_ref=compute_cancel
    )

    # --- Export sources ---
    export_sources: tuple[ExportSource, ...] = ()
    if state.result_image.value is not None and state.aoi.value is not None:
        result_image = state.result_image.value
        aoi_fc = state.aoi.value.feature_collection
        treecover = state.treecover.value
        year_start = state.year_start.value
        year_end = state.year_end.value
        default_name = f"gfc_{treecover}_{year_start}_{year_end}"

        export_sources = (
            ExportSource(
                id="gfc_classified",
                label="GFC classified image",
                kind="image",
                resolve=lambda img=result_image, fc=aoi_fc, name=default_name: ResolvedExport(
                    ee_object=img,
                    default_name=name,
                    region=fc.geometry(),
                    default_scale=30,
                    gee_folder="gfc",
                    drive_folder="gfc_exports",
                    sepal_folder="gfc",
                    max_pixels=1e13,
                ),
            ),
            ExportSource(
                id="gfc_aoi",
                label="AOI boundary",
                kind="table",
                resolve=lambda fc=aoi_fc, name=default_name: ResolvedExport(
                    ee_object=fc,
                    default_name=f"{name}_aoi",
                    gee_folder="gfc",
                    drive_folder="gfc_exports",
                    sepal_folder="gfc",
                ),
            ),
        )

    # --- UI ---
    with solara.Column():
        TaskButtonComponent(
            label="Compute area statistics",
            **compute_btn,
            icon="mdi-chart-bar",
            external_busy=state.result_image.value is None,
            small=True,
            block=True,
        )

        if stats_rows:
            _StatsTable(stats_rows)

        DashboardStep(state, legend_visible=legend_visible, sepal_map=sepal_map)

        ExportLauncher(
            sources=export_sources,
            label="Export results",
            button_text=True,
            small=True,
            block=True,
            gee_interface=gee_interface,
        )


@solara.component
def _StatsTable(rows: list):
    """Display area statistics as a data table."""
    loss_rows = [r for r in rows if r["code"] <= GFC_MAX_YEAR]
    summary_rows = [r for r in rows if r["code"] > GFC_MAX_YEAR]

    total_loss = sum(r["area_ha"] for r in loss_rows)
    all_rows = [
        *summary_rows,
        {"code": 60, "label": "total loss", "area_ha": round(total_loss, 2)},
    ]

    headers = [
        {"text": "Class", "value": "label", "align": "start"},
        {"text": "Area (ha)", "value": "area_ha"},
    ]
    items = [{"label": r["label"], "area_ha": f"{r['area_ha']:,.0f}"} for r in all_rows]

    rv.DataTable(
        headers=headers,
        items=items,
        dense=True,
        disable_filtering=True,
        disable_sort=True,
        hide_default_footer=True,
        class_="mt-2",
    )
