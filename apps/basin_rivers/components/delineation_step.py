"""Upstream delineation. Trace watershed + add map layers.

Statistics computation and dashboard live in `dashboard_step.py` — the
dashboard button runs the zonal stats on demand.
"""

import logging
from dataclasses import asdict as _asdict
from dataclasses import dataclass

import ee
import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.export import (
    ExportLauncher,
    ExportSource,
    ResolvedExport,
)
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.basin_rivers.params import (
    BASIN_WARN_THRESHOLD,
    GFC_LEGEND,
    SLD_INTERVALS,
)
from apps.basin_rivers.scripts import (
    classify_gfc,
    get_upstream_basin_ids,
)
from apps.basin_rivers.scripts.visualization import create_basins_layer

from .dashboard_step import DashboardStep

logger = logging.getLogger("sepal_gee_bundle.basin_rivers")


@dataclass(frozen=True, slots=True)
class TraceRequest:
    lat: float
    lon: float
    level: int
    year_start: int
    year_end: int
    treecover: int


@solara.component
def DelineationStep(
    state,
    sepal_map,
    gee_interface,
    legend_data=None,
    legend_visible=None,
):
    """Trace upstream basins and add the GFC classification layer to the map."""
    notifications = use_notifications()
    trace_cancel = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def trace_task(request: TraceRequest):
        with notifications.track("Tracing upstream watershed", total_steps=4) as task:
            task.step("Validating pour point...")
            geometry = ee.Geometry.Point([request.lon, request.lat])

            task.step("Tracing upstream basins...")
            upstream_fc, hybas_ids = await get_upstream_basin_ids(
                gee_interface, request.level, geometry
            )
            geojson_data = await gee_interface.get_info_async(upstream_fc)

            task.step("Classifying GFC forest change...")
            gfc_image = classify_gfc(
                upstream_fc, request.treecover, request.year_start, request.year_end
            )

            task.step("Rendering map layer...")
            gfc_layer = "GFC forest change"
            existing = sepal_map.find_layer(gfc_layer, none_ok=True)
            if existing:
                sepal_map.remove_layer(existing)
            await sepal_map.add_ee_layer_async(gfc_image.sldStyle(SLD_INTERVALS), {}, gfc_layer)

        return {
            "upstream_fc": upstream_fc,
            "hybas_ids": hybas_ids,
            "gfc_image": gfc_image,
            "geojson_data": geojson_data,
        }

    def _sync_trace():
        state.loading.value = trace_task.pending
        if trace_task.pending:
            return
        if trace_task.cancelled:
            notifications.info("Trace cancelled.")
            return
        if trace_task.error:
            notifications.error(f"Trace failed: {trace_task.exception}")
            return
        if trace_task.finished and trace_task.value is not None:
            result = trace_task.value
            state.hybasin_list.value = result["hybas_ids"]
            state.upstream_fc.value = result["upstream_fc"]
            state.forest_change.value = result["gfc_image"]
            state.selected_basins.value = result["hybas_ids"]

            existing = sepal_map.find_layer("Upstream catchment", none_ok=True)
            if existing:
                sepal_map.remove_layer(existing)
            basins_layer = create_basins_layer(result["geojson_data"])
            sepal_map.add_layer(basins_layer, key="Upstream catchment")

            from geopandas import GeoDataFrame

            gdf = GeoDataFrame.from_features(result["geojson_data"]["features"])
            if not gdf.empty:
                sepal_map.zoom_bounds(gdf.total_bounds)

            if legend_data is not None:
                legend_data.set(_asdict(GFC_LEGEND))
            if legend_visible is not None:
                legend_visible.set(True)

            n_basins = len(result["hybas_ids"])
            if n_basins > BASIN_WARN_THRESHOLD:
                notifications.warning(
                    f"Watershed has {n_basins} upstream basins — that's a lot. "
                    f"Consider a lower HydroSHEDS level for larger (fewer) basins."
                )
            else:
                notifications.success(f"Watershed traced: {n_basins} upstream basins")
            logger.info("Delineation complete: %d basins", n_basins)

    solara.use_effect(
        _sync_trace,
        [
            trace_task.pending,
            trace_task.finished,
            trace_task.error,
            trace_task.cancelled,
        ],
    )

    def _valid_year_range() -> bool:
        if state.year_start.value > state.year_end.value:
            notifications.warning(
                f"Invalid year range: start ({state.year_start.value}) is after "
                f"end ({state.year_end.value})."
            )
            return False
        return True

    def _start_trace():
        if state.lat.value is None or state.lon.value is None:
            notifications.warning("Select a pour point first.")
            return
        if not _valid_year_range():
            return
        trace_cancel.current = None
        state.hybasin_list.value = []
        state.zonal_df.value = None
        if legend_visible is not None:
            legend_visible.set(False)
        for _layer_key in ("GFC forest change", "Upstream catchment"):
            existing = sepal_map.find_layer(_layer_key, none_ok=True)
            if existing:
                sepal_map.remove_layer(existing)
        trace_task(
            TraceRequest(
                lat=state.lat.value,
                lon=state.lon.value,
                level=state.level.value,
                year_start=state.year_start.value,
                year_end=state.year_end.value,
                treecover=state.treecover.value,
            )
        )

    trace_btn = use_task_button(trace_task, on_start=_start_trace, cancel_reason_ref=trace_cancel)

    with solara.Column(gap="8px"):
        TaskButtonComponent(
            label="Trace watershed",
            **trace_btn,
            icon="mdi-source-branch",
            external_busy=state.lat.value is None,
            small=True,
            block=True,
        )

        if state.hybasin_list.value:
            rv.Select(
                v_model=state.method.value,
                on_v_model=state.method.set,
                items=[
                    {"text": "All upstream basins", "value": "all"},
                    {"text": "Filter specific basins", "value": "filter"},
                ],
                label="Basin selection",
                hint="Controls which basins are included in the statistics",
                persistent_hint=True,
                dense=True,
                outlined=True,
            )

            if state.method.value == "filter":
                rv.Select(
                    v_model=state.selected_basins.value,
                    on_v_model=state.selected_basins.set,
                    items=[{"text": str(h), "value": h} for h in state.hybasin_list.value],
                    label="Select basins",
                    multiple=True,
                    small_chips=True,
                    deletable_chips=True,
                    dense=True,
                    outlined=True,
                )

            DashboardStep(state, gee_interface, legend_visible, legend_data, sepal_map)

            export_sources: tuple[ExportSource, ...] = ()
            if state.forest_change.value is not None and state.upstream_fc.value is not None:
                forest_change = state.forest_change.value
                upstream_fc = state.upstream_fc.value
                default_name = (
                    f"basin_rivers_{state.level.value}_"
                    f"{state.year_start.value}_{state.year_end.value}"
                )
                export_sources = (
                    ExportSource(
                        id="forest_change",
                        label="GFC forest change (classified)",
                        kind="image",
                        resolve=lambda img=forest_change, fc=upstream_fc, name=default_name: (
                            ResolvedExport(
                                ee_object=img,
                                default_name=name,
                                region=fc.geometry(),
                                default_scale=30,
                                gee_folder="basin_rivers",
                                drive_folder="basin_rivers_exports",
                                sepal_folder="basin_rivers",
                                max_pixels=1e13,
                            )
                        ),
                    ),
                    ExportSource(
                        id="upstream_basins",
                        label="Upstream basins",
                        kind="table",
                        resolve=lambda fc=upstream_fc, name=default_name: ResolvedExport(
                            ee_object=fc,
                            default_name=f"{name}_basins",
                            gee_folder="basin_rivers",
                            drive_folder="basin_rivers_exports",
                            sepal_folder="basin_rivers",
                        ),
                    ),
                )

            ExportLauncher(
                sources=export_sources,
                label="Export results",
                button_text=True,
                small=True,
                block=True,
                gee_interface=gee_interface,
            )
