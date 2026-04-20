"""Per-catchment donut for the selected variable."""

import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Tooltip
from ipecharts.option.series import Pie

from apps.basin_rivers.params import CATCH_PIE_TITLES
from apps.basin_rivers.scripts.statistics import get_catchment_pie_df

from .theme import use_echarts_theme


@solara.component
def CatchmentPie(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)

    df = state.zonal_df.value
    selected = state.selected_var.value
    basins = state.selected_hybasid_chart.value

    if df is None or df.empty or not basins:
        solara.Text("Select catchments to see per-basin share.")
        return

    filtered = df[df["basin"].astype(str).isin([str(b) for b in basins])]
    pie_df = get_catchment_pie_df(filtered, selected)
    if pie_df.empty:
        solara.Text(f"No {selected.replace('_', ' ')} area in the selected basins.")
        return

    data = [
        {
            "value": round(float(row["area"]), 2),
            "name": str(row["basin"]),
            "itemStyle": {"color": row["catch_color"]},
        }
        for _, row in pie_df.iterrows()
    ]

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(
            text=CATCH_PIE_TITLES.get(selected, ""), left="center", textStyle={"fontSize": 14}
        ),
        tooltip=Tooltip(trigger="item", formatter="Basin {b}: {c} ha ({d}%)"),
        legend=Legend(orient="horizontal", bottom=0, textStyle={"fontSize": 10}),
        series=[
            Pie(
                radius=["25%", "70%"],
                center=["50%", "45%"],
                data=data,
                label={"show": True, "formatter": "{d}%", "fontSize": 11},
            )
        ],
    )

    EChartsWidget.element(option=option, theme=theme, style={"height": "340px", "width": "100%"})
