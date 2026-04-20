"""Basin parameter configuration: level, year range, threshold."""

import reacton.ipyvuetify as rv
import solara

from apps.basin_rivers.params import GFC_MAX_YEAR, GFC_MIN_YEAR, HYBAS_LEVELS


@solara.component
def ParamsStep(state):
    """HydroSHEDS level, year range, and tree cover threshold inputs."""
    level_items = [{"text": f"Level {lv}", "value": lv} for lv in HYBAS_LEVELS]
    year_items = [
        {"text": str(2000 + i), "value": 2000 + i} for i in range(GFC_MIN_YEAR, GFC_MAX_YEAR + 1)
    ]

    with solara.Column():
        rv.Select(
            v_model=state.level.value,
            on_v_model=state.level.set,
            items=level_items,
            label="HydroSHEDS Level",
            hint="Higher = smaller catchments",
            persistent_hint=True,
            dense=True,
            outlined=True,
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

        rv.Slider(
            v_model=state.treecover.value,
            on_v_model=state.treecover.set,
            label="Tree cover threshold (%)",
            min=0,
            max=100,
            thumb_label="always",
            class_="mt-4",
        )
