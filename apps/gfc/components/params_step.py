"""Parameter configuration and visualization step for GFC app."""

import logging
from dataclasses import asdict, dataclass

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.gfc.params import GFC_LEGEND, GFC_MAX_YEAR, GFC_MIN_YEAR, SLD_INTERVALS
from apps.gfc.scripts import classify_gfc

logger = logging.getLogger("sepal_gee_bundle.gfc")

GFC_LAYER_KEY = "gfc_classification"

TREECOVER_PRESETS = (10, 30, 50, 75, 80, 90)


@dataclass(frozen=True, slots=True)
class VisualizeRequest:
    aoi_fc: object  # ee.FeatureCollection
    treecover: int
    year_start: int
    year_end: int


@solara.component
def ParamsStep(state, sepal_map, gee_interface, legend_data=None, legend_visible=None):
    """Tree cover threshold, year range, and visualization controls."""
    notifications = use_notifications()
    cancel_reason = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def viz_task(request: VisualizeRequest):
        with notifications.track("Visualizing GFC map", total_steps=2) as task:
            task.step("Classifying GFC pixels")
            gfc_image = classify_gfc(
                request.aoi_fc,
                request.treecover,
                request.year_start,
                request.year_end,
            )

            # Remove any previous GFC layer before adding the new one
            sepal_map.remove_layer(GFC_LAYER_KEY, none_ok=True)

            task.step("Loading tiles on map")
            await sepal_map.add_ee_layer_async(
                gfc_image.sldStyle(SLD_INTERVALS),
                {},
                GFC_LAYER_KEY,
                autocenter=True,
            )

        logger.info("GFC visualization loaded: %s", GFC_LAYER_KEY)
        return gfc_image

    def _sync_viz():
        state.loading.value = viz_task.pending
        if viz_task.pending or viz_task.cancelled:
            return
        if viz_task.error:
            notifications.error(f"Visualization failed: {viz_task.exception}")
            return
        if viz_task.finished and viz_task.value is not None:
            state.result_image.value = viz_task.value
            if legend_data is not None:
                legend_data.set(asdict(GFC_LEGEND))
            if legend_visible is not None:
                legend_visible.set(True)
            notifications.success("GFC layer added to map")

    solara.use_effect(
        _sync_viz,
        [viz_task.pending, viz_task.cancelled, viz_task.finished, viz_task.error],
    )

    def _start_viz():
        if state.aoi.value is None:
            notifications.warning("Please select an Area of Interest first.")
            return
        cancel_reason.current = None
        state.loading.value = True
        state.result_image.value = None
        if legend_visible is not None:
            legend_visible.set(False)
        viz_task(
            VisualizeRequest(
                aoi_fc=state.aoi.value.feature_collection,
                treecover=state.treecover.value,
                year_start=state.year_start.value,
                year_end=state.year_end.value,
            )
        )

    btn_props = use_task_button(
        viz_task, on_start=_start_viz, cancel_reason_ref=cancel_reason
    )

    year_items = [
        {"text": str(2000 + i), "value": 2000 + i}
        for i in range(GFC_MIN_YEAR, GFC_MAX_YEAR + 1)
    ]

    current_tc = state.treecover.value
    preset_value = current_tc if current_tc in TREECOVER_PRESETS else None

    def _set_preset(v):
        if v is None:
            return
        state.treecover.set(int(v))

    def _set_custom(v):
        try:
            n = int(float(v))
        except (TypeError, ValueError):
            return
        if 0 <= n <= 100:
            state.treecover.set(n)

    with solara.Column():
        solara.Text("Tree cover threshold (%)", style={"opacity": "0.7"})
        with rv.Html(
            tag="div",
            style_="display: flex; align-items: center; gap: 8px; width: 100%;",
            class_="mt-1 mb-2",
        ):
            with solara.ToggleButtonsSingle(
                value=preset_value,
                on_value=_set_preset,
                mandatory=False,
                dense=True,
            ):
                for preset in TREECOVER_PRESETS:
                    solara.Button(
                        label=str(preset),
                        value=preset,
                        small=True,
                        text=True,
                    )

            rv.TextField(
                v_model=str(state.treecover.value),
                on_v_model=_set_custom,
                type="number",
                suffix="%",
                dense=True,
                hide_details=True,
                placeholder="Custom",
                style_="max-width: 96px;",
            )

        rv.Select(
            v_model=state.year_start.value,
            on_v_model=lambda v: state.year_start.set(int(v)),
            items=year_items,
            label="Start year",
        )

        rv.Select(
            v_model=state.year_end.value,
            on_v_model=lambda v: state.year_end.set(int(v)),
            items=year_items,
            label="End year",
        )

        TaskButtonComponent(
            label="Add layer",
            **btn_props,
            external_busy=state.aoi.value is None,
            small=True,
            block=True,
        )
