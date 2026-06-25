"""Export step for the TMF app — delegates to pysepal ExportLauncher."""

import logging

import solara
from pysepal.solara.components.export import (
    ExportLauncher,
    ExportSource,
    ResolvedExport,
)

from apps.tmf_sepal.params import asset_basename, export_vis_params_for

logger = logging.getLogger("sepal_gee_bundle.tmf_sepal")


@solara.component
def ExportStep(state, gee_interface):
    """Scale input + ExportLauncher for the visualized TMF image."""
    export_sources: tuple[ExportSource, ...] = ()

    if state.result_image.value is not None and state.aoi.value is not None:
        image = state.result_image.value
        aoi_fc = state.aoi.value.feature_collection
        aoi_name = getattr(state.aoi.value, "name", None) or "aoi"
        tmf_type = state.tmf_type.value
        year_start = state.year_start.value
        year_end = state.year_end.value
        default_name = asset_basename(aoi_name, tmf_type, year_start, year_end)
        export_vis = export_vis_params_for(tmf_type, year_start, year_end)

        export_sources = (
            ExportSource(
                id="tmf_image",
                label="JRC TMF image",
                kind="image",
                resolve=lambda img=image, fc=aoi_fc, name=default_name: ResolvedExport(
                    ee_object=img,
                    default_name=name,
                    region=fc.geometry(),
                    default_scale=30,
                    gee_folder="tmf",
                    drive_folder="tmf_exports",
                    sepal_folder="tmf",
                    max_pixels=1e13,
                    vis_params=export_vis,
                ),
            ),
            ExportSource(
                id="tmf_aoi",
                label="AOI boundary",
                kind="table",
                resolve=lambda fc=aoi_fc, name=default_name: ResolvedExport(
                    ee_object=fc,
                    default_name=f"{name}_aoi",
                    gee_folder="tmf",
                    drive_folder="tmf_exports",
                    sepal_folder="tmf",
                ),
            ),
        )

    with solara.Column():
        ExportLauncher(
            sources=export_sources,
            label="Export layers",
            icon="",
            button_text=True,
            small=True,
            block=True,
            gee_interface=gee_interface,
        )
