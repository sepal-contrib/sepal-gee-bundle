"""NBR / Delta-rNBR pipeline for FCDM.

Pure GEE functions — adjustment kernel, capping, DDR filter, and a top-level
`run_fcdm(...)` that wires everything together for one AOI + two date ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

import ee

from apps.fcdm.params import SENSORS
from apps.fcdm.scripts.collection import build_collection
from apps.fcdm.scripts.forest_mask import get_forest_mask


# ---------------------------------------------------------------------------
# Per-scene NBR
# ---------------------------------------------------------------------------
def compute_nbr(image: ee.Image, sensor: str) -> ee.Image:
    """Compute NBR = (NIR - SWIR2) / (NIR + SWIR2) plus a `yearday` band."""
    bands = SENSORS[sensor]["bands"]
    nir = image.select(bands["nir"])
    swir2 = image.select(bands["swir2"])

    doy = ee.Algorithms.Date(ee.Number(image.get("system:time_start")))
    yearday = ee.Number(doy.get("year")).add(ee.Number.parse(doy.format("D")).divide(365))
    yearday = ee.Image.constant(yearday).float().rename("yearday")
    nbr = nir.subtract(swir2).divide(nir.add(swir2)).rename("NBR")
    return nbr.addBands(yearday)


def adjustment_kernel(image: ee.Image, kernel_size: float) -> ee.Image:
    """Self-reference each NBR scene via focal-median subtraction."""
    nbr = image.select("NBR")
    yearday = image.select("yearday")
    return nbr.subtract(nbr.focal_median(kernel_size, "circle", "meters")).addBands(yearday)


def capping(image: ee.Image) -> ee.Image:
    """Clamp NBR to [-1, 0] then invert sign."""
    nbr = image.select("NBR")
    yearday = image.select("yearday")
    return nbr.where(nbr.gt(0), 0).where(nbr.lt(-1), -1).multiply(-1).addBands(yearday)


def ddr_filter(
    nbr_diff: ee.Image,
    threshold: float,
    radius: float,
    nb_disturbances: int,
) -> ee.Image:
    """Disturbing-density-related filter — mask pixels without enough events."""
    nbr_diff_threshold = nbr_diff.where(nbr_diff.lt(threshold), 0).And(
        nbr_diff.where(nbr_diff.gte(threshold), 1)
    )
    # keep the variable to mirror legacy behaviour (unused but clarifies intent)
    _ = nbr_diff_threshold

    nbr_nb_events = nbr_diff.reduceNeighborhood(
        reducer=ee.Reducer.sum().unweighted(),
        kernel=ee.Kernel.circle(radius, "meters"),
    )
    nbr_nb_events_mask = (
        nbr_diff.where(nbr_nb_events.gte(nb_disturbances), 1)
        .And(nbr_diff.where(nbr_nb_events.lt(nb_disturbances), 0))
        .unmask(-2)
    )
    return nbr_nb_events_mask.multiply(nbr_diff).unmask(-2).updateMask(nbr_diff.mask())


# ---------------------------------------------------------------------------
# Top-level pipeline
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FcdmResult:
    forest_mask: ee.Image
    forest_mask_display: ee.Image
    reference_rnbr: ee.Image  # bands: NBR, yearday
    analysis_rnbr: ee.Image  # bands: NBR, yearday
    delta_rnbr_raw: ee.Image  # before DDR filter — bands: NBR, yearday
    delta_rnbr: ee.Image  # after DDR filter — bands: NBR, yearday


def run_fcdm(
    aoi,
    sensors: list[str],
    reference_start: str,
    reference_end: str,
    analysis_start: str,
    analysis_end: str,
    forest_map: str,
    forest_map_year: int,
    treecover: int,
    cloud_buffer: float,
    kernel_radius: float,
    filter_threshold: float,
    filter_radius: float,
    cleaning_offset: int,
) -> FcdmResult:
    """Run the full Delta-rNBR pipeline across selected sensors.

    Mirrors `launch_tile._launch_fcdm` from the legacy repo, minus the UI. All
    work is described as a GEE graph; no `.getInfo()` is called here.
    """
    if not sensors:
        raise ValueError("At least one sensor must be selected")

    forest_mask, forest_mask_display = get_forest_mask(forest_map, forest_map_year, treecover, aoi)

    analysis_nbr_merge = ee.ImageCollection([])
    reference_nbr_merge = ee.ImageCollection([])

    for sensor in sensors:
        analysis_coll = build_collection(
            sensor,
            analysis_start,
            analysis_end,
            forest_map,
            forest_map_year,
            forest_mask,
            cloud_buffer,
            aoi,
        )
        reference_coll = build_collection(
            sensor,
            reference_start,
            reference_end,
            forest_map,
            forest_map_year,
            forest_mask,
            cloud_buffer,
            aoi,
        )

        analysis_nbr = analysis_coll.map(partial(compute_nbr, sensor=sensor))
        reference_nbr = reference_coll.map(partial(compute_nbr, sensor=sensor))

        analysis_nbr = analysis_nbr.map(partial(adjustment_kernel, kernel_size=kernel_radius))
        reference_nbr = reference_nbr.map(partial(adjustment_kernel, kernel_size=kernel_radius))

        analysis_nbr_merge = analysis_nbr_merge.merge(analysis_nbr)
        reference_nbr_merge = reference_nbr_merge.merge(reference_nbr)

    analysis_rnbr = analysis_nbr_merge.map(capping).qualityMosaic("NBR")
    reference_rnbr = reference_nbr_merge.map(capping).qualityMosaic("NBR")

    nbr_diff = analysis_rnbr.select("NBR").subtract(reference_rnbr.select("NBR"))
    nbr_diff_capped = nbr_diff.select("NBR").where(nbr_diff.select("NBR").lt(0), 0)

    delta_raw = nbr_diff_capped.addBands(analysis_rnbr.select("yearday")).select("NBR", "yearday")

    nbr_diff_ddr = ddr_filter(
        nbr_diff_capped.select("NBR"),
        filter_threshold,
        filter_radius,
        cleaning_offset,
    )
    delta_rnbr = nbr_diff_ddr.addBands(analysis_rnbr.select("yearday")).select("NBR", "yearday")

    return FcdmResult(
        forest_mask=forest_mask,
        forest_mask_display=forest_mask_display,
        reference_rnbr=reference_rnbr.select("NBR", "yearday"),
        analysis_rnbr=analysis_rnbr.select("NBR", "yearday"),
        delta_rnbr_raw=delta_raw,
        delta_rnbr=delta_rnbr,
    )
