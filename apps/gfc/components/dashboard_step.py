"""Dashboard step: computes area statistics on demand and opens the modal."""

from dataclasses import dataclass
from io import StringIO

import ipyvuetify as ipv
import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications
from traitlets import Int, Unicode

from apps.gfc.scripts import compute_area_stats, parse_area_stats

from .dashboard import LossTrend, OverallPie, SummaryCard


@dataclass(frozen=True, slots=True)
class StatsRequest:
    result_image: object  # ee.Image
    aoi_fc: object  # ee.FeatureCollection


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


def _csv_bytes(rows: list[dict]) -> bytes:
    buf = StringIO()
    buf.write("code,label,area_ha\n")
    for r in rows:
        buf.write(f"{r['code']},{r['label']},{r['area_ha']}\n")
    return buf.getvalue().encode("utf-8")


@solara.component
def DashboardStep(state, gee_interface, legend_visible=None, sepal_map=None):
    notifications = use_notifications()
    open_dialog = solara.use_reactive(False)
    resizer = solara.use_memo(lambda: _DialogResizer(), [])
    compute_cancel = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def compute_task(request: StatsRequest):
        with notifications.track("Computing area statistics", total_steps=2) as task:
            task.step("Running reduceRegion on GEE")
            stats_obj = compute_area_stats(request.result_image, request.aoi_fc)
            raw = await gee_interface.get_info_async(stats_obj)
            task.step("Parsing results")
            return parse_area_stats(raw)

    def _sync_compute():
        if compute_task.pending or compute_task.cancelled:
            return
        if compute_task.error:
            notifications.error(f"Statistics failed: {compute_task.exception}")
            return
        if compute_task.finished and compute_task.value is not None:
            state.stats_rows.set(compute_task.value)
            notifications.success(
                f"Area statistics computed ({len(compute_task.value)} classes)"
            )
            open_dialog.set(True)

    solara.use_effect(
        _sync_compute,
        [compute_task.pending, compute_task.cancelled, compute_task.finished, compute_task.error],
    )

    def _start_compute():
        if state.result_image.value is None or state.aoi.value is None:
            notifications.warning("Run visualization first.")
            return
        compute_cancel.current = None
        state.stats_rows.set([])
        compute_task(
            StatsRequest(
                result_image=state.result_image.value,
                aoi_fc=state.aoi.value.feature_collection,
            )
        )

    rows = state.stats_rows.value
    has_data = bool(rows)

    def _on_open_change():
        if open_dialog.value:
            resizer.tick = resizer.tick + 1
            if legend_visible is not None:
                legend_visible.set(False)
        elif legend_visible is not None and has_data:
            legend_visible.set(True)
        return None

    solara.use_effect(_on_open_change, [open_dialog.value])

    compute_btn = use_task_button(
        compute_task, on_start=_start_compute, cancel_reason_ref=compute_cancel
    )

    TaskButtonComponent(
        label="Compute & show dashboard",
        **compute_btn,
        icon="mdi-view-dashboard",
        external_busy=state.result_image.value is None,
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
                    children=["Global Forest Change — Dashboard"],
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
    rows = state.stats_rows.value or []

    with rv.Container(fluid=True, class_="pa-0"):
        SummaryCard(
            rows=rows,
            treecover=state.treecover.value,
            year_start=state.year_start.value,
            year_end=state.year_end.value,
        )

        with rv.Row(dense=True, class_="mb-2"):
            with rv.Col(cols=12, md=5):
                OverallPie(rows)
            with rv.Col(cols=12, md=7):
                LossTrend(rows)

        with rv.Row(dense=True, class_="mt-3", justify="end"):
            with rv.Col(cols="auto"):
                with solara.FileDownload(
                    data=lambda: _csv_bytes(state.stats_rows.value or []),
                    filename="gfc_stats.csv",
                    mime_type="text/csv",
                ):
                    solara.Button(
                        label="Download CSV",
                        color="primary",
                        small=True,
                    )
