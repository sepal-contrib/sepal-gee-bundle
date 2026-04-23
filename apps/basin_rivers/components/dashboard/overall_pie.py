"""Overall forest-change donut.

The selected slice (`state.selected_var`) is visually emphasized via ECharts'
`selectedMode`. Variable selection itself is driven by the settings card
dropdown. Click-to-select on the slice is a known-broken pattern with
ipecharts-in-solara (reacton `Element.on()` ≠ ipywidget `.on()`) and is a
follow-up.
"""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Toolbox, Tooltip
from ipecharts.option.series import Pie

from apps.basin_rivers.scripts.statistics import get_overall_pie_df

from .theme import use_echarts_theme


@solara.component
def OverallPie(state):
    theme = use_echarts_theme()

    df = state.zonal_df.value
    selected = state.selected_var.value

    if df is None or df.empty:
        solara.Text("Run statistics to see the overall distribution.")
        return

    pie_df = get_overall_pie_df(df)
    data = [
        {
            "value": round(float(row["area"]), 2),
            "name": row["group"].replace("_", " ").title(),
            "itemStyle": {"color": row["color"]},
            "selected": row["group"] == selected,
        }
        for _, row in pie_df.iterrows()
    ]

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(text="Overall forest change", left="center", textStyle={"fontSize": 14}),
        tooltip=Tooltip(trigger="item", formatter="{b}: {c} ha ({d}%)"),
        legend=Legend(orient="horizontal", bottom=0, textStyle={"fontSize": 11}),
        toolbox=Toolbox(
            show=True,
            feature={"saveAsImage": {"show": True, "title": "Save PNG"}},
        ),
        series=[
            Pie(
                radius=["25%", "70%"],
                center=["50%", "45%"],
                data=data,
                label={
                    "show": True,
                    "position": "inside",
                    "formatter": "{d}%",
                    "fontSize": 11,
                    "color": "#fff",
                    "textBorderColor": "rgba(0,0,0,0.5)",
                    "textBorderWidth": 2,
                },
                labelLine={"show": False},
                minShowLabelAngle=15,
                selectedMode="single",
                emphasis={"scale": True, "scaleSize": 8},
            )
        ],
    )

    with rv.Html(tag="div", class_="br-echart-overall", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
