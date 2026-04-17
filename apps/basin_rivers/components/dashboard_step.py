"""Dashboard step: settings card + four ipecharts charts."""

import reacton.ipyvuetify as rv
import solara

from .dashboard import CatchmentBar, CatchmentPie, LossTrend, OverallPie, SettingsCard


@solara.component
def DashboardStep(state, theme_toggle):
    df = state.zonal_df.value
    if df is None or df.empty:
        solara.Text("Run delineation and calculate statistics to see results.")
        return

    with rv.Layout(column=True):
        with rv.Layout(class_="d-flex flex-wrap mb-2"):
            with rv.Flex(sm12=True, md5=True):
                SettingsCard(state)
            with rv.Flex(sm12=True, md7=True):
                OverallPie(state, theme_toggle)

        with rv.Layout(class_="d-flex flex-wrap mb-2"):
            with rv.Flex(sm12=True, md5=True):
                CatchmentPie(state, theme_toggle)
            with rv.Flex(sm12=True, md7=True):
                CatchmentBar(state, theme_toggle)

        if state.selected_var.value == "loss":
            with rv.Flex(xs12=True):
                LossTrend(state, theme_toggle)
