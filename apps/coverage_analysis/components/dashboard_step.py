"""Dashboard step for Coverage Analysis.

Separate compute-stats button + modal launcher mirroring the GFC pattern.
Image counts are cheap ``size()`` calls, so they're computed on-demand
here rather than folded into the visualize task (keeps visualize snappy).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import StringIO

import ipyvuetify as ipv
import pandas as pd
import reacton.ipyvuetify as rv
import solara
from pysepal.solara import get_current_gee_interface
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications
from reacton import ipyvue
from traitlets import Int, Unicode

from apps.coverage_analysis.scripts import compute_dashboard_stats

from .dashboard import SensorBar, SummaryCard, YearBar

logger = logging.getLogger("sepal_gee_bundle.coverage_analysis")


class _DialogResizer(ipv.VuetifyTemplate):
    """Dispatch a window resize event whenever `tick` changes.

    ECharts measures zero width when mounted inside a just-opened dialog.
    Bumping `tick` after dialog open forces the widget to re-layout.
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


@dataclass(frozen=True, slots=True)
class _StatsRequest:
    aoi_fc: object
    start: str
    end: str
    sensors: tuple[str, ...]
    sr: bool
    t2: bool
    measure: str


def _csv_bytes(stats: dict | None) -> bytes:
    buf = StringIO()
    if not stats:
        buf.write("group,name,count\n")
        return buf.getvalue().encode("utf-8")

    rows: list[dict] = []
    for r in stats.get("per_sensor", []) or []:
        rows.append({"group": "sensor", "name": r["sensor"], "count": int(r["count"])})
    for r in stats.get("per_year", []) or []:
        rows.append({"group": "year", "name": str(r["year"]), "count": int(r["count"])})

    df = pd.DataFrame(rows, columns=["group", "name", "count"])
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


@solara.component
def DashboardStep(state, legend_visible=None, sepal_map=None):
    notifications = use_notifications()
    open_dialog = solara.use_reactive(False)
    resizer = solara.use_memo(lambda: _DialogResizer(), [])
    compute_cancel = solara.use_ref(None)

    stats = state.dashboard_stats.value
    has_data = bool(stats)

    # Session-backed GEE interface for the async counts.
    gee_interface = get_current_gee_interface()

    # --- Compute task ---
    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def compute_task(request: _StatsRequest):
        with notifications.track("Computing dashboard stats", total_steps=2) as task:
            task.step("Counting images per sensor & year")
            result = await compute_dashboard_stats(
                aoi=request.aoi_fc,
                start=request.start,
                end=request.end,
                sensors=list(request.sensors),
                sr=request.sr,
                include_t2=request.t2,
                measure=request.measure,
                gee_interface=gee_interface,
            )
            task.step("Packaging results")
            return result

    def _sync_compute():
        if compute_task.pending or compute_task.cancelled:
            return
        if compute_task.error:
            notifications.error(f"Dashboard stats failed: {compute_task.exception}")
            return
        if compute_task.finished and compute_task.value is not None:
            state.dashboard_stats.set(compute_task.value)
            total = compute_task.value.get("totals", {}).get("total_count", 0)
            logger.info("Dashboard stats computed: %d total images", int(total or 0))
            notifications.success(f"Dashboard ready ({int(total or 0)} images)")

    solara.use_effect(
        _sync_compute,
        [compute_task.pending, compute_task.cancelled, compute_task.finished, compute_task.error],
    )

    def _start_compute():
        if state.aoi.value is None:
            notifications.warning("Select an AOI first.")
            return
        if state.collection.value is None:
            notifications.warning("Run 'Show on map' first.")
            return
        if not state.sensors.value:
            notifications.warning("Select at least one sensor.")
            return
        compute_cancel.current = None
        state.dashboard_stats.set(None)
        compute_task(
            _StatsRequest(
                aoi_fc=state.aoi.value.feature_collection,
                start=state.start_date.value,
                end=state.end_date.value,
                sensors=tuple(state.sensors.value),
                sr=bool(state.surface_reflectance.value),
                t2=bool(state.include_tier2.value),
                measure=state.measure.value,
            )
        )

    compute_btn = use_task_button(
        compute_task, on_start=_start_compute, cancel_reason_ref=compute_cancel
    )

    # --- Dialog open/close + legend hide/restore ---
    def _on_open_change():
        if open_dialog.value:
            resizer.tick = resizer.tick + 1
            if legend_visible is not None:
                legend_visible.set(False)
        elif legend_visible is not None and has_data:
            legend_visible.set(True)
        return None

    solara.use_effect(_on_open_change, [open_dialog.value])

    def _auto_open():
        if has_data and not open_dialog.value:
            open_dialog.set(True)

    # Re-open the modal every time fresh stats arrive.
    solara.use_effect(_auto_open, [id(stats) if has_data else None])

    # --- UI ---
    with solara.Column():
        TaskButtonComponent(
            label="Compute dashboard stats",
            **compute_btn,
            external_busy=state.collection.value is None,
            small=True,
            block=True,
        )

        open_btn = rv.Btn(
            color="primary",
            block=True,
            small=True,
            class_="mt-2",
            disabled=not has_data,
            children=["Open dashboard"],
        )
        ipyvue.use_event(open_btn, "click", lambda *_: open_dialog.set(True))

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
                        children=["Coverage Analysis — Dashboard"],
                    )
                    rv.Spacer()
                    solara.Button(
                        icon_name="mdi-close",
                        icon=True,
                        on_click=lambda: open_dialog.set(False),
                    )

                rv.Divider()

                with rv.CardText(class_="pa-4"):
                    rv.Html(tag="div", children=[resizer], style_="display:none;")
                    _DashboardContent(state)


@solara.component
def _DashboardContent(state):
    stats = state.dashboard_stats.value or {}
    per_sensor = stats.get("per_sensor", []) or []
    per_year = stats.get("per_year", []) or []

    with rv.Container(fluid=True, class_="pa-0"):
        SummaryCard(stats=stats)

        with rv.Row(dense=True, class_="mb-2"):
            with rv.Col(cols=12, md=6):
                SensorBar(per_sensor)
            with rv.Col(cols=12, md=6):
                YearBar(per_year)

        with rv.Row(dense=True, class_="mt-3", justify="end"):
            with rv.Col(cols="auto"):
                with solara.FileDownload(
                    data=lambda: _csv_bytes(state.dashboard_stats.value),
                    filename="coverage_analysis_stats.csv",
                    mime_type="text/csv",
                ):
                    solara.Button(
                        label="Download CSV",
                        color="primary",
                        small=True,
                    )
