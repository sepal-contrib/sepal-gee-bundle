"""Date ranges and algorithm-parameter step for FCDM."""

import reacton.ipyvuetify as rv
import solara

from apps.fcdm.params import (
    MAX_CLEANING_OFFSET,
    MAX_FILTER_RADIUS,
    MAX_KERNEL_RADIUS,
    MIN_FILTER_RADIUS,
)


@solara.component
def ParamsStep(state):
    """Reference / analysis date pickers and DDR / kernel parameters."""
    with solara.Column():
        solara.Text("Reference period (baseline)", style={"font-weight": "bold"})
        rv.TextField(
            v_model=state.reference_start.value,
            on_v_model=state.reference_start.set,
            label="Start date (YYYY-MM-DD)",
            placeholder="2015-01-01",
            dense=True,
            outlined=True,
        )
        rv.TextField(
            v_model=state.reference_end.value,
            on_v_model=state.reference_end.set,
            label="End date (YYYY-MM-DD)",
            placeholder="2015-12-31",
            dense=True,
            outlined=True,
        )

        solara.Text("Analysis period", style={"font-weight": "bold"}, classes=["mt-3"])
        rv.TextField(
            v_model=state.analysis_start.value,
            on_v_model=state.analysis_start.set,
            label="Start date (YYYY-MM-DD)",
            placeholder="2020-01-01",
            dense=True,
            outlined=True,
        )
        rv.TextField(
            v_model=state.analysis_end.value,
            on_v_model=state.analysis_end.set,
            label="End date (YYYY-MM-DD)",
            placeholder="2020-12-31",
            dense=True,
            outlined=True,
        )

        solara.Text("Cloud mask", style={"font-weight": "bold"}, classes=["mt-3"])
        rv.Slider(
            v_model=state.cloud_buffer.value,
            on_v_model=lambda v: state.cloud_buffer.set(int(v)),
            label="Cloud buffer (m)",
            min=0,
            max=2000,
            step=50,
            thumb_label="always",
        )

        solara.Text("Adjustment kernel", style={"font-weight": "bold"}, classes=["mt-3"])
        rv.Slider(
            v_model=state.kernel_radius.value,
            on_v_model=lambda v: state.kernel_radius.set(int(v)),
            label="Kernel radius (m)",
            min=30,
            max=MAX_KERNEL_RADIUS,
            step=10,
            thumb_label="always",
        )

        solara.Text("DDR filter", style={"font-weight": "bold"}, classes=["mt-3"])
        rv.Slider(
            v_model=state.filter_threshold.value,
            on_v_model=lambda v: state.filter_threshold.set(float(v)),
            label="Disturbance threshold",
            min=0.0,
            max=0.2,
            step=0.005,
            thumb_label="always",
        )
        rv.Slider(
            v_model=state.filter_radius.value,
            on_v_model=lambda v: state.filter_radius.set(int(v)),
            label="DDR kernel radius (m)",
            min=MIN_FILTER_RADIUS,
            max=MAX_FILTER_RADIUS,
            step=10,
            thumb_label="always",
        )
        rv.Slider(
            v_model=state.cleaning_offset.value,
            on_v_model=lambda v: state.cleaning_offset.set(int(v)),
            label="Minimum events per kernel",
            min=1,
            max=MAX_CLEANING_OFFSET,
            thumb_label="always",
        )
