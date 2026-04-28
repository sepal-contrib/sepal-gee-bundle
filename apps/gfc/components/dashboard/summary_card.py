"""Summary stats row for the GFC dashboard."""

import reacton.ipyvuetify as rv
import solara

from apps.gfc.params import GFC_MAX_YEAR


def _fmt_area(ha: float) -> str:
    if ha >= 1_000_000:
        return f"{ha / 1_000_000:.2f} Mha"
    if ha >= 1_000:
        return f"{ha / 1_000:.1f} kha"
    return f"{ha:.1f} ha"


def summarize(rows: list[dict]) -> dict:
    """Return aggregate totals for the summary card."""
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
    totals["total"] = sum(totals.values())
    totals["forest_pct"] = (
        totals["forest"] / totals["total"] * 100.0 if totals["total"] > 0 else 0.0
    )
    totals["loss_pct"] = totals["loss"] / totals["total"] * 100.0 if totals["total"] > 0 else 0.0
    return totals


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
def SummaryCard(rows: list, treecover: int, year_start: int, year_end: int):
    """Compact stat row with AOI totals + loss/forest shares + parameters."""
    totals = summarize(rows) if rows else None

    with rv.Row(dense=True, class_="mb-6", align="center", justify="center"):
        if totals is None:
            _StatItem("mdi-alert-circle-outline", "Statistics", "—")
            return

        _StatItem("mdi-map", "AOI area", _fmt_area(totals["total"]))
        _StatItem(
            "mdi-tree",
            "Stable forest",
            f"{_fmt_area(totals['forest'])} ({totals['forest_pct']:.1f}%)",
        )
        _StatItem(
            "mdi-trending-down",
            "Forest loss",
            f"{_fmt_area(totals['loss'])} ({totals['loss_pct']:.1f}%)",
        )
        _StatItem("mdi-sprout", "Gain", _fmt_area(totals["gains"]))
        _StatItem("mdi-swap-vertical", "Gain + Loss", _fmt_area(totals["gain_loss"]))
        _StatItem("mdi-percent", "Tree cover threshold", f"{treecover}%")
        _StatItem("mdi-calendar-range", "Years", f"{year_start}-{year_end}")
