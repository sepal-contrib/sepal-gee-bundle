"""Dashboard step: button that opens a fullscreen modal with the charts."""

import reacton.ipyvuetify as rv
import solara

from .dashboard import CatchmentBar, CatchmentPie, LossTrend, OverallPie, SettingsCard


@solara.component
def DashboardStep(state, theme_toggle):
    open_dialog = solara.use_reactive(False)

    df = state.zonal_df.value
    has_data = df is not None and not df.empty

    if not has_data:
        solara.Text("Run delineation and calculate statistics to see results.")
        return

    solara.Text(f"{len(state.hybasin_list.value)} basins · {len(df)} stats rows")

    rv.Btn(
        children=[
            rv.Icon(left=True, children=["mdi-chart-bar"]),
            "Open dashboard",
        ],
        color="primary",
        block=True,
        class_="mt-2",
        on_click=lambda *_: open_dialog.set(True),
    )

    with rv.Dialog(
        v_model=open_dialog.value,
        on_v_model=open_dialog.set,
        fullscreen=True,
        hide_overlay=True,
        transition="dialog-bottom-transition",
        eager=True,
    ):
        with rv.Card():
            with rv.Toolbar(dark=True, color="primary", dense=True):
                rv.ToolbarTitle(children=["Basin Rivers — Dashboard"])
                rv.Spacer()
                rv.Btn(
                    icon=True,
                    dark=True,
                    children=[rv.Icon(children=["mdi-close"])],
                    on_click=lambda *_: open_dialog.set(False),
                )

            with rv.CardText(class_="pa-4"):
                _DashboardContent(state, theme_toggle)


@solara.component
def _DashboardContent(state, theme_toggle):
    with rv.Layout(column=True):
        with rv.Layout(class_="d-flex flex-wrap mb-2"):
            with rv.Flex(sm12=True, md5=True, class_="pa-2"):
                SettingsCard(state)
            with rv.Flex(sm12=True, md7=True, class_="pa-2"):
                OverallPie(state, theme_toggle)

        with rv.Layout(class_="d-flex flex-wrap mb-2"):
            with rv.Flex(sm12=True, md5=True, class_="pa-2"):
                CatchmentPie(state, theme_toggle)
            with rv.Flex(sm12=True, md7=True, class_="pa-2"):
                CatchmentBar(state, theme_toggle)

        if state.selected_var.value == "loss":
            with rv.Flex(xs12=True, class_="pa-2"):
                LossTrend(state, theme_toggle)
