"""Sensors, dates, measure selection, and one-shot collection build + visualize."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.legend import GradientEntry, LegendData
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.coverage_analysis.params import (
    MEASURE_ITEMS,
    SENSOR_ITEMS,
    VIS_COUNT,
    VIS_NDVI_MEAN,
    VIS_NDVI_STDDEV,
)
from apps.coverage_analysis.scripts import build_collection, compose_measure

_MEASURE_LABELS = {item["value"]: item["text"] for item in MEASURE_ITEMS}

logger = logging.getLogger("sepal_gee_bundle.coverage_analysis")

LAYER_KEY_PREFIX = "coverage_"


def _vis_for(measure: str, annual: bool) -> dict:
    if measure == "pixel_count":
        vis = dict(VIS_COUNT)
        vis["max"] = 20 if annual else 100
        return vis
    if measure == "pixel_count_all":
        vis = dict(VIS_COUNT)
        vis["max"] = 40 if annual else 200
        return vis
    if measure == "ndvi_median":
        return dict(VIS_NDVI_MEAN)
    if measure == "ndvi_stdDev":
        return dict(VIS_NDVI_STDDEV)
    return dict(VIS_COUNT)


def _valid_date(value: str | None) -> bool:
    if not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class VisualizeRequest:
    aoi_fc: object
    measure: str
    start: str
    end: str
    annual: bool
    sensors: tuple[str, ...]
    sr: bool
    t2: bool


@solara.component
def VisualizeStep(
    state, sepal_map, gee_interface, legend_data=None, legend_visible=None
):
    """Build the multi-sensor collection and render the chosen measure in one click."""
    notifications = use_notifications()
    cancel_reason = solara.use_ref(None)
    previous_layers = solara.use_ref([])

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def viz_task(request: VisualizeRequest):
        with notifications.track("Visualizing measure", total_steps=3) as task:
            task.step("Assembling multi-sensor collection")
            coll = build_collection(
                aoi=request.aoi_fc,
                start=request.start,
                end=request.end,
                sensors=list(request.sensors),
                sr=request.sr,
                include_t2=request.t2,
            )
            if coll is None:
                raise ValueError("No sensors selected.")

            size = await gee_interface.get_info_async(coll.size())
            size = int(size or 0)
            if size == 0:
                raise ValueError("No images in the selected period.")

            state.collection.value = coll

            task.step(f"Composing {size} images")
            image, band_names = compose_measure(
                coll=coll,
                measure=request.measure,
                start=request.start,
                end=request.end,
                aoi=request.aoi_fc,
                annual=request.annual,
            )

            for key in previous_layers.current:
                sepal_map.remove_layer(key, none_ok=True)
            previous_layers.current = []

            vis = _vis_for(request.measure, request.annual)

            task.step("Adding layers to map")
            for i, band in enumerate(band_names):
                key = f"{LAYER_KEY_PREFIX}{band}"
                layer_image = image.select(band)
                await sepal_map.add_ee_layer_async(
                    layer_image,
                    vis,
                    key,
                    autocenter=(i == 0),
                )
                previous_layers.current.append(key)

        logger.info(
            "Coverage visualization added: %d layers from %d images",
            len(band_names),
            size,
        )
        return image, band_names

    def _sync_viz():
        state.loading.value = viz_task.pending
        if viz_task.pending or viz_task.cancelled:
            return
        if viz_task.error:
            notifications.error(f"Visualization failed: {viz_task.exception}")
            return
        if viz_task.finished and viz_task.value is not None:
            image, bands = viz_task.value
            state.result_image.value = image
            state.result_band_names.value = list(bands)
            if legend_data is not None:
                vis = _vis_for(state.measure.value, bool(state.annual.value))
                label = _MEASURE_LABELS.get(state.measure.value, state.measure.value)
                legend = LegendData(
                    gradients=[
                        GradientEntry(
                            colors=list(vis["palette"]),
                            labels=[str(vis["min"]), str(vis["max"])],
                            title=label,
                        )
                    ]
                )
                legend_data.set(asdict(legend))
            if legend_visible is not None:
                legend_visible.set(True)
            notifications.success(f"Added {len(bands)} layer(s) to map")

    solara.use_effect(
        _sync_viz,
        [viz_task.pending, viz_task.cancelled, viz_task.finished, viz_task.error],
    )

    def _start_viz():
        if state.aoi.value is None:
            notifications.warning("Select an AOI first.")
            return
        if not state.sensors.value:
            notifications.warning("Select at least one sensor.")
            return
        if not (
            _valid_date(state.start_date.value) and _valid_date(state.end_date.value)
        ):
            notifications.warning("Dates must be YYYY-MM-DD.")
            return
        if state.start_date.value >= state.end_date.value:
            notifications.warning("Start date must precede end date.")
            return
        cancel_reason.current = None
        state.collection.value = None
        state.result_image.value = None
        state.result_band_names.value = []
        if legend_visible is not None:
            legend_visible.set(False)
        viz_task(
            VisualizeRequest(
                aoi_fc=state.aoi.value.feature_collection,
                measure=state.measure.value,
                start=state.start_date.value,
                end=state.end_date.value,
                annual=bool(state.annual.value),
                sensors=tuple(state.sensors.value),
                sr=bool(state.surface_reflectance.value),
                t2=bool(state.include_tier2.value),
            )
        )

    btn_props = use_task_button(
        viz_task, on_start=_start_viz, cancel_reason_ref=cancel_reason
    )

    with solara.Column():
        rv.TextField(
            v_model=state.start_date.value,
            on_v_model=state.start_date.set,
            label="Start date (YYYY-MM-DD)",
            dense=True,
            outlined=True,
        )
        rv.TextField(
            v_model=state.end_date.value,
            on_v_model=state.end_date.set,
            label="End date (YYYY-MM-DD)",
            dense=True,
            outlined=True,
        )
        rv.Select(
            v_model=state.sensors.value,
            on_v_model=state.sensors.set,
            items=SENSOR_ITEMS,
            label="Sensors",
            multiple=True,
            small_chips=True,
            deletable_chips=True,
        )
        rv.Switch(
            v_model=state.surface_reflectance.value,
            on_v_model=state.surface_reflectance.set,
            label="Surface Reflectance (SR)",
            class_="ml-2",
        )
        rv.Switch(
            v_model=state.include_tier2.value,
            on_v_model=state.include_tier2.set,
            label="Include Tier 2 (Landsat)",
            class_="ml-2",
        )
        rv.Select(
            v_model=state.measure.value,
            on_v_model=state.measure.set,
            items=MEASURE_ITEMS,
            label="Measure",
        )
        rv.Switch(
            v_model=state.annual.value,
            on_v_model=state.annual.set,
            label="Annual (one layer per year)",
            class_="ml-2",
        )

        TaskButtonComponent(
            label="Show on map",
            **btn_props,
            external_busy=state.aoi.value is None,
            small=True,
            block=True,
        )
