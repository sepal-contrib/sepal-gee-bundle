"""TMF year-trend bar chart (area of degradation/deforestation per year)."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Grid, Option, Title, Toolbox, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar

from .theme import use_echarts_theme, year_color


@solara.component
def YearTrend(rows: list, tmf_type: str):
    theme = use_echarts_theme()

    if not rows:
        return

    # CHG rows are keyed by class code, not year — the year view is meaningless.
    if tmf_type == "CHG":
        return

    year_rows = sorted(
        (r for r in rows if float(r["area_ha"]) > 0),
        key=lambda r: int(r["code"]),
    )
    if not year_rows:
        solara.Text("No loss/degradation events detected in the analysis period.")
        return

    years = [int(r["code"]) for r in year_rows]
    y0, y1 = min(years), max(years)
    categories = [str(int(r["code"])) for r in year_rows]
    data = [
        {
            "value": round(float(r["area_ha"]), 2),
            "itemStyle": {"color": year_color(int(r["code"]), y0, y1)},
        }
        for r in year_rows
    ]

    y_label = "Degraded area (ha)" if tmf_type == "DEG" else "Deforested area (ha)"
    title_text = "Degradation by year" if tmf_type == "DEG" else "Deforestation by year"

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(text=title_text, left="center", textStyle={"fontSize": 14}),
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
        yAxis=YAxis(type="value", name=y_label),
        series=[Bar(data=data, label={"show": False})],
    )

    with rv.Html(tag="div", class_="tmf-echart-year-trend", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
