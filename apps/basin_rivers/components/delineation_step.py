"""Upstream delineation and statistics computation."""

import logging
from dataclasses import asdict as _asdict
from dataclasses import dataclass

import ee
import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.basin_rivers.params import GFC_LEGEND, SLD_INTERVALS
from apps.basin_rivers.scripts import (
    classify_gfc,
    compute_zonal_stats,
    get_hydroshed_collection,
    get_upstream_basin_ids,
    parse_zonal_stats,
)
from apps.basin_rivers.scripts.visualization import create_basins_layer

from .dashboard_step import DashboardStep

logger = logging.getLogger("sepal_gee_bundle.basin_rivers")


@dataclass(frozen=True, slots=True)
class DelineationRequest:
    lat: float
    lon: float
    level: int
    year_start: int
    year_end: int
    treecover: int


@dataclass(frozen=True, slots=True)
class StatsRequest:
    level: int
    hybas_ids: tuple[int, ...]
    year_start: int
    year_end: int
    treecover: int


@solara.component
def DelineationStep(
    state,
    sepal_map,
    gee_interface,
    theme_toggle,
    legend_data=None,
    legend_visible=None,
):
    """Delineate upstream basins and compute forest change statistics."""
    notifications = use_notifications()
    delineate_cancel = solara.use_ref(None)
    stats_cancel = solara.use_ref(None)

    # --- Task 1: Delineation ---
    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def delineate_task(request: DelineationRequest):
        with notifications.track("Delineating upstream basins", total_steps=4) as task:
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

    def _sync_delineation():
        """Mirror task state into AppState and add non-GEE map layers."""
        state.loading.value = delineate_task.pending
        if delineate_task.pending:
            return
        if delineate_task.cancelled:
            notifications.info("Delineation cancelled.")
            return
        if delineate_task.error:
            notifications.error(f"Delineation failed: {delineate_task.exception}")
            return
        if delineate_task.finished and delineate_task.value is not None:
            result = delineate_task.value
            state.hybasin_list.value = result["hybas_ids"]
            state.upstream_fc.value = result["upstream_fc"]
            state.forest_change.value = result["gfc_image"]
            state.selected_basins.value = result["hybas_ids"]

            # Add basins as vector GeoJSON layer (pure ipyleaflet, no GEE)
            existing = sepal_map.find_layer("Upstream catchment", none_ok=True)
            if existing:
                sepal_map.remove_layer(existing)
            basins_layer = create_basins_layer(result["geojson_data"])
            sepal_map.add_layer(basins_layer, key="Upstream catchment")

            # Zoom using GeoJSON bounds (no GEE call needed)
            from geopandas import GeoDataFrame

            gdf = GeoDataFrame.from_features(result["geojson_data"]["features"])
            if not gdf.empty:
                sepal_map.zoom_bounds(gdf.total_bounds)

            if legend_data is not None:
                legend_data.set(_asdict(GFC_LEGEND))
            if legend_visible is not None:
                legend_visible.set(True)

            notifications.success(
                f"Watershed traced: {len(result['hybas_ids'])} upstream basins"
            )
            logger.info("Delineation complete: %d basins", len(result["hybas_ids"]))

    solara.use_effect(
        _sync_delineation,
        [
            delineate_task.pending,
            delineate_task.finished,
            delineate_task.error,
            delineate_task.cancelled,
        ],
    )

    # --- Task 2: Statistics ---
    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def stats_task(request: StatsRequest):
        with notifications.track("Computing zonal statistics", total_steps=3) as task:
            task.step("Building basin selection...")
            base_fc = get_hydroshed_collection(request.level)
            selected_fc = base_fc.filter(ee.Filter.inList("HYBAS_ID", list(request.hybas_ids)))

            task.step("Classifying GFC forest change...")
            gfc_image = classify_gfc(
                selected_fc, request.treecover, request.year_start, request.year_end
            )

            task.step("Running reduceRegions...")
            stats_fc = compute_zonal_stats(gfc_image, selected_fc)
            raw = await gee_interface.get_info_async(stats_fc)
        return parse_zonal_stats(raw)

    def _sync_stats():
        if stats_task.pending:
            return
        if stats_task.cancelled:
            notifications.info("Statistics cancelled.")
            return
        if stats_task.error:
            notifications.error(f"Statistics failed: {stats_task.exception}")
            return
        if stats_task.finished and stats_task.value is not None:
            from apps.basin_rivers.scripts import add_catchment_colors

            df = add_catchment_colors(stats_task.value)
            state.zonal_df.value = df

            state.selected_var.value = "all"
            seed_ids = (
                state.selected_basins.value
                if state.method.value == "filter" and state.selected_basins.value
                else state.hybasin_list.value
            )
            state.selected_hybasid_chart.value = [str(b) for b in seed_ids]
            state.sett_timespan.value = (state.year_start.value, state.year_end.value)

            notifications.success(f"Statistics computed: {len(df)} rows")
            logger.info("Statistics computed: %d rows", len(df))

    solara.use_effect(
        _sync_stats,
        [stats_task.pending, stats_task.finished, stats_task.error, stats_task.cancelled],
    )

    # --- Button handlers ---
    def _valid_year_range() -> bool:
        if state.year_start.value > state.year_end.value:
            notifications.warning(
                f"Invalid year range: start ({state.year_start.value}) is after "
                f"end ({state.year_end.value})."
            )
            return False
        return True

    def _start_delineation():
        if state.lat.value is None or state.lon.value is None:
            notifications.warning("Select a pour point first.")
            return
        if not _valid_year_range():
            return
        delineate_cancel.current = None
        state.hybasin_list.value = []
        state.zonal_df.value = None
        if legend_visible is not None:
            legend_visible.set(False)
        for _layer_key in ("GFC forest change", "Upstream catchment"):
            existing = sepal_map.find_layer(_layer_key, none_ok=True)
            if existing:
                sepal_map.remove_layer(existing)
        delineate_task(
            DelineationRequest(
                lat=state.lat.value,
                lon=state.lon.value,
                level=state.level.value,
                year_start=state.year_start.value,
                year_end=state.year_end.value,
                treecover=state.treecover.value,
            )
        )

    def _start_stats():
        ids = (
            state.selected_basins.value
            if state.method.value == "filter"
            else state.hybasin_list.value
        )
        if not ids:
            notifications.warning("Delineate upstream basins first.")
            return
        if not _valid_year_range():
            return
        stats_cancel.current = None
        state.zonal_df.value = None
        stats_task(
            StatsRequest(
                level=state.level.value,
                hybas_ids=tuple(ids),
                year_start=state.year_start.value,
                year_end=state.year_end.value,
                treecover=state.treecover.value,
            )
        )

    delineate_btn = use_task_button(
        delineate_task, on_start=_start_delineation, cancel_reason_ref=delineate_cancel
    )
    stats_btn = use_task_button(stats_task, on_start=_start_stats, cancel_reason_ref=stats_cancel)

    # --- UI ---
    with solara.Column():
        TaskButtonComponent(
            label="Trace watershed",
            **delineate_btn,
            icon="mdi-source-branch",
            external_busy=state.lat.value is None,
            small=True,
            block=True,
        )

        if state.hybasin_list.value:
            with rv.ListItem(dense=True, class_="pa-0 mt-2"):
                with rv.ListItemIcon(class_="mr-2 my-auto"):
                    rv.Icon(small=True, color="primary", children=["mdi-waves"])
                with rv.ListItemContent(class_="py-1"):
                    rv.ListItemTitle(
                        class_="caption",
                        style_="opacity: 0.6;",
                        children=["Upstream basins"],
                    )
                    rv.ListItemSubtitle(
                        class_="body-2",
                        children=[str(len(state.hybasin_list.value))],
                    )

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
                    chips=True,
                    deletable_chips=True,
                    dense=True,
                    outlined=True,
                )

            TaskButtonComponent(
                label="Calculate Statistics",
                **stats_btn,
                icon="mdi-chart-bar",
                external_busy=not state.hybasin_list.value,
                small=True,
                block=True,
            )

            DashboardStep(state, theme_toggle)
