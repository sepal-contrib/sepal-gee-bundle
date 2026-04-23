"""Export step for the ALOS mosaics app — delegates to pysepal ExportLauncher."""

from __future__ import annotations

import logging

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.export import (
    ExportLauncher,
    ExportSource,
    ResolvedExport,
)

from apps.alos_mosaics.params import asset_name, fnf_available
from apps.alos_mosaics.scripts import select_export_bands
from apps.alos_mosaics.scripts.kc_mosaic import select_fnf_band

logger = logging.getLogger("sepal_gee_bundle.alos_mosaics")


@solara.component
def ExportStep(state, gee_interface):
    """Band-selection switches + scale input + ExportLauncher."""
    export_sources: tuple[ExportSource, ...] = ()

    image = state.result_image.value
    aoi = state.aoi.value
    if image is not None and aoi is not None:
        aoi_fc = aoi.feature_collection
        aoi_name = getattr(aoi, "name", None) or "aoi"
        year = int(state.year.value)
        db = bool(state.db.value)
        speckle = state.speckle_filter.value
        ls_mask = bool(state.ls_mask.value)

        backscatter = bool(state.export_backscatter.value)
        rfdi = bool(state.export_rfdi.value)
        texture = bool(state.export_texture.value)
        aux = bool(state.export_aux.value)

        mosaic_image = select_export_bands(
            image,
            year=year,
            backscatter=backscatter,
            rfdi=rfdi,
            texture=texture,
            aux=aux,
        )

        sources: list[ExportSource] = []

        if mosaic_image is not None:
            default_name = asset_name(
                aoi_name=aoi_name,
                year=year,
                speckle_filter=speckle,
                rfdi=rfdi,
                ls_mask=ls_mask,
                db=db,
                texture=texture,
                aux=aux,
            )
            sources.append(
                ExportSource(
                    id="alos_mosaic",
                    label="ALOS mosaic image",
                    kind="image",
                    resolve=lambda img=mosaic_image, fc=aoi_fc, name=default_name: ResolvedExport(
                        ee_object=img,
                        default_name=name,
                        region=fc.geometry(),
                        default_scale=25,
                        gee_folder="alos_mosaics",
                        drive_folder="alos_mosaics_exports",
                        sepal_folder="alos_mosaics",
                        max_pixels=1e13,
                    ),
                )
            )

        if state.export_fnf.value and fnf_available(year):
            fnf_image = select_fnf_band(image, year)
            if fnf_image is not None:
                fnf_name = asset_name(
                    aoi_name=aoi_name,
                    year=year,
                    speckle_filter=speckle,
                    rfdi=False,
                    ls_mask=False,
                    db=False,
                    texture=False,
                    aux=False,
                    fnf=True,
                )
                sources.append(
                    ExportSource(
                        id="alos_fnf",
                        label="ALOS Forest / Non-Forest",
                        kind="image",
                        resolve=lambda img=fnf_image, fc=aoi_fc, name=fnf_name: ResolvedExport(
                            ee_object=img,
                            default_name=name,
                            region=fc.geometry(),
                            default_scale=25,
                            gee_folder="alos_mosaics",
                            drive_folder="alos_mosaics_exports",
                            sepal_folder="alos_mosaics",
                            max_pixels=1e13,
                        ),
                    )
                )

        sources.append(
            ExportSource(
                id="alos_aoi",
                label="AOI boundary",
                kind="table",
                resolve=lambda fc=aoi_fc, name=asset_name(aoi_name=aoi_name, year=year): (
                    ResolvedExport(
                        ee_object=fc,
                        default_name=f"{name}_aoi",
                        gee_folder="alos_mosaics",
                        drive_folder="alos_mosaics_exports",
                        sepal_folder="alos_mosaics",
                    )
                ),
            )
        )

        export_sources = tuple(sources)

    fnf_ok = fnf_available(int(state.year.value)) if state.year.value else False

    with solara.Column():
        rv.Switch(
            v_model=state.export_backscatter.value,
            on_v_model=state.export_backscatter.set,
            label="Backscatter (HH, HV, HH/HV ratio)",
            class_="ml-2",
        )
        rv.Switch(
            v_model=state.export_rfdi.value,
            on_v_model=state.export_rfdi.set,
            label="RFDI",
            class_="ml-2",
        )
        rv.Switch(
            v_model=state.export_texture.value,
            on_v_model=state.export_texture.set,
            label="GLCM texture bands",
            class_="ml-2",
        )
        rv.Switch(
            v_model=state.export_aux.value,
            on_v_model=state.export_aux.set,
            label="Auxiliary bands (angle, date, qa)",
            class_="ml-2",
        )
        rv.Switch(
            v_model=state.export_fnf.value,
            on_v_model=state.export_fnf.set,
            label="Forest / Non-Forest (year <= 2017)",
            disabled=not fnf_ok,
            class_="ml-2",
        )

        ExportLauncher(
            sources=export_sources,
            label="Export results",
            button_text=True,
            small=True,
            block=True,
            gee_interface=gee_interface,
        )
