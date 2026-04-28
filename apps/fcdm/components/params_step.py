"""Date ranges and algorithm-parameter step for FCDM."""

from datetime import date

import reacton.ipyvuetify as rv
import solara
import solara.lab

from apps.fcdm.params import (
    MAX_CLEANING_OFFSET,
    MAX_FILTER_RADIUS,
    MAX_KERNEL_RADIUS,
    MIN_FILTER_RADIUS,
)

# Lower bound covers Landsat-5; upper bound is "today" so users can pick a
# very recent end date right after a satellite acquisition.
_DATE_MIN = "1984-01-01"


def _str_to_date(s: str) -> date | None:
    if not s or len(s) < 10:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _date_to_str(d: date | None) -> str:
    return d.isoformat() if d else ""


def _sepal_slider(reactive, label, *, min, max, step=1, cast=int, fmt=str, suffix=""):
    """Slim slider mimicking SEPAL's UI: label, slider, editable numeric field."""
    value = reactive.value

    def _set(v, r=reactive, c=cast, lo=min, hi=max):
        try:
            n = c(float(v))
        except (TypeError, ValueError):
            return
        if n < lo or n > hi:
            return
        r.set(n)

    with rv.Html(
        tag="div",
        class_="mt-2 mb-1",
        style_="display: flex; align-items: center; gap: 12px;",
    ):
        rv.Html(
            tag="span",
            style_="flex: 0 0 auto; min-width: 140px; font-size: 0.8rem; opacity: 0.7;",
            children=[label],
        )
        rv.Slider(
            v_model=value,
            on_v_model=_set,
            min=min,
            max=max,
            step=step,
            hide_details=True,
            dense=True,
            thumb_label=False,
            class_="pt-0 mt-0",
            style_="flex: 1 1 auto;",
        )
        rv.TextField(
            v_model=fmt(value),
            on_v_model=_set,
            type="number",
            suffix=suffix.strip() or None,
            hide_details=True,
            dense=True,
            single_line=True,
            style_="flex: 0 0 auto; max-width: 70px; font-size: 0.75rem;",
            class_="pt-0 mt-0",
        )


@solara.component
def ParamsStep(state):
    """Reference / analysis date pickers and DDR / kernel parameters."""
    today_iso = date.today().isoformat()

    def _date_field(reactive, label):
        return solara.lab.InputDate(
            value=_str_to_date(reactive.value),
            on_value=lambda d, r=reactive: r.set(_date_to_str(d)),
            label=label,
            optional=True,
            min_date=_DATE_MIN,
            max_date=today_iso,
            date_format="%Y-%m-%d",
            dense=True,
            classes=["mb-2"],
        )

    with solara.Column():
        solara.Text("Reference period (baseline)", style={"font-weight": "bold"})
        _date_field(state.reference_start, "Start date")
        _date_field(state.reference_end, "End date")

        solara.Text("Analysis period", style={"font-weight": "bold"}, classes=["mt-3"])
        _date_field(state.analysis_start, "Start date")
        _date_field(state.analysis_end, "End date")

        solara.Text("Cloud mask", style={"font-weight": "bold"}, classes=["mt-3"])
        _sepal_slider(
            state.cloud_buffer,
            "Cloud buffer",
            min=0,
            max=2000,
            step=50,
            suffix=" m",
        )

        solara.Text("Adjustment kernel", style={"font-weight": "bold"}, classes=["mt-3"])
        _sepal_slider(
            state.kernel_radius,
            "Kernel radius",
            min=30,
            max=MAX_KERNEL_RADIUS,
            step=10,
            suffix=" m",
        )

        solara.Text("DDR filter", style={"font-weight": "bold"}, classes=["mt-3"])
        _sepal_slider(
            state.filter_threshold,
            "Disturbance threshold",
            min=0.0,
            max=0.2,
            step=0.005,
            cast=float,
            fmt=lambda v: f"{v:.3f}",
        )
        _sepal_slider(
            state.filter_radius,
            "DDR kernel radius",
            min=MIN_FILTER_RADIUS,
            max=MAX_FILTER_RADIUS,
            step=10,
            suffix=" m",
        )
        _sepal_slider(
            state.cleaning_offset,
            "Min events / kernel",
            min=1,
            max=MAX_CLEANING_OFFSET,
        )
