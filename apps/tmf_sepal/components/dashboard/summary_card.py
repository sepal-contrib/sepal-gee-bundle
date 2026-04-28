"""Summary stats row for the TMF dashboard."""

import reacton.ipyvuetify as rv
import solara


def _fmt_area(ha: float) -> str:
    if ha >= 1_000_000:
        return f"{ha / 1_000_000:.2f} Mha"
    if ha >= 1_000:
        return f"{ha / 1_000:.1f} kha"
    return f"{ha:.1f} ha"


_TYPE_LABEL = {
    "DEG": "Degradation year",
    "DEF": "Deforestation year",
    "CHG": "Annual change",
}

_TYPE_TOTAL_LABEL = {
    "DEG": "Degraded area",
    "DEF": "Deforested area",
    "CHG": "Classified area",
}

_TYPE_TOTAL_ICON = {
    "DEG": "mdi-tree",
    "DEF": "mdi-tree-outline",
    "CHG": "mdi-layers",
}


def summarize(rows: list[dict], tmf_type: str) -> dict:
    total = sum(float(r["area_ha"]) for r in rows)
    if tmf_type in ("DEG", "DEF"):
        years = [int(r["code"]) for r in rows if float(r["area_ha"]) > 0]
        y0 = min(years) if years else None
        y1 = max(years) if years else None
    else:
        y0 = y1 = None
    return {"total": total, "year_min": y0, "year_max": y1}


@solara.component
def _StatItem(icon: str, label: str, value: str):
    with rv.Col(cols="auto", class_="pa-0"):
        with rv.ListItem(dense=True, class_="pa-0 pr-4"):
            with rv.ListItemIcon(class_="mr-2 my-auto"):
                rv.Icon(small=True, color="primary", children=[icon])
            with rv.ListItemContent(class_="py-1"):
                rv.ListItemTitle(
                    class_="caption",
                    style_="opacity: 0.6;",
                    children=[label],
                )
                rv.ListItemSubtitle(class_="body-2", children=[value])


@solara.component
def SummaryCard(rows: list, tmf_type: str, year_start: int, year_end: int):
    """Compact stat row with TMF totals + selected range + layer type."""
    with rv.Row(dense=True, class_="mb-6", align="center", justify="center"):
        if not rows:
            _StatItem("mdi-alert-circle-outline", "Statistics", "—")
            return

        totals = summarize(rows, tmf_type)

        _StatItem(
            _TYPE_TOTAL_ICON.get(tmf_type, "mdi-map"),
            _TYPE_TOTAL_LABEL.get(tmf_type, "Total area"),
            _fmt_area(totals["total"]),
        )

        if tmf_type in ("DEG", "DEF") and totals["year_min"] is not None:
            _StatItem(
                "mdi-calendar-range",
                "Event year range",
                f"{totals['year_min']}-{totals['year_max']}",
            )
            _StatItem(
                "mdi-format-list-numbered",
                "Years with events",
                str(sum(1 for r in rows if float(r["area_ha"]) > 0)),
            )
        elif tmf_type == "CHG":
            _StatItem(
                "mdi-shape",
                "Classes present",
                str(sum(1 for r in rows if float(r["area_ha"]) > 0)),
            )

        _StatItem(
            "mdi-calendar-range",
            "Selected range",
            f"{year_start}-{year_end}",
        )
        _StatItem(
            "mdi-layers",
            "TMF layer",
            _TYPE_LABEL.get(tmf_type, tmf_type),
        )
