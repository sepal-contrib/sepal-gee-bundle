"""Results display and export step for GFC app."""

import logging

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.export import (
    ExportLauncher,
    ExportSource,
    ResolvedExport,
)

from apps._commons.gfc import GFC_VIS_PARAMS
from apps.gfc.params import GFC_MAX_YEAR

from .dashboard_step import DashboardStep

logger = logging.getLogger("sepal_gee_bundle.gfc")


@solara.component
def ResultsStep(state, sepal_map, gee_interface, legend_visible=None):
    """Dashboard launcher, stats table, and export controls."""
    stats_rows = state.stats_rows.value

    # --- Export sources ---
    export_sources: tuple[ExportSource, ...] = ()
    if state.result_image.value is not None and state.aoi.value is not None:
        result_image = state.result_image.value
        aoi_fc = state.aoi.value.feature_collection
        treecover = state.treecover.value
        year_start = state.year_start.value
        year_end = state.year_end.value
        default_name = f"gfc_{treecover}_{year_start}_{year_end}"

        export_sources = (
            ExportSource(
                id="gfc_classified",
                label="GFC classified image",
                kind="image",
                resolve=lambda img=result_image, fc=aoi_fc, name=default_name: ResolvedExport(
                    ee_object=img,
                    default_name=name,
                    region=fc.geometry(),
                    default_scale=30,
                    gee_folder="gfc",
                    drive_folder="gfc_exports",
                    sepal_folder="gfc",
                    max_pixels=1e13,
                    vis_params=GFC_VIS_PARAMS,
                ),
            ),
            ExportSource(
                id="gfc_aoi",
                label="AOI boundary",
                kind="table",
                resolve=lambda fc=aoi_fc, name=default_name: ResolvedExport(
                    ee_object=fc,
                    default_name=f"{name}_aoi",
                    gee_folder="gfc",
                    drive_folder="gfc_exports",
                    sepal_folder="gfc",
                ),
            ),
        )

    with solara.Column():
        DashboardStep(
            state,
            gee_interface=gee_interface,
            legend_visible=legend_visible,
            sepal_map=sepal_map,
        )

        if stats_rows:
            _StatsTable(stats_rows)

        ExportLauncher(
            sources=export_sources,
            label="Export layers",
            icon="mdi-cloud-download",
            button_text=True,
            small=True,
            block=True,
            gee_interface=gee_interface,
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
