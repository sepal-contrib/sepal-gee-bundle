"""Batched basin fetching and the per-session tile directory."""

import json
from unittest.mock import MagicMock, patch

import pytest


def _feature(basin_id):
    return {
        "type": "Feature",
        "properties": {"HYBAS_ID": basin_id},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }


class FakeGeeInterface:
    """Serves one response per chunk, in order, recording each window's size."""

    def __init__(self, batches):
        self._queue = list(batches)
        self.window_sizes = []
        self.lines_on_disk_per_call = []
        self.dest = None

    async def get_info_batch_async(self, chunks):
        self.window_sizes.append(len(chunks))
        if self.dest is not None:
            written = self.dest.read_text() if self.dest.exists() else ""
            self.lines_on_disk_per_call.append(len(written.splitlines()))
        taken = [self._queue.pop(0) for _ in chunks]

        return [{"features": [_feature(i) for i in batch]} for batch in taken]


@pytest.fixture
def upstream_fc():
    fc = MagicMock()
    fc.filter.return_value = fc
    return fc


def _split(ids, size):
    return [ids[i : i + size] for i in range(0, len(ids), size)]


@pytest.mark.asyncio
async def test_writes_one_feature_per_line(tmp_path, upstream_fc):
    from apps.basin_rivers.scripts.tiles import write_basins_geojson

    dest = tmp_path / "basins.geojson"
    gee = FakeGeeInterface([[1, 2, 3]])

    with patch("apps.basin_rivers.scripts.tiles.ee"):
        count = await write_basins_geojson(gee, upstream_fc, [1, 2, 3], dest)

    lines = dest.read_text().strip().split("\n")
    assert count == 3
    assert len(lines) == 3
    assert json.loads(lines[0])["properties"]["HYBAS_ID"] == 1


@pytest.mark.asyncio
async def test_splits_ids_into_batches(tmp_path, upstream_fc):
    from apps.basin_rivers.params import BASIN_FETCH_BATCH_SIZE
    from apps.basin_rivers.scripts.tiles import write_basins_geojson

    ids = list(range(BASIN_FETCH_BATCH_SIZE + 5))
    gee = FakeGeeInterface(_split(ids, BASIN_FETCH_BATCH_SIZE))

    with patch("apps.basin_rivers.scripts.tiles.ee"):
        await write_basins_geojson(gee, upstream_fc, ids, tmp_path / "b.geojson")

    assert upstream_fc.filter.call_count == 2


@pytest.mark.asyncio
async def test_bounds_the_number_of_requests_in_flight(tmp_path, upstream_fc):
    import math

    from apps.basin_rivers.params import BASIN_FETCH_BATCH_SIZE, BASIN_FETCH_WINDOW
    from apps.basin_rivers.scripts.tiles import write_basins_geojson

    n_batches = BASIN_FETCH_WINDOW + 2
    ids = list(range(BASIN_FETCH_BATCH_SIZE * n_batches))
    gee = FakeGeeInterface(_split(ids, BASIN_FETCH_BATCH_SIZE))

    with patch("apps.basin_rivers.scripts.tiles.ee"):
        count = await write_basins_geojson(gee, upstream_fc, ids, tmp_path / "b.geojson")

    assert count == len(ids)
    assert max(gee.window_sizes) <= BASIN_FETCH_WINDOW
    assert len(gee.window_sizes) == math.ceil(n_batches / BASIN_FETCH_WINDOW)


@pytest.mark.asyncio
async def test_writes_each_window_before_fetching_the_next(tmp_path, upstream_fc):
    from apps.basin_rivers.params import BASIN_FETCH_BATCH_SIZE, BASIN_FETCH_WINDOW
    from apps.basin_rivers.scripts.tiles import write_basins_geojson

    ids = list(range(BASIN_FETCH_BATCH_SIZE * (BASIN_FETCH_WINDOW + 1)))
    dest = tmp_path / "b.geojson"
    gee = FakeGeeInterface(_split(ids, BASIN_FETCH_BATCH_SIZE))
    gee.dest = dest

    with patch("apps.basin_rivers.scripts.tiles.ee"):
        await write_basins_geojson(gee, upstream_fc, ids, dest)

    # Nothing on disk when the first window is requested, the first window's
    # features on disk by the time the second is — i.e. it does not accumulate
    # every response before writing.
    assert gee.lines_on_disk_per_call[0] == 0
    assert gee.lines_on_disk_per_call[1] == BASIN_FETCH_BATCH_SIZE * BASIN_FETCH_WINDOW


@pytest.mark.asyncio
async def test_raises_when_a_batch_failed(tmp_path, upstream_fc):
    from apps.basin_rivers.scripts.tiles import write_basins_geojson

    gee = MagicMock()

    async def _batch(chunks):
        return [RuntimeError("EE said no")]

    gee.get_info_batch_async = _batch

    with patch("apps.basin_rivers.scripts.tiles.ee"):
        with pytest.raises(RuntimeError, match="EE said no"):
            await write_basins_geojson(gee, upstream_fc, [1], tmp_path / "b.geojson")


class TestBrowserTilePrefix:
    """The prefix decides the URL the browser fetches the archive from."""

    def test_points_at_the_session_route(self, monkeypatch):
        from solara.server import settings

        from apps.basin_rivers.scripts.tiles import browser_tile_prefix

        monkeypatch.setattr(settings.main, "root_path", None)

        assert browser_tile_prefix("kernel-a") == "/tiles/kernel-a"

    def test_carries_the_app_launcher_root_path(self, monkeypatch):
        """A bare /tiles/... 404s behind the proxy, so root_path must lead."""
        from solara.server import settings

        from apps.basin_rivers.scripts.tiles import browser_tile_prefix

        monkeypatch.setattr(settings.main, "root_path", "/api/app-launcher/sepal-gee-bundle")

        prefix = browser_tile_prefix("kernel-a")

        assert prefix == "/api/app-launcher/sepal-gee-bundle/tiles/kernel-a"

    def test_the_url_vectortileserver_builds_matches_the_route(self, monkeypatch):
        """asgi.py routes /tiles/{kernel_id}/pmtiles; the client appends that."""
        from solara.server import settings

        from apps.basin_rivers.scripts.tiles import browser_tile_prefix

        monkeypatch.setattr(settings.main, "root_path", None)

        url = f"{browser_tile_prefix('kernel-a')}/pmtiles?filePath=/tmp/x.pmtiles"

        assert url.startswith("/tiles/kernel-a/pmtiles?")
