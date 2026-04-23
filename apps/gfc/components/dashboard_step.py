"""Dashboard step: button that opens a large modal with the GFC charts."""

from io import StringIO

import ipyvuetify as ipv
import reacton.ipyvuetify as rv
import solara
from reacton import ipyvue
from traitlets import Int, Unicode

from .dashboard import LossTrend, OverallPie, SummaryCard


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
def DashboardStep(state, legend_visible=None, sepal_map=None):
    open_dialog = solara.use_reactive(False)
    resizer = solara.use_memo(lambda: _DialogResizer(), [])

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

    def _auto_open():
        if has_data and not open_dialog.value:
            open_dialog.set(True)

    # Re-open the modal every time fresh stats arrive.
    solara.use_effect(_auto_open, [id(rows) if has_data else None])

    btn = rv.Btn(
        color="primary",
        block=True,
        small=True,
        class_="mt-2",
        disabled=not has_data,
        children=[
            rv.Icon(left=True, small=True, children=["mdi-view-dashboard"]),
            "Open dashboard",
        ],
    )
    ipyvue.use_event(btn, "click", lambda *_: open_dialog.set(True))

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
                    children=["GFC — Dashboard"],
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
