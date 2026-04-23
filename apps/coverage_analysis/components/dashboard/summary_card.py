"""Summary stats row for the Coverage Analysis dashboard."""

import reacton.ipyvuetify as rv
import solara

from apps.coverage_analysis.params import MEASURE_ITEMS

from .theme import SENSOR_LABELS

_MEASURE_LABELS = {item["value"]: item["text"] for item in MEASURE_ITEMS}


def _fmt_area(ha: float) -> str:
    if ha >= 1_000_000:
        return f"{ha / 1_000_000:.2f} Mha"
    if ha >= 1_000:
        return f"{ha / 1_000:.1f} kha"
    return f"{ha:.1f} ha"


def _fmt_sensors(sensors: list[str]) -> str:
    if not sensors:
        return "—"
    return ", ".join(SENSOR_LABELS.get(s, s) for s in sensors)


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
def SummaryCard(stats: dict | None):
    """Compact stat row with totals + parameters."""
    with rv.Row(dense=True, class_="mb-3", align="center", justify="center"):
        if not stats:
            _StatItem("mdi-alert-circle-outline", "Statistics", "—")
            return

        totals = stats.get("totals", {}) or {}
        sensors = totals.get("sensors", []) or []
        measure_label = _MEASURE_LABELS.get(totals.get("measure", ""), totals.get("measure", "—"))

        _StatItem("mdi-map", "AOI area", _fmt_area(float(totals.get("aoi_area_ha", 0.0))))
        _StatItem("mdi-calendar-range", "Date range", totals.get("date_range", "—"))
        _StatItem("mdi-image-multiple", "Total images", f"{int(totals.get('total_count', 0)):,}")
        _StatItem("mdi-satellite-variant", "Sensors", _fmt_sensors(sensors))
        _StatItem("mdi-chart-line", "Measure", measure_label)
