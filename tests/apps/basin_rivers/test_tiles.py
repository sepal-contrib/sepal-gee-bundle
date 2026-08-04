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


def test_session_tile_dir_is_per_session_and_created(tmp_path, monkeypatch):
    from apps.basin_rivers.scripts import tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")

    first = tiles.session_tile_dir("session-a")
    second = tiles.session_tile_dir("session-b")

    assert first.is_dir() and second.is_dir()
    assert first != second


def test_cleanup_removes_the_session_directory(tmp_path, monkeypatch):
    from apps.basin_rivers.scripts import tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")
    path = tiles.session_tile_dir("session-a")
    (path / "x.pmtiles").write_text("data")

    tiles.cleanup_tile_dir("session-a")

    assert not path.exists()


def test_cleanup_is_safe_when_nothing_was_written(tmp_path, monkeypatch):
    from apps.basin_rivers.scripts import tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")

    tiles.cleanup_tile_dir("never-used")


def test_session_tile_dir_still_works_for_a_normal_id(tmp_path, monkeypatch):
    from apps.basin_rivers.scripts import tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")

    path = tiles.session_tile_dir("session-a")

    assert path == tmp_path / "tiles" / "session-a"
    assert path.is_dir()


# "" and "." both collapse to TILE_ROOT itself under Path.__truediv__, so both
# are as dangerous as each other for cleanup_tile_dir; "/etc/passwd" (absolute)
# and "../escape" (traversal) both leave TILE_ROOT entirely.
UNSAFE_SESSION_IDS = ["", ".", "..", "/etc/passwd", "../escape"]


@pytest.mark.parametrize("bad_id", UNSAFE_SESSION_IDS)
def test_session_tile_dir_rejects_unsafe_ids(tmp_path, monkeypatch, bad_id):
    from apps.basin_rivers.scripts import tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")

    with pytest.raises(ValueError):
        tiles.session_tile_dir(bad_id)


@pytest.mark.parametrize("bad_id", UNSAFE_SESSION_IDS)
def test_cleanup_tile_dir_rejects_unsafe_ids(tmp_path, monkeypatch, bad_id):
    from apps.basin_rivers.scripts import tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")

    with pytest.raises(ValueError):
        tiles.cleanup_tile_dir(bad_id)


@pytest.mark.parametrize("bad_id", ["", "."])
def test_cleanup_with_root_collapsing_id_does_not_wipe_tile_root(tmp_path, monkeypatch, bad_id):
    from apps.basin_rivers.scripts import tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")
    tiles.session_tile_dir("session-a")

    with pytest.raises(ValueError):
        tiles.cleanup_tile_dir(bad_id)

    # The property that actually matters: other sessions survive a bad id.
    assert tiles.TILE_ROOT.is_dir()
    assert (tiles.TILE_ROOT / "session-a").is_dir()
