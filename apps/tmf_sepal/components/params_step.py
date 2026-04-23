"""Parameter configuration and visualization step for the TMF app."""

import logging
from dataclasses import asdict, dataclass

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps.tmf_sepal.params import (
    TMF_MAX_YEAR,
    TMF_MIN_YEAR,
    TMF_TYPES,
    change_legend,
    year_legend,
)
from apps.tmf_sepal.scripts import build_tmf_image, viz_params_for

logger = logging.getLogger("sepal_gee_bundle.tmf_sepal")

TMF_LAYER_KEY = "tmf_layer"
AOI_OUTLINE_KEY = "tmf_aoi_outline"


@dataclass(frozen=True, slots=True)
class VisualizeRequest:
    aoi_fc: object  # ee.FeatureCollection
    tmf_type: str
    year_start: int
    year_end: int


@solara.component
def ParamsStep(state, sepal_map, gee_interface, legend_data=None, legend_visible=None):
    """TMF layer type, year range, and visualize button."""
    notifications = use_notifications()
    cancel_reason = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def viz_task(request: VisualizeRequest):
        with notifications.track("Visualizing JRC TMF layer", total_steps=2) as task:
            task.step("Building TMF image")
            image = build_tmf_image(
                request.aoi_fc,
                request.tmf_type,
                request.year_start,
                request.year_end,
            )
            vis = viz_params_for(request.tmf_type, request.year_start, request.year_end)

            sepal_map.remove_layer(TMF_LAYER_KEY, none_ok=True)

            task.step("Loading tiles on map")
            await sepal_map.add_ee_layer_async(
                image,
                vis,
                TMF_LAYER_KEY,
                autocenter=True,
            )

        logger.info(
            "TMF visualization loaded: type=%s years=%s-%s",
            request.tmf_type,
            request.year_start,
            request.year_end,
        )
        return image

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
                if state.tmf_type.value == "CHG":
                    legend_data.set(asdict(change_legend()))
                else:
                    legend_data.set(
                        asdict(
                            year_legend(
                                state.tmf_type.value,
                                state.year_start.value,
                                state.year_end.value,
                            )
                        )
                    )
            if legend_visible is not None:
                legend_visible.set(True)
            notifications.success("TMF layer added to map")

    solara.use_effect(
        _sync_viz,
        [viz_task.pending, viz_task.cancelled, viz_task.finished, viz_task.error],
    )

    def _start_viz():
        if state.aoi.value is None:
            notifications.warning("Please select an Area of Interest first.")
            return
        if state.year_start.value > state.year_end.value:
            notifications.warning("Start year must be lower than or equal to end year.")
            return
        cancel_reason.current = None
        state.loading.value = True
        state.result_image.value = None
        if legend_visible is not None:
            legend_visible.set(False)
        viz_task(
            VisualizeRequest(
                aoi_fc=state.aoi.value.feature_collection,
                tmf_type=state.tmf_type.value,
                year_start=state.year_start.value,
                year_end=state.year_end.value,
            )
        )

    btn_props = use_task_button(viz_task, on_start=_start_viz, cancel_reason_ref=cancel_reason)

    year_items = [{"text": str(y), "value": y} for y in range(TMF_MIN_YEAR, TMF_MAX_YEAR + 1)]
    type_items = [{"text": t["label"], "value": t["value"]} for t in TMF_TYPES]

    with solara.Column():
        rv.Select(
            v_model=state.tmf_type.value,
            on_v_model=state.tmf_type.set,
            items=type_items,
            label="TMF layer",
            dense=True,
            outlined=True,
            class_="mt-2",
        )

        rv.Select(
            v_model=state.year_start.value,
            on_v_model=lambda v: state.year_start.set(int(v)),
            items=year_items,
            label="Start year",
            dense=True,
            outlined=True,
        )

        rv.Select(
            v_model=state.year_end.value,
            on_v_model=lambda v: state.year_end.set(int(v)),
            items=year_items,
            label="End year",
            dense=True,
            outlined=True,
        )

        TaskButtonComponent(
            label="Add layer",
            **btn_props,
            icon="mdi-plus",
            external_busy=state.aoi.value is None,
            small=True,
            block=True,
        )
