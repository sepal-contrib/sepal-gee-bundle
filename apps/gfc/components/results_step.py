"""Results display and export step for GFC app."""

import asyncio
import logging

import reacton.ipyvuetify as rv
import solara

from apps.gfc.params import GFC_MAX_YEAR
from apps.gfc.scripts import compute_area_stats, parse_area_stats

logger = logging.getLogger("sepal_gee_bundle.gfc")


@solara.component
def ResultsStep(state, sepal_map, gee_interface):
    """Area statistics, loss chart, and export controls."""
    stats_rows, set_stats_rows = solara.use_state([])
    error, set_error = solara.use_state("")
    export_status, set_export_status = solara.use_state("")

    # Trigger counters — incrementing these triggers the corresponding use_task
    compute_trigger = solara.use_reactive(0)
    export_trigger = solara.use_reactive(0)

    @solara.lab.use_task(
        dependencies=[compute_trigger.value], raise_error=False, prefer_threaded=True
    )
    async def compute_task():
        if compute_trigger.value == 0:
            return
        set_error("")
        aoi = state.aoi.value
        result_image = state.result_image.value

        if aoi is None or result_image is None:
            set_error("Run visualization first.")
            return

        raw = await asyncio.to_thread(
            lambda: gee_interface.get_info(
                compute_area_stats(result_image, aoi.feature_collection)
            ),
        )
        rows = parse_area_stats(raw)
        set_stats_rows(rows)
        logger.info("Area statistics computed: %d classes", len(rows))

    @solara.lab.use_task(
        dependencies=[export_trigger.value], raise_error=False, prefer_threaded=True
    )
    async def export_task():
        if export_trigger.value == 0:
            return
        set_export_status("Exporting to asset...")
        aoi = state.aoi.value
        result_image = state.result_image.value
        t = state.treecover.value
        ys = state.year_start.value
        ye = state.year_end.value
        description = f"gfc_{t}_{ys}_{ye}"

        folder = await gee_interface.get_folder_async()
        asset_id = f"{folder}/{description}"

        await gee_interface.export_image_to_asset_async(
            image=result_image,
            asset_id=asset_id,
            description=description,
            scale=30,
            region=aoi.feature_collection.geometry(),
            max_pixels=1e13,
        )
        set_export_status(f"Export task started: {asset_id}")
        logger.info("Export to asset started: %s", asset_id)

    with solara.Column():
        solara.Button(
            "Compute area statistics",
            icon_name="mdi-chart-bar",
            on_click=lambda *_: compute_trigger.set(compute_trigger.value + 1),
            loading=compute_task.pending,
            disabled=compute_task.pending or state.result_image.value is None,
            color="primary",
        )

        if compute_task.error:
            rv.Alert(type="error", text=True, children=[str(compute_task.error)])

        if error:
            rv.Alert(type="error", text=True, children=[error])

        if stats_rows:
            _StatsTable(stats_rows)
            _LossChart(stats_rows)

        if export_status:
            rv.Alert(type="info", text=True, children=[export_status])

        if export_task.error:
            rv.Alert(type="error", text=True, children=[str(export_task.error)])

        solara.Button(
            "Export to GEE Asset",
            icon_name="mdi-cloud-upload",
            on_click=lambda *_: export_trigger.set(export_trigger.value + 1),
            loading=export_task.pending,
            disabled=export_task.pending or state.result_image.value is None,
        )


@solara.component
def _StatsTable(rows: list):
    """Display area statistics as a data table."""
    loss_rows = [r for r in rows if r["code"] <= GFC_MAX_YEAR]
    summary_rows = [r for r in rows if r["code"] > GFC_MAX_YEAR]

    total_loss = sum(r["area_ha"] for r in loss_rows)
    all_rows = [
        *summary_rows,
        {"code": 60, "label": "total loss", "area_ha": round(total_loss, 2)},
    ]

    headers = [
        {"text": "Class", "value": "label", "align": "start"},
        {"text": "Area (ha)", "value": "area_ha"},
    ]
    items = [{"label": r["label"], "area_ha": f"{r['area_ha']:,.0f}"} for r in all_rows]

    rv.DataTable(
        headers=headers,
        items=items,
        dense=True,
        disable_filtering=True,
        disable_sort=True,
        hide_default_footer=True,
        class_="mt-2",
    )


@solara.component
def _LossChart(rows: list):
    """Simple text-based loss-by-year summary."""
    loss_rows = [r for r in rows if 1 <= r["code"] <= GFC_MAX_YEAR]
    if not loss_rows:
        return

    with rv.Card(class_="mt-2", flat=True):
        with rv.CardTitle():
            solara.Text("Loss by year")
        with rv.CardText():
            for r in loss_rows:
                year = 2000 + r["code"]
                area = r["area_ha"]
                solara.Text(f"{year}: {area:,.0f} ha")
