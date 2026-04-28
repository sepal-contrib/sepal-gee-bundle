"""Run and export step for FCDM."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import solara
from pysepal.solara.components.export import (
    ExportLauncher,
    ExportSource,
    ResolvedExport,
)
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.fcdm.params import (
    DELTA_NBR_VIS,
    LAYER_ANALYSIS_RNBR,
    LAYER_AOI,
    LAYER_DELTA_RNBR,
    LAYER_FOREST_MASK,
    LAYER_REFERENCE_RNBR,
    viz_forest_mask,
)
from apps.fcdm.scripts.nbr_pipeline import run_fcdm

logger = logging.getLogger("sepal_gee_bundle.fcdm")


@dataclass(frozen=True, slots=True)
class RunRequest:
    aoi_fc: object
    sensors: tuple
    reference_start: str
    reference_end: str
    analysis_start: str
    analysis_end: str
    forest_map: str
    forest_map_year: int
    treecover: int
    cloud_buffer: float
    kernel_radius: float
    filter_threshold: float
    filter_radius: float
    cleaning_offset: int


def _validate_inputs(state) -> str | None:
    """Return an error message or None if inputs are valid."""
    if state.aoi.value is None:
        return "Please select an Area of Interest first."
    if not state.sensors.value:
        return "Select at least one sensor."
    if state.forest_map.value == "custom" and not state.forest_map_asset.value:
        return "Select a custom GEE asset for the forest mask."
    for label, v in (
        ("Reference start", state.reference_start.value),
        ("Reference end", state.reference_end.value),
        ("Analysis start", state.analysis_start.value),
        ("Analysis end", state.analysis_end.value),
    ):
        if not v or len(v) < 10:
            return f"{label} date is required (YYYY-MM-DD)."
    return None


@solara.component
def RunStep(state, sepal_map, gee_interface):
    """Run the Delta-rNBR pipeline, display layers, and expose exports."""
    notifications = use_notifications()
    cancel_ref = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def run_task(request: RunRequest):
        with notifications.track("Running FCDM pipeline", total_steps=4) as task:
            task.step("Building GEE graph")
            result = run_fcdm(
                aoi=request.aoi_fc,
                sensors=list(request.sensors),
                reference_start=request.reference_start,
                reference_end=request.reference_end,
                analysis_start=request.analysis_start,
                analysis_end=request.analysis_end,
                forest_map=request.forest_map,
                forest_map_year=request.forest_map_year,
                treecover=request.treecover,
                cloud_buffer=request.cloud_buffer,
                kernel_radius=request.kernel_radius,
                filter_threshold=request.filter_threshold,
                filter_radius=request.filter_radius,
                cleaning_offset=request.cleaning_offset,
            )

            task.step("Clearing previous FCDM layers")
            for name in (
                LAYER_AOI,
                LAYER_FOREST_MASK,
                LAYER_REFERENCE_RNBR,
                LAYER_ANALYSIS_RNBR,
                LAYER_DELTA_RNBR,
            ):
                sepal_map.remove_layer(name, none_ok=True)

            task.step("Adding AOI and forest mask")
            await sepal_map.add_ee_layer_async(
                request.aoi_fc,
                {"color": "#1976d2"},
                LAYER_AOI,
                autocenter=True,
            )
            await sepal_map.add_ee_layer_async(
                result.forest_mask_display,
                viz_forest_mask(request.forest_map),
                LAYER_FOREST_MASK,
            )

            task.step("Rendering Delta-rNBR on the map")
            await sepal_map.add_ee_layer_async(
                result.delta_rnbr.select("NBR"),
                DELTA_NBR_VIS,
                LAYER_DELTA_RNBR,
            )
            return result

    def _sync_run():
        state.loading.value = run_task.pending
        if run_task.pending or run_task.cancelled:
            return
        if run_task.error:
            notifications.error(f"FCDM failed: {run_task.exception}")
            return
        if run_task.finished and run_task.value is not None:
            state.result.value = run_task.value
            notifications.success("Delta-rNBR layer added to map")

    solara.use_effect(
        _sync_run,
        [run_task.pending, run_task.cancelled, run_task.finished, run_task.error],
    )

    def _start_run():
        error = _validate_inputs(state)
        if error:
            notifications.warning(error)
            return
        cancel_ref.current = None
        state.loading.value = True
        state.result.value = None
        # Translate the UI "custom" sentinel into the asset id so the pipeline's
        # get_forest_mask() falls through to its ee.Image(asset_id) branch.
        forest_map_value = (
            state.forest_map_asset.value
            if state.forest_map.value == "custom"
            else state.forest_map.value
        )
        run_task(
            RunRequest(
                aoi_fc=state.aoi.value.feature_collection,
                sensors=tuple(state.sensors.value),
                reference_start=state.reference_start.value,
                reference_end=state.reference_end.value,
                analysis_start=state.analysis_start.value,
                analysis_end=state.analysis_end.value,
                forest_map=forest_map_value,
                forest_map_year=state.forest_map_year.value,
                treecover=state.treecover.value,
                cloud_buffer=state.cloud_buffer.value,
                kernel_radius=state.kernel_radius.value,
                filter_threshold=state.filter_threshold.value,
                filter_radius=state.filter_radius.value,
                cleaning_offset=state.cleaning_offset.value,
            )
        )

    btn_props = use_task_button(run_task, on_start=_start_run, cancel_reason_ref=cancel_ref)

    # --- Export sources (only available once a result exists) ---
    export_sources: tuple[ExportSource, ...] = ()
    result = state.result.value
    if result is not None and state.aoi.value is not None:
        aoi_fc = state.aoi.value.feature_collection
        region = aoi_fc.geometry()
        prefix = (
            f"fcdm_{state.reference_start.value[:4]}-{state.reference_end.value[:4]}"
            f"_{state.analysis_start.value[:4]}-{state.analysis_end.value[:4]}"
        )

        def _mk(id_, label, image, scale=30, suffix=""):
            return ExportSource(
                id=id_,
                label=label,
                kind="image",
                resolve=lambda img=image, fc=region, name=f"{prefix}_{suffix or id_}", s=scale: (
                    ResolvedExport(
                        ee_object=img,
                        default_name=name,
                        region=fc,
                        default_scale=s,
                        gee_folder="fcdm",
                        drive_folder="fcdm_exports",
                        sepal_folder="fcdm",
                        max_pixels=1e13,
                    )
                ),
            )

        export_sources = (
            _mk("delta_rnbr", "Delta rNBR (DDR filtered)", result.delta_rnbr, suffix="delta_rnbr"),
            _mk(
                "delta_rnbr_raw",
                "Delta rNBR (no DDR filter)",
                result.delta_rnbr_raw,
                suffix="delta_rnbr_raw",
            ),
            _mk("reference_rnbr", "Reference rNBR", result.reference_rnbr, suffix="reference_rnbr"),
            _mk("analysis_rnbr", "Analysis rNBR", result.analysis_rnbr, suffix="analysis_rnbr"),
            _mk("forest_mask", "Forest mask", result.forest_mask, suffix="forest_mask"),
        )

    with solara.Column():
        TaskButtonComponent(
            label="Run FCDM",
            **btn_props,
            icon="mdi-play",
            external_busy=state.aoi.value is None or not state.sensors.value,
            small=True,
            block=True,
        )

        ExportLauncher(
            sources=export_sources,
            label="Export layers",
            icon="mdi-cloud-download",
            button_text=True,
            small=True,
            block=True,
            gee_interface=gee_interface,
        )
