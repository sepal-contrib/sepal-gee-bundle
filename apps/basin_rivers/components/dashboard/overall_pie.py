"""Overall forest-change donut.

The selected slice (`state.selected_var`) is visually emphasized via ECharts'
`selectedMode`. Variable selection itself is driven by the settings card
dropdown. Click-to-select on the slice is a known-broken pattern with
ipecharts-in-solara (reacton `Element.on()` ≠ ipywidget `.on()`) and is a
follow-up.
"""

import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Tooltip
from ipecharts.option.series import Pie

from apps.basin_rivers.scripts.statistics import get_overall_pie_df

from .theme import use_echarts_theme


@solara.component
def OverallPie(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)

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
        title=Title(text="Overall forest change", left="center"),
        tooltip=Tooltip(trigger="item", formatter="{b}: {c} ha ({d}%)"),
        legend=Legend(orient="horizontal", bottom=0),
        series=[
            Pie(
                radius=["50%", "70%"],
                data=data,
                label={"show": True, "formatter": "{b}: {d}%"},
                selectedMode="single",
                emphasis={"scale": True, "scaleSize": 10},
            )
        ],
    )

    EChartsWidget.element(option=option, theme=theme, style={"height": "320px"})
