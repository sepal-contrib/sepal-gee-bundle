"""Image count per sensor — bar chart."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Grid, Option, Title, Toolbox, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar

from .theme import SENSOR_LABELS, sensor_color, use_echarts_theme


@solara.component
def SensorBar(per_sensor: list[dict]):
    theme = use_echarts_theme()

    if not per_sensor:
        solara.Text("No sensor counts available.")
        return

    categories = [SENSOR_LABELS.get(r["sensor"], r["sensor"]) for r in per_sensor]
    data = [
        {
            "value": int(r["count"]),
            "itemStyle": {"color": sensor_color(r["sensor"])},
        }
        for r in per_sensor
    ]

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(text="Image count per sensor", left="center", textStyle={"fontSize": 14}),
        tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
        toolbox=Toolbox(
            show=True,
            feature={"saveAsImage": {"show": True, "title": "Save PNG"}},
        ),
        grid=Grid(left=50, right=20, top=50, bottom=50, containLabel=True),
        xAxis=XAxis(
            type="category",
            data=categories,
            name="Sensor",
            axisLabel={"rotate": 20, "fontSize": 10},
        ),
        yAxis=YAxis(type="value", name="Images"),
        series=[Bar(data=data, label={"show": True, "position": "top", "fontSize": 10})],
    )

    with rv.Html(tag="div", class_="coverage-echart-sensor", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
