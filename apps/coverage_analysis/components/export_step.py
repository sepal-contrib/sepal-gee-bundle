"""Export step using pysepal ExportLauncher."""

from __future__ import annotations

import logging

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.export import (
    ExportLauncher,
    ExportSource,
    ResolvedExport,
)

from apps.coverage_analysis.params import STATS_ITEMS, TEMP_ITEMS
from apps.coverage_analysis.scripts import build_asset_name, build_export_image

logger = logging.getLogger("sepal_gee_bundle.coverage_analysis")


@solara.component
def ExportStep(state, gee_interface):
    """Export the current analysis as an EE asset, to Drive, or to SEPAL."""
    sources: tuple[ExportSource, ...] = ()
    if state.collection.value is not None and state.aoi.value is not None:
        coll = state.collection.value
        aoi_obj = state.aoi.value
        aoi_fc = aoi_obj.feature_collection
        start = state.start_date.value
        end = state.end_date.value
        stats_sel = list(state.stats.value)
        temps_sel = list(state.temps.value)

        asset_name = build_asset_name(
            aoi_name=getattr(aoi_obj, "name", "aoi"),
            start=start,
            end=end,
            sensors=state.sensors.value,
            sr=bool(state.surface_reflectance.value),
        )

        def _resolve(
            coll=coll,
            aoi_fc=aoi_fc,
            stats_sel=stats_sel,
            temps_sel=temps_sel,
            start=start,
            end=end,
            asset_name=asset_name,
        ) -> ResolvedExport:
            image = build_export_image(
                coll=coll,
                stats=stats_sel,
                temps=temps_sel,
                start=start,
                end=end,
                aoi=aoi_fc,
            )
            if image is None:
                raise ValueError("Select at least one stat and one temporal option.")
            return ResolvedExport(
                ee_object=image,
                default_name=asset_name,
                region=aoi_fc.geometry(),
                default_scale=30,
                gee_folder="coverage_analysis",
                drive_folder="coverage_analysis_exports",
                sepal_folder="coverage_analysis",
                max_pixels=1e13,
            )

        sources = (
            ExportSource(
                id="coverage_composite",
                label="Coverage / NDVI composite",
                kind="image",
                resolve=_resolve,
            ),
        )

    with solara.Column():
        rv.Select(
            v_model=state.stats.value,
            on_v_model=state.stats.set,
            items=STATS_ITEMS,
            label="Statistics to export",
            multiple=True,
            small_chips=True,
            deletable_chips=True,
            dense=True,
            outlined=True,
        )
        rv.Select(
            v_model=state.temps.value,
            on_v_model=state.temps.set,
            items=TEMP_ITEMS,
            label="Temporal aggregation",
            multiple=True,
            small_chips=True,
            deletable_chips=True,
            dense=True,
            outlined=True,
        )
        ExportLauncher(
            sources=sources,
            label="Export results",
            button_text=True,
            small=True,
            block=True,
            gee_interface=gee_interface,
        )

        if state.collection.value is None:
            solara.Text("Build the collection first to enable export.")
