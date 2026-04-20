"""Spline line chart for forest loss trend per basin."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Grid, Legend, Option, Title, Tooltip, XAxis, YAxis
from ipecharts.option.series import Line

from apps.basin_rivers.scripts.statistics import get_loss_trend_df

from .theme import use_echarts_theme


@solara.component
def LossTrend(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)

    df = state.zonal_df.value
    basins = state.selected_hybasid_chart.value
    timespan = state.sett_timespan.value

    if df is None or df.empty or not basins:
        return

    trend_df = get_loss_trend_df(df, list(basins), tuple(timespan))
    if trend_df.empty:
        solara.Text("No loss in the selected range.")
        return

    years = sorted(trend_df["year"].unique().tolist())
    series = []
    for basin_id in sorted(trend_df["basin"].astype(str).unique()):
        sub = trend_df[trend_df["basin"].astype(str) == basin_id]
        by_year = {int(y): float(a) for y, a in zip(sub["year"], sub["area"])}
        color = sub["catch_color"].iloc[0]
        series.append(
            Line(
                name=basin_id,
                smooth=True,
                showSymbol=True,
                data=[round(by_year.get(y, 0.0), 2) for y in years],
                lineStyle={"color": color},
                itemStyle={"color": color},
            )
        )

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(text="Forest loss trend", left="center", textStyle={"fontSize": 14}),
        tooltip=Tooltip(trigger="axis"),
        legend=Legend(bottom=0, textStyle={"fontSize": 10}),
        grid=Grid(left=50, right=20, top=50, bottom=60, containLabel=True),
        xAxis=XAxis(type="category", data=[str(y) for y in years], name="Year"),
        yAxis=YAxis(type="value", name="Loss (ha)"),
        series=series,
    )

    with rv.Html(tag="div", class_="br-echart-loss-trend", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
