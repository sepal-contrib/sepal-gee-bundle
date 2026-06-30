"""Dashboard step: computes zonal statistics on demand and opens the modal."""

from dataclasses import dataclass
from io import StringIO

import ee
import ipyvuetify as ipv
import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications
from traitlets import Int, Unicode

from apps.basin_rivers.params import MAX_CATCH_DISPLAY
from apps.basin_rivers.scripts import (
    add_catchment_colors,
    classify_gfc,
    compute_zonal_stats,
    get_hydroshed_collection,
    parse_zonal_stats,
)
from pdf_report import (
    EChartCapture,
    LegendCapture,
    MapCapture,
    PdfReportButton,
    PdfReportConfig,
    StatsTableCapture,
)

from .dashboard import CatchmentBar, CatchmentPie, LossTrend, OverallPie, SettingsCard


@dataclass(frozen=True, slots=True)
class StatsRequest:
    level: int
    hybas_ids: tuple[int, ...]
    year_start: int
    year_end: int
    treecover: int


class _DialogResizer(ipv.VuetifyTemplate):
    """Dispatches a window resize event every time `tick` changes.

    ECharts listens for window `resize` events and recalculates its canvas
    dimensions. When a chart is mounted inside a just-opened dialog it starts
    out measuring the (zero-width) pre-animation size; we need to nudge it
    after the dialog has settled.
    """

    tick = Int(0).tag(sync=True)
    template = Unicode(
        """
        <script class='dashboard-resize'>
        {
            watch: {
                tick() {
                    this.$nextTick(() => {
                        setTimeout(() => {
                            window.dispatchEvent(new Event("resize"));
                        }, 120);
                    });
                }
            }
        }
        </script>
        """
    ).tag(sync=True)


def _csv_bytes(df) -> bytes:
    buf = StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


@solara.component
def DashboardStep(state, gee_interface, legend_visible=None, legend_data=None, sepal_map=None):
    notifications = use_notifications()
    open_dialog = solara.use_reactive(False)
    resizer = solara.use_memo(lambda: _DialogResizer(), [])
    stats_cancel = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def stats_task(request: StatsRequest):
        with notifications.track("Computing zonal statistics", total_steps=3) as task:
            task.step("Building basin selection...")
            base_fc = get_hydroshed_collection(request.level)
            selected_fc = base_fc.filter(ee.Filter.inList("HYBAS_ID", list(request.hybas_ids)))

            task.step("Classifying GFC forest change...")
            gfc_image = classify_gfc(
                selected_fc, request.treecover, request.year_start, request.year_end
            )

            task.step("Running reduceRegions...")
            stats_fc = compute_zonal_stats(gfc_image, selected_fc)
            raw = await gee_interface.get_info_async(stats_fc)
        return parse_zonal_stats(raw)

    def _sync_stats():
        if stats_task.pending or stats_task.cancelled:
            return
        if stats_task.error:
            notifications.error(f"Statistics failed: {stats_task.exception}")
            return
        if stats_task.finished and stats_task.value is not None:
            df = add_catchment_colors(stats_task.value)
            state.zonal_df.value = df
            state.selected_var.value = "all"

            seed_ids = state.hybasin_list.value
            seed_strs = [str(b) for b in seed_ids]
            if len(seed_strs) > MAX_CATCH_DISPLAY:
                totals = (
                    df[df["basin"].astype(str).isin(seed_strs)]
                    .groupby("basin")["area"]
                    .sum()
                    .sort_values(ascending=False)
                )
                seed_strs = [str(b) for b in totals.head(MAX_CATCH_DISPLAY).index.tolist()]
                notifications.info(
                    f"Showing top {MAX_CATCH_DISPLAY} basins by area in the dashboard. "
                    f"Adjust the Catchments selector to include more."
                )
            state.selected_hybasid_chart.value = seed_strs
            state.sett_timespan.value = (state.year_start.value, state.year_end.value)

            notifications.success("Statistics ready")
            open_dialog.set(True)

    solara.use_effect(
        _sync_stats,
        [stats_task.pending, stats_task.cancelled, stats_task.finished, stats_task.error],
    )

    def _start_stats():
        ids = state.hybasin_list.value
        if not ids:
            notifications.warning("Trace the watershed first.")
            return
        stats_cancel.current = None
        state.zonal_df.value = None
        stats_task(
            StatsRequest(
                level=state.level.value,
                hybas_ids=tuple(ids),
                year_start=state.year_start.value,
                year_end=state.year_end.value,
                treecover=state.treecover.value,
            )
        )

    df = state.zonal_df.value
    has_data = df is not None and not df.empty

    def _on_open_change():
        if open_dialog.value:
            resizer.tick = resizer.tick + 1
            if legend_visible is not None:
                legend_visible.set(False)
        elif legend_visible is not None and has_data:
            legend_visible.set(True)
        return None

    solara.use_effect(_on_open_change, [open_dialog.value])

    stats_btn = use_task_button(stats_task, on_start=_start_stats, cancel_reason_ref=stats_cancel)

    TaskButtonComponent(
        label="Compute & show dashboard",
        **stats_btn,
        external_busy=not state.hybasin_list.value,
        small=True,
        block=True,
    )

    with rv.Dialog(
        v_model=open_dialog.value and has_data,
        on_v_model=open_dialog.set,
        max_width="1400px",
        scrollable=True,
        eager=True,
    ):
        with rv.Card():
            with rv.CardTitle(class_="d-flex align-center py-3 px-4"):
                rv.Icon(color="primary", class_="mr-2", children=["mdi-chart-bar"])
                rv.Html(
                    tag="span",
                    class_="text-h6",
                    children=["Basin Rivers — Dashboard"],
                )
                rv.Spacer()
                solara.Button(
                    icon_name="mdi-close",
                    icon=True,
                    on_click=lambda: open_dialog.set(False),
                )

            rv.Divider()

            with rv.CardText(class_="pa-4"):
                # Mount the resizer inside the dialog so it lives in the DOM.
                rv.Html(tag="div", children=[resizer], style_="display:none;")
                _DashboardContent(state, legend_data, sepal_map)


def _fmt_area(ha: float) -> str:
    """Compact ha / kha / Mha formatting."""
    if ha >= 1_000_000:
        return f"{ha / 1_000_000:.2f} Mha"
    if ha >= 1_000:
        return f"{ha / 1_000:.1f} kha"
    return f"{ha:.1f} ha"


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
def _DashboardContent(state, legend_data=None, sepal_map=None):
    df = state.zonal_df.value
    has_rows = df is not None and not df.empty
    n_basins = int(df["basin"].nunique()) if has_rows else 0
    total_area = float(df["area"].sum()) if has_rows else 0.0
    forest_area = float(df.loc[df["group"] == "forest", "area"].sum()) if has_rows else 0.0
    loss_area = float(df.loc[df["group"] == "loss", "area"].sum()) if has_rows else 0.0
    forest_pct = (forest_area / total_area * 100.0) if total_area > 0 else 0.0
    loss_pct = (loss_area / total_area * 100.0) if total_area > 0 else 0.0

    with rv.Container(fluid=True, class_="pa-0"):
        with rv.Row(dense=True, class_="mb-3", align="center", justify="center"):
            _StatItem("mdi-waves", "Upstream basins", str(n_basins))
            _StatItem("mdi-map", "Watershed area", _fmt_area(total_area))
            _StatItem(
                "mdi-tree",
                "Stable forest",
                f"{_fmt_area(forest_area)} ({forest_pct:.1f}%)",
            )
            _StatItem(
                "mdi-trending-down",
                "Forest loss",
                f"{_fmt_area(loss_area)} ({loss_pct:.1f}%)",
            )
            _StatItem(
                "mdi-calendar-range",
                "Years",
                f"{state.year_start.value}-{state.year_end.value}",
            )

        with rv.Row(dense=True, class_="mb-2"):
            with rv.Col(cols=12, md=5):
                SettingsCard(state)
            with rv.Col(cols=12, md=7):
                OverallPie(state)

        with rv.Row(dense=True, class_="mb-2"):
            with rv.Col(cols=12, md=5):
                CatchmentPie(state)
            with rv.Col(cols=12, md=7):
                CatchmentBar(state)

        if state.selected_var.value == "loss":
            with rv.Row(dense=True):
                with rv.Col(cols=12):
                    LossTrend(state)

        with rv.Row(dense=True, class_="mt-3", justify="end"):
            with rv.Col(cols="auto"):
                with solara.FileDownload(
                    data=lambda: _csv_bytes(state.zonal_df.value),
                    filename="basin_rivers_stats.csv",
                    mime_type="text/csv",
                ):
                    solara.Button(
                        label="Download CSV",
                        color="primary",
                        small=True,
                    )
            with rv.Col(cols="auto"):
                if sepal_map is not None:
                    _outlet_str = (
                        f"{state.lat.value:.4f}, {state.lon.value:.4f}"
                        if state.lat.value is not None and state.lon.value is not None
                        else "—"
                    )
                    PdfReportButton(
                        filename="basin_rivers_report.pdf",
                        config=PdfReportConfig(
                            title="Basin Rivers — Watershed Report",
                            subtitle="Upstream delineation & forest change",
                            metadata=(
                                ("Outlet", _outlet_str),
                                ("HydroSHEDS level", str(state.level.value)),
                                (
                                    "Year range",
                                    f"{state.year_start.value}-{state.year_end.value}",
                                ),
                                ("Tree cover threshold", f"{state.treecover.value}%"),
                                ("Upstream basins", str(n_basins)),
                                ("Watershed area", _fmt_area(total_area)),
                                (
                                    "Stable forest",
                                    f"{_fmt_area(forest_area)} ({forest_pct:.1f}%)",
                                ),
                                (
                                    "Forest loss",
                                    f"{_fmt_area(loss_area)} ({loss_pct:.1f}%)",
                                ),
                            ),
                        ),
                        captures=(
                            MapCapture(selector=f".{sepal_map._id}", label="Map view"),
                            LegendCapture(
                                legend_data=(legend_data.value if legend_data is not None else {}),
                                title="Legend",
                            ),
                            StatsTableCapture(
                                title="Summary",
                                rows=(
                                    (
                                        "Stable forest",
                                        f"{_fmt_area(forest_area)} ({forest_pct:.1f}%)",
                                    ),
                                    (
                                        "Forest loss",
                                        f"{_fmt_area(loss_area)} ({loss_pct:.1f}%)",
                                    ),
                                ),
                            ),
                            EChartCapture(
                                selector=".br-echart-overall",
                                label="Forest composition",
                            ),
                            EChartCapture(
                                selector=".br-echart-catchment-pie",
                                label="Per-catchment share",
                            ),
                            EChartCapture(
                                selector=".br-echart-catchment-bar",
                                label="Per-catchment breakdown",
                                width_fraction=1.0,
                            ),
                            EChartCapture(
                                selector=".br-echart-loss-trend",
                                label="Loss over time",
                                optional=True,
                                width_fraction=1.0,
                            ),
                        ),
                        label="Download PDF",
                        icon_name="",
                    )
