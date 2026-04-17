"""Overall forest-change donut. Click a slice to set selected_var."""

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
            "_group": row["group"],
        }
        for _, row in pie_df.iterrows()
    ]

    pie = Pie(
        radius=["50%", "70%"],
        data=data,
        label={"show": True, "formatter": "{b}: {d}%"},
        emphasis={"scale": True, "scaleSize": 10},
    )

    option = Option(
        title=Title(text="Overall forest change", left="center"),
        tooltip=Tooltip(trigger="item", formatter="{b}: {c} ha ({d}%)"),
        legend=Legend(orient="horizontal", bottom=0),
        series=[pie],
    )

    def on_click(params):
        group = (params or {}).get("data", {}).get("_group")
        if not group:
            return
        state.selected_var.value = "all" if selected == group else group

    chart = EChartsWidget.element(
        option=option, theme=theme, style={"height": "320px"}
    )

    def _attach_click():
        widget = getattr(chart, "widget", None)
        if widget is not None:
            widget.on("click", None, on_click)
            return lambda: widget.off("click", on_click)
        return None

    solara.use_effect(_attach_click, [id(chart)])
