"""Dashboard settings: variable, timespan, catchment multi-select."""

import reacton.ipyvuetify as rv
import solara

from apps.basin_rivers.params import GFC_MAX_YEAR, VARIABLE_LABELS


@solara.component
def SettingsCard(state):
    """Controls for selected_var, sett_timespan, selected_hybasid_chart."""
    basins = state.hybasin_list.value

    with rv.Card(flat=True, class_="pa-3"):
        with rv.CardTitle():
            solara.Text("Dashboard settings")

        with rv.CardText():
            rv.Select(
                v_model=state.selected_var.value,
                on_v_model=state.selected_var.set,
                items=[{"text": label, "value": key} for key, label in VARIABLE_LABELS.items()],
                label="Variable",
                dense=True,
                outlined=True,
            )

            solara.Text("Timespan")
            year_min = 2001
            year_max = 2000 + GFC_MAX_YEAR
            rv.RangeSlider(
                v_model=list(state.sett_timespan.value),
                on_v_model=lambda v: state.sett_timespan.set(tuple(v)),
                min=year_min,
                max=year_max,
                step=1,
                thumb_label="always",
                dense=True,
                class_="mt-6",
            )

            rv.Select(
                v_model=list(state.selected_hybasid_chart.value),
                on_v_model=lambda v: state.selected_hybasid_chart.set(list(v)),
                items=[{"text": str(b), "value": b} for b in basins],
                label="Catchments",
                multiple=True,
                chips=True,
                deletable_chips=True,
                dense=True,
                outlined=True,
                class_="mt-3",
            )
