"""Forest loss trend: bar chart of loss area by year."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Grid, Option, Title, Toolbox, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar

from apps.gfc.params import GFC_MAX_YEAR

from .theme import loss_year_color, use_echarts_theme


@solara.component
def LossTrend(rows: list):
    theme = use_echarts_theme()

    if not rows:
        return

    loss_rows = [r for r in rows if 1 <= r["code"] <= GFC_MAX_YEAR]
    if not loss_rows:
        solara.Text("No loss detected in the analysis period.")
        return

    loss_rows = sorted(loss_rows, key=lambda r: r["code"])
    categories = [str(2000 + r["code"]) for r in loss_rows]
    data = [
        {
            "value": round(float(r["area_ha"]), 2),
            "itemStyle": {"color": loss_year_color(r["code"])},
        }
        for r in loss_rows
    ]

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(text="Forest loss by year", left="center", textStyle={"fontSize": 14}),
        tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
        toolbox=Toolbox(
            show=True,
            feature={"saveAsImage": {"show": True, "title": "Save PNG"}},
        ),
        grid=Grid(left=50, right=20, top=50, bottom=50, containLabel=True),
        xAxis=XAxis(
            type="category",
            data=categories,
            name="Year",
            axisLabel={"rotate": 30, "fontSize": 10},
        ),
        yAxis=YAxis(type="value", name="Loss (ha)"),
        series=[Bar(data=data, label={"show": False})],
    )

    with rv.Html(tag="div", class_="gfc-echart-loss-trend", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
