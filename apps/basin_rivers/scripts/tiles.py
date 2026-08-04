"""Turn the upstream basins into a PMTiles layer.

Rendering thousands of basin polygons as client-side GeoJSON is what made large
watersheds unusable; tiles fix the drawing, and batching the fetch fixes the
transfer.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

import ee
import solara

from apps.basin_rivers.params import BASIN_FETCH_BATCH_SIZE, BASIN_FETCH_WINDOW

if TYPE_CHECKING:
    from vectortileserver import VectorTileLayer

TILE_ROOT = Path(tempfile.gettempdir()) / "sepal_gee_bundle_tiles"


def _session_dir(session_id: str) -> Path:
    """Resolve a session id to its directory under TILE_ROOT.

    This id ultimately reaches ``shutil.rmtree``, so anything that is not a
    single plain path component is rejected before it is joined: an empty,
    "." or ".." id collapses to ``TILE_ROOT`` itself under ``Path.__truediv__``
    (making cleanup wipe every session), and an embedded separator can escape
    it entirely (absolute id, or a "../" traversal).

    Args:
        session_id: the Solara kernel id.

    Returns:
        the (not yet created) path under TILE_ROOT.

    Raises:
        ValueError: session_id is empty, ".", "..", or contains a path separator.
    """
    if not session_id or session_id in (".", "..") or "/" in session_id:
        raise ValueError(f"unsafe session id: {session_id!r}")

    return TILE_ROOT / session_id


def session_tile_dir(session_id: str) -> Path:
    """Directory holding one session's tile artifacts.

    The tile endpoint serves anything inside its allowed directories, so this
    root holds generated archives and nothing else.

    Args:
        session_id: the Solara kernel id.

    Returns:
        the created directory.

    Raises:
        ValueError: session_id is empty, ".", "..", or contains a path separator.
    """
    path = _session_dir(session_id)
    path.mkdir(parents=True, exist_ok=True)

    return path


def cleanup_tile_dir(session_id: str) -> None:
    """Remove a session's tile artifacts. Safe when nothing was written.

    Args:
        session_id: the Solara kernel id.

    Raises:
        ValueError: session_id is empty, ".", "..", or contains a path separator.
    """
    shutil.rmtree(_session_dir(session_id), ignore_errors=True)


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

    tile_dir = session_tile_dir(solara.get_kernel_id())
    dest = tile_dir / "upstream_basins.geojson"

    if not await write_basins_geojson(gee_interface, upstream_fc, hybas_ids, dest):
        return None

    # No client_prefix on purpose: the URL must stay the kernel-local loopback URL
    # so pysepal's TileBridge (mounted in page.py) can intercept it.
    workspace = vts.TileWorkspace(allowed_directories=[tile_dir])
    layer = await workspace.open_async(dest, style=basin_tile_style(hybas_ids))
    layer.name = name

    # Safe to reclaim now: the layer serves the converted PMTiles (its
    # pmtiles_path), never this intermediate .geojson, and the next trace
    # recreates dest via write_basins_geojson before any TileConverter/_can_reuse
    # check runs again. Left alone, it would sit in /tmp until cull_timeout
    # (24h default, unoverridden here) reaps the session directory.
    dest.unlink(missing_ok=True)

    return layer
