"""Turn the upstream basins into a PMTiles layer.

Rendering thousands of basin polygons as client-side GeoJSON is what made large
watersheds unusable; tiles fix the drawing, and batching the fetch fixes the
transfer.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

import ee
import solara
from solara.server import settings

from apps._commons.tiles import session_tile_dir
from apps.basin_rivers.params import BASIN_FETCH_BATCH_SIZE, BASIN_FETCH_WINDOW

if TYPE_CHECKING:
    from vectortileserver import VectorTileLayer


def browser_tile_prefix(kernel_id: str) -> str:
    """URL prefix the browser should use to reach this session's archives.

    Points at the route ``asgi.py`` serves rather than the kernel-local
    loopback address, which no remote browser can resolve. The route is keyed
    by kernel because it authorizes per session, and ``root_path`` carries the
    app-launcher prefix -- a bare ``/tiles/...`` 404s behind the proxy. Solara
    fills that setting in from the ASGI scope on the first page request, well
    before any layer is built.

    Args:
        kernel_id: the Solara kernel id.

    Returns:
        the prefix vectortileserver appends ``/pmtiles?filePath=...`` to.
    """
    root_path = settings.main.root_path or ""

    return f"{root_path}/tiles/{kernel_id}"


def _batches(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def write_basins_geojson(
    gee_interface,
    upstream_fc: ee.FeatureCollection,
    hybas_ids: Iterable,
    dest: Path,
) -> int:
    """Fetch the basins in bounded windows and stream them to newline-delimited GeoJSON.

    Batching by ``HYBAS_ID`` keeps each response under Earth Engine's payload
    limit. Windowing the batches is a separate concern: ``get_info_batch_async``
    gathers everything handed to it, so passing every batch at once would both
    fire every request concurrently and hold all responses in memory — exactly
    what this is meant to avoid on the large watersheds it exists for.

    Args:
        gee_interface: the session-backed GEEInterface.
        upstream_fc: the delineated upstream collection.
        hybas_ids: the basin ids to fetch.
        dest: file to write.

    Returns:
        the number of features written.

    Raises:
        Exception: whatever Earth Engine raised for the first failed batch.
    """
    batches = list(_batches(list(hybas_ids), BASIN_FETCH_BATCH_SIZE))

    count = 0
    with open(dest, "w") as f:
        for window in _batches(batches, BASIN_FETCH_WINDOW):
            chunks = [
                upstream_fc.filter(ee.Filter.inList("HYBAS_ID", batch)) for batch in window
            ]
            results = await gee_interface.get_info_batch_async(chunks)

            for result in results:
                # get_info_batch_async gathers with return_exceptions=True, so a
                # failed batch arrives as a value rather than propagating.
                if isinstance(result, Exception):
                    raise result
                for feature in result.get("features", []):
                    f.write(json.dumps(feature) + "\n")
                    count += 1

            # Not a memory bound: Python's text buffer is already ~8 KB. This flush
            # is load-bearing for test_writes_each_window_before_fetching_the_next,
            # which reads the file mid-run and expects each window's rows to
            # already be on disk before the next is fetched.
            f.flush()

    return count


async def build_basins_layer(
    gee_interface,
    upstream_fc: ee.FeatureCollection,
    hybas_ids: Iterable,
    name: str = "Upstream catchment",
) -> Optional["VectorTileLayer"]:
    """Convert the upstream basins to PMTiles and return a styled tile layer.

    Args:
        gee_interface: the session-backed GEEInterface.
        upstream_fc: the delineated upstream collection.
        hybas_ids: the basin ids to fetch.
        name: layer name on the map.

    Returns:
        a ``VectorTileLayer``, or ``None`` when the collection was empty.
    """
    import vectortileserver as vts

    from apps.basin_rivers.scripts.visualization import basin_tile_style

    kernel_id = solara.get_kernel_id()
    tile_dir = session_tile_dir(kernel_id)
    dest = tile_dir / "upstream_basins.geojson"

    if not await write_basins_geojson(gee_interface, upstream_fc, hybas_ids, dest):
        return None

    workspace = vts.TileWorkspace(
        client_prefix=browser_tile_prefix(kernel_id), allowed_directories=[tile_dir]
    )
    layer = await workspace.open_async(dest, style=basin_tile_style(hybas_ids))
    layer.name = name

    # Safe to reclaim now: the layer serves the converted PMTiles (its
    # pmtiles_path), never this intermediate .geojson, and the next trace
    # recreates dest via write_basins_geojson before any TileConverter/_can_reuse
    # check runs again. Left alone, it would sit in /tmp until cull_timeout
    # (24h default, unoverridden here) reaps the session directory.
    dest.unlink(missing_ok=True)

    return layer
