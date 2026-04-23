"""Forest mask + sensor selection step for FCDM."""

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.inputs.asset_select import AssetSelectComponent

from apps.fcdm.params import (
    FOREST_MAP_ITEMS,
    FOREST_MAP_MAX_YEAR,
    FOREST_MAP_MIN_YEAR,
    SENSOR_ITEMS,
)


@solara.component
def ForestStep(state, gee_interface=None):
    """Forest mask source, GFC threshold, baseline year, and sensor selection."""
    forest_map = state.forest_map.value

    with solara.Column():
        rv.Select(
            v_model=forest_map,
            on_v_model=state.forest_map.set,
            items=FOREST_MAP_ITEMS,
            label="Forest mask source",
            dense=True,
            outlined=True,
        )

        if forest_map == "gfc":
            rv.Slider(
                v_model=state.treecover.value,
                on_v_model=lambda v: state.treecover.set(int(v)),
                label="Tree cover threshold (%)",
                min=0,
                max=100,
                thumb_label="always",
                class_="mt-4",
            )

        if forest_map in ("gfc", "roadless"):
            rv.Slider(
                v_model=state.forest_map_year.value,
                on_v_model=lambda v: state.forest_map_year.set(int(v)),
                label="Forest mask baseline year",
                min=FOREST_MAP_MIN_YEAR,
                max=FOREST_MAP_MAX_YEAR,
                thumb_label="always",
                class_="mt-4",
            )

        if forest_map == "custom":
            current_asset = state.forest_map_asset.value
            current_value = {"asset_id": current_asset} if current_asset else None

            def _on_asset(v):
                state.forest_map_asset.set((v or {}).get("asset_id") or "")

            AssetSelectComponent(
                types=["IMAGE"],
                value=current_value,
                on_value=_on_asset,
                loading=state.loading,
                gee_interface=gee_interface,
            )

        rv.Select(
            v_model=state.sensors.value,
            on_v_model=state.sensors.set,
            items=SENSOR_ITEMS,
            label="Sensors",
            multiple=True,
            small_chips=True,
            deletable_chips=True,
            dense=True,
            outlined=True,
            class_="mt-2",
        )
