"""Build ALOS PALSAR / PALSAR-2 yearly mosaic as an ``ee.Image``.

Ported from legacy ``component/scripts/kc_mosaic.py`` with the UI dependency
(``output.add_live_msg``) removed. All processing is server-side GEE; the
caller is expected to wrap invocations in a Solara ``use_task`` with
``prefer_threaded=False`` and to call ``gee_interface.get_map_id_async`` /
``add_ee_layer_async`` for rendering.
"""

from __future__ import annotations

import ee

from apps.alos_mosaics.params import (
    ALOS_FNF_COLLECTION,
    ALOS_SAR_COLLECTION,
    DEFAULT_SPECKLE_DICT,
    SPECKLE_NONE,
    SPECKLE_QUEGAN,
    SPECKLE_REFINED_LEE,
    VIS_PARAM_DB,
    VIS_PARAM_FNF,
    VIS_PARAM_POW,
    VIS_PARAM_RFDI,
    VIZ_FNF,
    VIZ_RFDI,
    VIZ_RGB,
    fnf_available,
)
from apps.alos_mosaics.scripts import _quegan, _refined_lee


def _psr_calibrate(image: ee.Image) -> ee.Image:
    """Convert DN to PSR backscatter (gamma naught)."""
    calibrated = ee.Image(10.0).pow(image.select(["HH", "HV"]).log10().multiply(2.0).subtract(8.3))
    return image.addBands(calibrated, None, True)


def _set_resample(image: ee.Image) -> ee.Image:
    return image.resample()


def _mask_ls(image: ee.Image) -> ee.Image:
    """Mask layover / shadow pixels (qa = 100 or 150)."""
    ls = image.select("qa").neq(100).bitwiseAnd(image.select("qa").neq(150))
    return image.updateMask(ls)


def _to_db(image: ee.Image) -> ee.Image:
    db_bands = ee.Image(10).multiply(image.select(["HH", "HV"]).log10()).rename(["HH", "HV"])
    return image.addBands(db_bands, None, True)


def build_alos_mosaic(
    region: ee.FeatureCollection,
    year: int,
    speckle_filter: str = SPECKLE_NONE,
    speckle_filter_dict: dict | None = None,
    ls_mask: bool = True,
    db: bool = True,
) -> ee.Image:
    """Build the ALOS mosaic for a given year and AOI.

    The returned image always carries the following bands:

    * ``HH``, ``HV`` — backscatter (power or dB depending on ``db``)
    * ``HHHV_ratio`` — HH / HV
    * ``RFDI`` — normalizedDifference(HH, HV)
    * ``HH_var``, ``HH_idm``, ``HH_diss`` — GLCM texture of HH
    * ``HV_var``, ``HV_idm``, ``HV_diss`` — GLCM texture of HV
    * ``qa``, ``date``, ``angle`` — original auxiliary bands
    * ``fnf_<year>`` — only when ``year <= 2017``

    Args:
        region: AOI as an ``ee.FeatureCollection``.
        year: Target year (one of ``ALOS_YEARS``).
        speckle_filter: One of ``SPECKLE_NONE``, ``SPECKLE_QUEGAN``,
            ``SPECKLE_REFINED_LEE``.
        speckle_filter_dict: Kernel parameters for the Quegan filter.
        ls_mask: Whether to apply the layover / shadow mask.
        db: Whether to convert HH / HV to dB.
    """
    opts = dict(DEFAULT_SPECKLE_DICT)
    if speckle_filter_dict:
        opts.update(speckle_filter_dict)

    collection = ee.ImageCollection(ALOS_SAR_COLLECTION).map(_psr_calibrate).map(_set_resample)

    if speckle_filter == SPECKLE_QUEGAN:
        collection = _quegan.apply(collection, opts)

    image = collection.filter(ee.Filter.date(f"{year}-01-01", f"{year}-12-31")).first()

    if speckle_filter == SPECKLE_REFINED_LEE:
        image = _refined_lee.apply(image)

    if ls_mask:
        image = _mask_ls(image)

    image = image.addBands(image.select("HH").divide(image.select("HV")).rename("HHHV_ratio"))
    image = image.addBands(image.normalizedDifference(["HH", "HV"]).rename("RFDI"))

    # GLCM texture (computed on power bands scaled to int16)
    image_100 = image.select(["HH", "HV"]).multiply(ee.Image(100)).toInt16()
    texture_hh = image_100.select("HH").glcmTexture(7)
    texture_hv = image_100.select("HV").glcmTexture(7)
    image = image.addBands(texture_hh.select("HH_var", "HH_idm", "HH_diss")).addBands(
        texture_hv.select("HV_var", "HV_idm", "HV_diss")
    )

    if db:
        image = _to_db(image)

    if fnf_available(year):
        fnf_image = (
            ee.ImageCollection(ALOS_FNF_COLLECTION)
            .filter(ee.Filter.date(f"{year}-01-01", f"{year}-12-31"))
            .first()
            .rename(f"fnf_{year}")
        )
        image = image.addBands(fnf_image)

    return image.clip(region)


# --- Band selection helpers --------------------------------------------------
RGB_BANDS = ["HH", "HV", "HHHV_ratio"]
TEXTURE_BANDS = ["HH_var", "HH_idm", "HH_diss", "HV_var", "HV_idm", "HV_diss"]
AUX_BANDS = ["angle", "date", "qa"]


def select_viz_bands(image: ee.Image, viz_layer: str, year: int, db: bool) -> ee.Image:
    """Select the bands to display for a given visualization mode."""
    if viz_layer == VIZ_RGB:
        return image.select(RGB_BANDS)
    if viz_layer == VIZ_RFDI:
        return image.select(["RFDI"])
    if viz_layer == VIZ_FNF:
        if not fnf_available(year):
            raise ValueError(f"FNF is not available for year {year}")
        return image.select([f"fnf_{year}"])
    raise ValueError(f"Unknown viz layer: {viz_layer!r}")


def viz_params_for(viz_layer: str, db: bool) -> dict:
    """Return the visualization params for a given viz mode."""
    if viz_layer == VIZ_RGB:
        return dict(VIS_PARAM_DB if db else VIS_PARAM_POW)
    if viz_layer == VIZ_RFDI:
        return dict(VIS_PARAM_RFDI)
    if viz_layer == VIZ_FNF:
        return dict(VIS_PARAM_FNF)
    raise ValueError(f"Unknown viz layer: {viz_layer!r}")


def select_export_bands(
    image: ee.Image,
    year: int,
    backscatter: bool = True,
    rfdi: bool = True,
    texture: bool = False,
    aux: bool = False,
) -> ee.Image | None:
    """Build the export image from the requested band toggles.

    Returns ``None`` when no bands are requested (caller should skip the
    export entirely).
    """
    dataset: ee.Image | None = None

    def _add(bands: list[str]) -> None:
        nonlocal dataset
        if dataset is None:
            dataset = image.select(bands)
        else:
            dataset = dataset.addBands(image.select(bands))

    if backscatter:
        _add(RGB_BANDS)
    if rfdi:
        _add(["RFDI"])
    if texture:
        _add(TEXTURE_BANDS)
    if aux:
        _add(AUX_BANDS)

    return dataset


def select_fnf_band(image: ee.Image, year: int) -> ee.Image | None:
    """Return the FNF band image for the given year, if available."""
    if not fnf_available(year):
        return None
    return image.select(f"fnf_{year}")
