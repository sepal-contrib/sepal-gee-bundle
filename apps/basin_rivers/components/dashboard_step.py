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
def DashboardStep(state, theme_toggle, legend_visible=None, legend_data=None):
    open_dialog = solara.use_reactive(False)
    resizer = solara.use_memo(lambda: _DialogResizer(), [])

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

    if not has_data:
        return

    solara.Button(
        label="Open dashboard",
        icon_name="mdi-chart-bar",
        on_click=lambda: open_dialog.set(True),
        color="primary",
        block=True,
        small=True,
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
                _DashboardContent(state, theme_toggle, legend_data)


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
def _DashboardContent(state, theme_toggle, legend_data=None):
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

        with rv.Row(dense=True, class_="mt-3", justify="end"):
            with rv.Col(cols="auto"):
                solara.FileDownload(
                    data=lambda: _csv_bytes(state.zonal_df.value),
                    filename="basin_rivers_stats.csv",
                    mime_type="text/csv",
                    label="Download CSV",
                )
