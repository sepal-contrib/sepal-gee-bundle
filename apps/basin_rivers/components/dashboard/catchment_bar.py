"""Per-catchment bar chart. Three modes driven by selected_var."""

import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar

from apps.basin_rivers.params import CATCH_BAR_TITLES
from apps.basin_rivers.scripts.statistics import get_catchment_bar_df

from .theme import use_echarts_theme


@solara.component
def CatchmentBar(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)

    df = state.zonal_df.value
    selected = state.selected_var.value
    timespan = state.sett_timespan.value
    basins = state.selected_hybasid_chart.value

    if df is None or df.empty or not basins:
        solara.Text("Select catchments to see the bar chart.")
        return

    filtered = df[df["basin"].astype(str).isin([str(b) for b in basins])]
    bar_df, mode = get_catchment_bar_df(filtered, selected, tuple(timespan))
    title = CATCH_BAR_TITLES.get(selected, "")

    if bar_df.empty:
        solara.Text(f"No data for {selected.replace('_', ' ')} in this range.")
        return

    if mode == "single":
        data = [
            {
                "value": round(float(row["area"]), 2),
                "itemStyle": {"color": row["catch_color"]},
            }
            for _, row in bar_df.iterrows()
        ]
        categories = bar_df["basin"].astype(str).tolist()
        option = Option(
            title=Title(text=title, left="center"),
            tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
            xAxis=XAxis(type="category", data=categories, name="Catchment"),
            yAxis=YAxis(type="value", name="Area (ha)"),
            series=[Bar(data=data, label={"show": True, "position": "top"})],
        )
    else:
        years = sorted(bar_df["year"].unique().tolist())
        series = []
        for basin_id in sorted(bar_df["basin"].astype(str).unique()):
            sub = bar_df[bar_df["basin"].astype(str) == basin_id]
            by_year = {int(y): float(a) for y, a in zip(sub["year"], sub["area"])}
            color = sub["catch_color"].iloc[0]
            series.append(
                Bar(
                    name=basin_id,
                    stack="total",
                    data=[round(by_year.get(y, 0.0), 2) for y in years],
                    itemStyle={"color": color},
                )
            )
        option = Option(
            title=Title(text=title, left="center"),
            tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
            legend=Legend(bottom=0),
            xAxis=XAxis(type="category", data=[str(y) for y in years], name="Year"),
            yAxis=YAxis(type="value", name="Loss (ha)"),
            series=series,
        )

    EChartsWidget.element(option=option, theme=theme, style={"height": "360px"})
