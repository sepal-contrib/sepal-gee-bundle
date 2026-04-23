"""Image count per year — bar chart."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Grid, Option, Title, Toolbox, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar

from .theme import use_echarts_theme


@solara.component
def YearBar(per_year: list[dict]):
    theme = use_echarts_theme()

    if not per_year:
        solara.Text("No yearly counts available.")
        return

    rows = sorted(per_year, key=lambda r: r["year"])
    categories = [str(r["year"]) for r in rows]
    data = [int(r["count"]) for r in rows]

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(text="Image count per year", left="center", textStyle={"fontSize": 14}),
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
        yAxis=YAxis(type="value", name="Images"),
        series=[
            Bar(
                data=data,
                itemStyle={"color": "#4a90d9"},
                label={"show": True, "position": "top", "fontSize": 10},
            )
        ],
    )

    with rv.Html(tag="div", class_="coverage-echart-year", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
