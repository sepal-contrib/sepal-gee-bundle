"""Basin parameter configuration: level, year range, threshold."""

import reacton.ipyvuetify as rv
import solara

from apps.basin_rivers.params import GFC_MAX_YEAR, GFC_MIN_YEAR, HYBAS_LEVELS

TREECOVER_PRESETS = (10, 30, 50, 75, 80, 90)


@solara.component
def ParamsStep(state):
    """HydroSHEDS level, year range, and tree cover threshold inputs."""
    level_items = [{"text": f"Level {lv}", "value": lv} for lv in HYBAS_LEVELS]
    year_items = [
        {"text": str(2000 + i), "value": 2000 + i} for i in range(GFC_MIN_YEAR, GFC_MAX_YEAR + 1)
    ]

    current = state.treecover.value
    preset_value = current if current in TREECOVER_PRESETS else None

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
        rv.Select(
            v_model=state.level.value,
            on_v_model=state.level.set,
            items=level_items,
            label="HydroSHEDS Level",
            hint="Higher = smaller catchments",
            persistent_hint=True,
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

        solara.Text("Tree cover threshold (%)", style={"opacity": "0.7"})
        with rv.Html(
            tag="div",
            style_="display: flex; align-items: center; gap: 8px; width: 100%;",
            class_="mt-1",
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
