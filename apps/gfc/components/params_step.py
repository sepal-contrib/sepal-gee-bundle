"""Parameter configuration and visualization step for GFC app."""

import asyncio
import logging

import reacton.ipyvuetify as rv
import solara

from apps.gfc.params import GFC_MAX_YEAR, GFC_MIN_YEAR, SLD_INTERVALS
from apps.gfc.scripts import classify_gfc

logger = logging.getLogger("sepal_gee_bundle.gfc")


@solara.component
def ParamsStep(state, sepal_map, gee_interface):
    """Tree cover threshold, year range, and visualization controls."""
    error, set_error = solara.use_state("")
    viz_trigger = solara.use_reactive(0)

    @solara.lab.use_task(
        dependencies=[viz_trigger.value], raise_error=False, prefer_threaded=True
    )
    async def viz_task():
        if viz_trigger.value == 0:
            return
        set_error("")
        aoi = state.aoi.value
        if aoi is None:
            set_error("Please select an Area of Interest first.")
            return

        gfc_image = await asyncio.to_thread(
            classify_gfc,
            aoi.feature_collection,
            state.treecover.value,
            state.year_start.value,
            state.year_end.value,
        )

        state.result_image.set(gfc_image)

        layer_name = (
            f"gfc_{state.treecover.value}_{state.year_start.value}_{state.year_end.value}"
        )

        if not sepal_map.find_layer(layer_name, none_ok=True):
            await sepal_map.add_ee_layer_async(
                gfc_image.sldStyle(SLD_INTERVALS),
                {},
                layer_name,
                autocenter=True,
            )

        logger.info("GFC visualization loaded: %s", layer_name)

    year_items = [
        {"text": str(2000 + i), "value": 2000 + i} for i in range(GFC_MIN_YEAR, GFC_MAX_YEAR + 1)
    ]

    with solara.Column():
        rv.Slider(
            v_model=state.treecover.value,
            on_v_model=state.treecover.set,
            label="Tree cover threshold (%)",
            min=0,
            max=100,
            thumb_label="always",
            class_="mt-4",
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

        if viz_task.error:
            rv.Alert(type="error", text=True, children=[str(viz_task.error)])

        if error:
            rv.Alert(type="error", text=True, children=[error])

        solara.Button(
            "Visualize",
            icon_name="mdi-eye",
            on_click=lambda *_: viz_trigger.set(viz_trigger.value + 1),
            loading=viz_task.pending,
            disabled=viz_task.pending or state.aoi.value is None,
            color="primary",
        )
