"""Dashboard settings: variable, timespan, catchment multi-select."""

import reacton.ipyvuetify as rv
import solara

from apps.basin_rivers.params import VARIABLE_LABELS


@solara.component
def SettingsCard(state):
    """Controls for selected_var, sett_timespan, selected_hybasid_chart."""
    df = state.zonal_df.value
    if df is not None and not df.empty:
        # Order basins by total area (largest first) so the list mirrors the
        # catchment-bar ordering the user sees in the graphs.
        basins = df.groupby("basin")["area"].sum().sort_values(ascending=False).index.tolist()
    else:
        basins = list(state.hybasin_list.value)
    year_min = state.year_start.value
    year_max = state.year_end.value
    current = state.sett_timespan.value
    # Clamp current value to the analysed range in case the user's earlier
    # selection falls outside it (e.g. after re-running with a tighter range).
    clamped = (max(year_min, current[0]), min(year_max, current[1]))

    with rv.Card(flat=True, class_="pa-3"):
        with rv.CardTitle():
            solara.Text("Dashboard settings")

        with rv.CardText():
            rv.Select(
                v_model=state.selected_var.value,
                on_v_model=state.selected_var.set,
                items=[{"text": label, "value": key} for key, label in VARIABLE_LABELS.items()],
                label="Variable",
            )

            # Timespan only affects loss-year aggregations (stacked bar + trend).
            # Other variables are static over the analysis period — hide the slider.
            if state.selected_var.value == "loss":
                solara.Text(f"Loss-year range ({year_min}-{year_max})")
                if year_max > year_min:
                    rv.RangeSlider(
                        v_model=list(clamped),
                        on_v_model=lambda v: state.sett_timespan.set(tuple(v)),
                        min=year_min,
                        max=year_max,
                        step=1,
                        thumb_label="always",
                        dense=True,
                        class_="mt-6",
                    )
                else:
                    solara.Text(
                        f"Single-year analysis: {year_min}",
                        style={"opacity": "0.6"},
                    )

            rv.Select(
                v_model=list(state.selected_hybasid_chart.value),
                on_v_model=lambda v: state.selected_hybasid_chart.set(list(v)),
                items=[{"text": str(b), "value": b} for b in basins],
                label="Catchments",
                multiple=True,
                small_chips=True,
                deletable_chips=True,
                class_="mt-3",
            )
