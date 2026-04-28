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

TREECOVER_PRESETS = (10, 30, 50, 75, 80, 90)


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

        if forest_map in ("gfc", "roadless"):
            year_items = [
                {"text": str(y), "value": y}
                for y in range(FOREST_MAP_MAX_YEAR, FOREST_MAP_MIN_YEAR - 1, -1)
            ]
            rv.Select(
                v_model=state.forest_map_year.value,
                on_v_model=lambda v: state.forest_map_year.set(int(v)),
                items=year_items,
                label="Forest mask baseline year",
                dense=True,
                outlined=True,
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
