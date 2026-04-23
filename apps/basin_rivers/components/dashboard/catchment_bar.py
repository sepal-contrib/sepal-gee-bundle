"""Per-catchment bar chart. Three modes driven by selected_var."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Grid, Legend, Option, Title, Toolbox, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar

from apps.basin_rivers.params import CATCH_BAR_TITLES
from apps.basin_rivers.scripts.statistics import get_catchment_bar_df

from .theme import use_echarts_theme


@solara.component
def CatchmentBar(state):
    theme = use_echarts_theme()

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
            backgroundColor="#1e1e1e00",
            title=Title(text=title, left="center", textStyle={"fontSize": 14}),
            tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
            toolbox=Toolbox(
                show=True,
                feature={"saveAsImage": {"show": True, "title": "Save PNG"}},
            ),
            grid=Grid(left=50, right=20, top=50, bottom=60, containLabel=True),
            xAxis=XAxis(
                type="category",
                data=categories,
                name="Catchment",
                axisLabel={"rotate": 30, "fontSize": 10},
            ),
            yAxis=YAxis(type="value", name="Area (ha)"),
            series=[Bar(data=data, label={"show": False})],
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
            backgroundColor="#1e1e1e00",
            title=Title(text=title, left="center", textStyle={"fontSize": 14}),
            tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
            toolbox=Toolbox(
                show=True,
                feature={"saveAsImage": {"show": True, "title": "Save PNG"}},
            ),
            legend=Legend(bottom=0, textStyle={"fontSize": 10}),
            grid=Grid(left=50, right=20, top=50, bottom=60, containLabel=True),
            xAxis=XAxis(type="category", data=[str(y) for y in years], name="Year"),
            yAxis=YAxis(type="value", name="Loss (ha)"),
            series=series,
        )

    with rv.Html(tag="div", class_="br-echart-catchment-bar", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "380px", "width": "100%"}
        )
