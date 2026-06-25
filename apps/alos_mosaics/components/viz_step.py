"""Visualization step for the ALOS mosaics app.

Builds the ALOS mosaic server-side (GEE) from the selected year / speckle
filter / LS mask / dB toggles, then picks a display layer (RGB backscatter /
RFDI / FNF) and adds it to the map. The mosaic build is a purely lazy GEE
graph operation, so it is combined with the layer rendering into a single
button.

The FNF radio option is disabled for years > 2017.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent, use_task_button
from pysepal.solara.notifications import use_notifications

from apps._widgets import MarkdownNewTab
from apps.alos_mosaics.params import (
    ALOS_YEARS,
    SPECKLE_FILTERS,
    VIZ_FNF,
    VIZ_LAYERS,
    VIZ_RFDI,
    VIZ_RGB,
    fnf_available,
    fnf_legend,
    rfdi_legend,
    rgb_legend,
)
from apps.alos_mosaics.scripts import (
    build_alos_mosaic,
    select_viz_bands,
    viz_params_for,
)

logger = logging.getLogger("sepal_gee_bundle.alos_mosaics")

ALOS_LAYER_KEY = "alos_mosaic"

SAR_RGB_INTERPRETATION = """\
The map shows a false-colour composite of three SAR bands, one per RGB channel.

## Channel mapping

| Channel | Band | Sensitive to |
|---------|------|--------------|
| **Red** | HH (co-polarized) | hard surfaces, edges, water / land boundaries |
| **Green** | HV (cross-polarized) | volume scattering (vegetation canopy) |
| **Blue** | HH/HV ratio | differences in scattering mechanism |

## Typical appearances

| What you see on the map | What it *tends to* indicate |
|---|---|
| Bright green / yellow-green | dense vegetation, forest |
| Olive / dull green | sparse vegetation, crops |
| Pink / magenta | bare soil, dry surfaces |
| Bright pink / white-pink | urban, built-up (corner reflectors) |
| Dark blue / cyan tinges | flooded vegetation, wetlands |
| Near-black | calm water, very smooth surfaces |

These are **tendencies**, not classes. The exact colors depend on soil
moisture, terrain roughness, and the acquisition geometry of the ALOS
PALSAR mosaic for the selected year, so two pixels with the same colour
can belong to different land covers.

## Reference

- [JAXA PALSAR mosaics — official portal and interpretation guide](https://www.eorc.jaxa.jp/ALOS/en/dataset/fnf_e.htm)
"""


@dataclass(frozen=True, slots=True)
class VizRequest:
    aoi_fc: object  # ee.FeatureCollection
    year: int
    speckle_filter: str
    ls_mask: bool
    db: bool
    viz_layer: str


@solara.component
def VizStep(state, sepal_map, gee_interface, legend_data=None, legend_visible=None):
    notifications = use_notifications()
    cancel_reason = solara.use_ref(None)
    rgb_info_open = solara.use_reactive(False)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def viz_task(request: VizRequest):
        with notifications.track("Rendering ALOS layer", total_steps=3) as task:
            task.step("Building ALOS mosaic")
            image = build_alos_mosaic(
                region=request.aoi_fc,
                year=request.year,
                speckle_filter=request.speckle_filter,
                ls_mask=request.ls_mask,
                db=request.db,
            )

            task.step("Selecting bands")
            viz_image = select_viz_bands(image, request.viz_layer, request.year, request.db)
            vis = viz_params_for(request.viz_layer, request.db)

            sepal_map.remove_layer(ALOS_LAYER_KEY, none_ok=True)

            task.step("Loading tiles on map")
            await sepal_map.add_ee_layer_async(
                viz_image,
                vis,
                ALOS_LAYER_KEY,
                autocenter=True,
            )
        logger.info(
            "ALOS layer rendered: year=%s filter=%s ls_mask=%s db=%s viz=%s",
            request.year,
            request.speckle_filter,
            request.ls_mask,
            request.db,
            request.viz_layer,
        )
        return image

    def _sync_viz():
        state.loading.value = viz_task.pending
        if viz_task.pending or viz_task.cancelled:
            return
        if viz_task.error:
            notifications.error(f"Visualization failed: {viz_task.exception}")
            return
        if viz_task.finished and viz_task.value is not None:
            state.result_image.value = viz_task.value
            if legend_data is not None:
                if state.viz_layer.value == VIZ_FNF:
                    legend_data.set(asdict(fnf_legend()))
                elif state.viz_layer.value == VIZ_RFDI:
                    legend_data.set(asdict(rfdi_legend()))
                else:
                    legend_data.set(asdict(rgb_legend(state.db.value)))
            if legend_visible is not None:
                legend_visible.set(True)
            notifications.success("Layer added to map.")

    solara.use_effect(
        _sync_viz,
        [viz_task.pending, viz_task.cancelled, viz_task.finished, viz_task.error],
    )

    def _start_viz():
        if state.aoi.value is None:
            notifications.warning("Please select an Area of Interest first.")
            return
        if state.year.value is None:
            notifications.warning("Please select a year.")
            return
        if state.viz_layer.value == VIZ_FNF and not fnf_available(state.year.value):
            notifications.warning("FNF data is only available up to 2017. Pick a different layer.")
            return
        cancel_reason.current = None
        state.loading.value = True
        state.result_image.value = None
        if legend_visible is not None:
            legend_visible.set(False)
        viz_task(
            VizRequest(
                aoi_fc=state.aoi.value.feature_collection,
                year=int(state.year.value),
                speckle_filter=state.speckle_filter.value,
                ls_mask=bool(state.ls_mask.value),
                db=bool(state.db.value),
                viz_layer=state.viz_layer.value,
            )
        )

    btn_props = use_task_button(viz_task, on_start=_start_viz, cancel_reason_ref=cancel_reason)

    year_items = [{"text": str(y), "value": y} for y in sorted(ALOS_YEARS, reverse=True)]
    filter_items = [{"text": f["text"], "value": f["value"]} for f in SPECKLE_FILTERS]

    # Build radio items, disabling FNF if the current year is > 2017
    fnf_ok = fnf_available(state.year.value)
    viz_items = []
    for item in VIZ_LAYERS:
        disabled = item["value"] == VIZ_FNF and not fnf_ok
        viz_items.append({"label": item["label"], "value": item["value"], "disabled": disabled})

    with solara.Column():
        rv.Select(
            v_model=state.year.value,
            on_v_model=lambda v: state.year.set(int(v) if v is not None else None),
            items=year_items,
            label="Year",
            class_="mt-2",
        )

        rv.Select(
            v_model=state.speckle_filter.value,
            on_v_model=state.speckle_filter.set,
            items=filter_items,
            label="Speckle filter",
        )

        rv.Switch(
            v_model=state.ls_mask.value,
            on_v_model=state.ls_mask.set,
            label="Mask layover / shadow pixels",
            class_="ml-2",
        )

        rv.Switch(
            v_model=state.db.value,
            on_v_model=state.db.set,
            label="Convert backscatter to dB",
            class_="ml-2",
        )

        with rv.RadioGroup(
            v_model=state.viz_layer.value,
            on_v_model=state.viz_layer.set,
            class_="mt-2",
        ):
            for item in viz_items:
                rv.Radio(
                    label=item["label"],
                    value=item["value"],
                    disabled=item["disabled"],
                )

        if state.viz_layer.value == VIZ_RGB:
            rv.Btn(
                text=True,
                small=True,
                class_="mt-n2 mb-2 align-self-start text-none",
                on_click=lambda *_: rgb_info_open.set(True),
                children=["How to read this image"],
            )

        if not fnf_ok and state.viz_layer.value == VIZ_FNF:
            rv.Alert(
                type="warning",
                dense=True,
                text=True,
                children=[f"FNF not available for {state.year.value}. Pick RGB or RFDI."],
            )

        TaskButtonComponent(
            label="Add layer to map",
            **btn_props,
            external_busy=state.aoi.value is None,
            small=True,
            block=True,
        )

    with rv.Dialog(
        v_model=rgb_info_open.value,
        on_v_model=rgb_info_open.set,
        max_width="720",
        scrollable=True,
        eager=True,
    ):
        with rv.Card():
            with rv.CardTitle(class_="d-flex align-center py-3 px-4"):
                rv.Icon(
                    color="primary",
                    class_="mr-2",
                    children=["mdi-image-filter-hdr"],
                )
                rv.Html(
                    tag="span",
                    class_="text-h6",
                    children=["How to read the SAR RGB composite"],
                )
                rv.Spacer()
                solara.Button(
                    icon_name="mdi-close",
                    icon=True,
                    on_click=lambda *_: rgb_info_open.set(False),
                )
            rv.Divider()
            with rv.CardText(class_="pa-4"):
                MarkdownNewTab(SAR_RGB_INTERPRETATION)
