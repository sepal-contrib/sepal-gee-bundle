"""Upstream watershed delineation using WWF HydroSHEDS basins."""

import ee

from apps.basin_rivers.params import HYBAS_DATASET_TEMPLATE


def get_hydroshed_collection(level: int) -> ee.FeatureCollection:
    """Return the HydroSHEDS basin FeatureCollection for the given level."""
    if level not in range(5, 13):
        raise ValueError(f"HydroSHEDS level must be 5-12, got {level}")
    return ee.FeatureCollection(HYBAS_DATASET_TEMPLATE.format(level=level))


def build_upstream_fc(
    level: int, geometry: ee.Geometry, max_steps: int = 100
) -> ee.FeatureCollection:
    """Build a lazy ee.FeatureCollection of all upstream basins.

    Iteratively traces upstream through the NEXT_DOWN field in HydroSHEDS.
    Returns a lazy EE object (not materialized).

    Args:
        level: HydroSHEDS basin level (5-12).
        geometry: Point geometry to find the initial basin.
        max_steps: Maximum upstream tracing iterations.
    """
    base_basin = get_hydroshed_collection(level)

    def get_upper(i, acc):
        acc = ee.List(acc)
        feature_collection = ee.FeatureCollection(acc.get(acc.size().subtract(1)))
        base_ids = feature_collection.aggregate_array("HYBAS_ID")
        upper_catchments = base_basin.filter(ee.Filter.inList("NEXT_DOWN", base_ids))
        return acc.add(upper_catchments)

    accumulated = ee.List.sequence(1, max_steps).iterate(
        get_upper, [base_basin.filterBounds(geometry)]
    )

    upstream_fc = ee.FeatureCollection(
        ee.List(accumulated).iterate(
            lambda fc, acc: ee.FeatureCollection(acc).merge(ee.FeatureCollection(fc)),
            ee.FeatureCollection([]),
        )
    )

    return upstream_fc


async def get_upstream_basin_ids(
    gee_interface, level: int, geometry: ee.Geometry, max_steps: int = 100
) -> tuple[ee.FeatureCollection, list[int]]:
    """Delineate upstream basins and materialize the HYBAS_ID list.

    Args:
        gee_interface: Session-backed GEEInterface.
        level: HydroSHEDS basin level (5-12).
        geometry: Point geometry for the pour point.
        max_steps: Maximum upstream tracing iterations.

    Returns:
        Tuple of (upstream ee.FeatureCollection, list of HYBAS_ID ints).
    """
    upstream_fc = build_upstream_fc(level, geometry, max_steps)
    hybas_ids = await gee_interface.get_info_async(upstream_fc.aggregate_array("HYBAS_ID"))
    return upstream_fc, hybas_ids
