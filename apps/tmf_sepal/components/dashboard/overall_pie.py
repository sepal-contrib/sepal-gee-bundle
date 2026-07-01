"""Overall TMF class/year-share donut."""

import reacton.ipyvuetify as rv
import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Toolbox, Tooltip
from ipecharts.option.series import Pie

from .theme import (
    CHG_CLASS_COLORS,
    CHG_CLASS_LABELS,
    MAIN_CLASS_COLORS,
    MAIN_CLASS_LABELS,
    use_echarts_theme,
    year_color,
)


def _class_data(rows: list[dict], color_by_code: dict, label_by_code: dict) -> list[dict]:
    data: list[dict] = []
    for r in rows:
        code = int(r["code"])
        area = float(r["area_ha"])
        if area <= 0:
            continue
        color = color_by_code.get(code) or r.get("color")
        label = label_by_code.get(code) or r.get("label") or f"class {code}"
        item: dict = {"value": round(area, 2), "name": label}
        if color:
            item["itemStyle"] = {"color": color}
        data.append(item)
    return data


def _year_data(rows: list[dict]) -> list[dict]:
    years = [int(r["code"]) for r in rows if float(r["area_ha"]) > 0]
    if not years:
        return []
    y0, y1 = min(years), max(years)
    data: list[dict] = []
    for r in rows:
        area = float(r["area_ha"])
        if area <= 0:
            continue
        year = int(r["code"])
        data.append(
            {
                "value": round(area, 2),
                "name": str(year),
                "itemStyle": {"color": year_color(year, y0, y1)},
            }
        )
    return data


@solara.component
def OverallPie(rows: list, tmf_type: str):
    theme = use_echarts_theme()

    if not rows:
        solara.Text("Run statistics to see the distribution.")
        return

    if tmf_type == "CHG":
        data = _class_data(rows, CHG_CLASS_COLORS, CHG_CLASS_LABELS)
        title_text = "Change between two years"
    elif tmf_type == "TRANS":
        data = _class_data(rows, MAIN_CLASS_COLORS, MAIN_CLASS_LABELS)
        title_text = "Transition map (full record)"
    else:
        data = _year_data(rows)
        title_text = "Degradation by year" if tmf_type == "DEG" else "Deforestation by year"

    if not data:
        solara.Text("No classified pixels in AOI.")
        return

    option = Option(
        backgroundColor="#1e1e1e00",
        title=Title(text=title_text, left="center", textStyle={"fontSize": 14}),
        tooltip=Tooltip(trigger="item", formatter="{b}: {c} ha ({d}%)"),
        legend=Legend(
            # Categorical layers (few items) wrap onto up to ~2 rows inside a
            # capped, centered width; year layers (many items) stay a single
            # paginated row. ECharts scroll legends are single-row by design,
            # so the categorical case uses a plain (wrapping) legend.
            type="plain" if tmf_type in ("CHG", "TRANS") else "scroll",
            orient="horizontal",
            bottom=0,
            left="center",
            width="60%",
            textStyle={"fontSize": 10},
        ),
        toolbox=Toolbox(
            show=True,
            feature={"saveAsImage": {"show": True, "title": "Save PNG"}},
        ),
        series=[
            Pie(
                radius=["25%", "62%"],
                center=["50%", "42%"],
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

    with rv.Html(tag="div", class_="tmf-echart-overall", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
