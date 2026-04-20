"""Dashboard step: button that opens a large modal with the charts."""

from io import StringIO

import ipyvuetify as ipv
import reacton.ipyvuetify as rv
import solara
from traitlets import Int, Unicode

from .dashboard import CatchmentBar, CatchmentPie, LossTrend, OverallPie, SettingsCard


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
def DashboardStep(state, theme_toggle):
    open_dialog = solara.use_reactive(False)
    resizer = solara.use_memo(lambda: _DialogResizer(), [])

    df = state.zonal_df.value
    has_data = df is not None and not df.empty

    def _bump_resize():
        if open_dialog.value:
            resizer.tick = resizer.tick + 1
        return None

    solara.use_effect(_bump_resize, [open_dialog.value])

    def _toggle_theme():
        theme_toggle.dark = not bool(getattr(theme_toggle, "dark", False))

    if not has_data:
        solara.Text("Run delineation and calculate statistics to see results.")
        return

    solara.Text(f"{len(state.hybasin_list.value)} basins · {len(df)} stats rows")

    solara.Button(
        label="Open dashboard",
        icon_name="mdi-chart-bar",
        on_click=lambda: open_dialog.set(True),
        color="primary",
        block=True,
        classes=["mt-2"],
    )

    with rv.Dialog(
        v_model=open_dialog.value,
        on_v_model=open_dialog.set,
        max_width="1400px",
        scrollable=True,
        eager=True,
    ):
        with rv.Card():
            with rv.Toolbar(dark=True, color="primary", dense=True, flat=True):
                rv.ToolbarTitle(children=["Basin Rivers — Dashboard"])
                rv.Spacer()
                solara.FileDownload(
                    data=lambda: _csv_bytes(state.zonal_df.value),
                    filename="basin_rivers_stats.csv",
                    mime_type="text/csv",
                    label="CSV",
                )
                solara.Button(
                    icon_name="mdi-theme-light-dark",
                    icon=True,
                    on_click=_toggle_theme,
                    color="white",
                )
                solara.Button(
                    icon_name="mdi-close",
                    icon=True,
                    on_click=lambda: open_dialog.set(False),
                    color="white",
                )

            with rv.CardText(style_="padding: 16px;"):
                # Mount the resizer inside the dialog so it lives in the DOM.
                rv.Html(tag="div", children=[resizer], style_="display:none;")
                _DashboardContent(state, theme_toggle)


@solara.component
def _DashboardContent(state, theme_toggle):
    with rv.Container(fluid=True, class_="pa-0"):
        with rv.Row(dense=True, class_="mb-2"):
            with rv.Col(cols=12, md=5):
                SettingsCard(state)
            with rv.Col(cols=12, md=7):
                OverallPie(state, theme_toggle)

        with rv.Row(dense=True, class_="mb-2"):
            with rv.Col(cols=12, md=5):
                CatchmentPie(state, theme_toggle)
            with rv.Col(cols=12, md=7):
                CatchmentBar(state, theme_toggle)

        if state.selected_var.value == "loss":
            with rv.Row(dense=True):
                with rv.Col(cols=12):
                    LossTrend(state, theme_toggle)
