"""Overall GFC class-share donut (stable forest / non-forest / gain / gain+loss / loss)."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Toolbox, Tooltip
from ipecharts.option.series import Pie

from apps.gfc.params import GFC_MAX_YEAR

from .theme import CLASS_COLORS, use_echarts_theme


def _aggregate(rows: list[dict]) -> list[dict]:
    """Aggregate raw stats rows into top-level class totals."""
    totals = {"forest": 0.0, "non_forest": 0.0, "gains": 0.0, "gain_loss": 0.0, "loss": 0.0}
    for r in rows:
        code = r["code"]
        area = float(r["area_ha"])
        if 1 <= code <= GFC_MAX_YEAR:
            totals["loss"] += area
        elif code == 30:
            totals["non_forest"] += area
        elif code == 40:
            totals["forest"] += area
        elif code == 50:
            totals["gains"] += area
        elif code == 51:
            totals["gain_loss"] += area
    labels = {
        "forest": "Stable forest",
        "non_forest": "Non-forest",
        "gains": "Gain",
        "gain_loss": "Gain + Loss",
        "loss": "Loss",
    }
    return [
        {
            "value": round(totals[k], 2),
            "name": labels[k],
            "itemStyle": {"color": CLASS_COLORS[k]},
        }
        for k in ("forest", "non_forest", "gains", "gain_loss", "loss")
        if totals[k] > 0
    ]


@solara.component
def OverallPie(rows: list):
    theme = use_echarts_theme()

    if not rows:
        solara.Text("Run statistics to see the overall distribution.")
        return

    data = _aggregate(rows)
    if not data:
        solara.Text("No classified pixels in AOI.")
        return

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
                emphasis={"scale": True, "scaleSize": 8},
            )
        ],
    )

    with rv.Html(tag="div", class_="gfc-echart-overall", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
