"""Tests for the same-origin tile archive route.

The route hands one user's file to a browser in a container shared with other
users, so every test here is about who is refused.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from apps._commons.tiles import (
    TILE_ROOT,
    cleanup_tile_dir,
    resolve_in_session,
    session_tile_dir,
)


@pytest.fixture
def tile_root(tmp_path, monkeypatch):
    """Point the tile helpers and the route at a temporary root."""
    import apps._commons.tiles as tiles

    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def client(tile_root):
    """A test client whose kernel registry we control."""
    from solara.server import kernel_context

    import asgi

    monkey = kernel_context.contexts
    kernel_context.contexts = {}
    try:
        yield TestClient(asgi.app)
    finally:
        kernel_context.contexts = monkey


class FakeContext:
    """Stands in for solara's VirtualKernelContext; the route reads session_id."""

    def __init__(self, session_id):
        self.session_id = session_id


def _register(kernel_id, session_id):
    from solara.server import kernel_context

    kernel_context.contexts[kernel_id] = FakeContext(session_id)


def _archive(tile_root, kernel_id, name="basins.pmtiles", payload=b"PMTiles-bytes"):
    directory = tile_root / kernel_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(payload)
    return payload


class TestTileArchiveAuthorization:
    def test_serves_the_archive_to_its_own_session(self, client, tile_root):
        payload = _archive(tile_root, "kernel-a")
        _register("kernel-a", "session-a")
        client.cookies.set("solara-session-id", "session-a")

        response = client.get("/tiles/kernel-a/basins.pmtiles")

        assert response.status_code == 200
        assert response.content == payload

    def test_refuses_another_users_session(self, client, tile_root):
        _archive(tile_root, "kernel-a")
        _register("kernel-a", "session-a")
        client.cookies.set("solara-session-id", "session-b")

        assert client.get("/tiles/kernel-a/basins.pmtiles").status_code == 403

    def test_refuses_a_missing_cookie(self, client, tile_root):
        _archive(tile_root, "kernel-a")
        _register("kernel-a", "session-a")

        assert client.get("/tiles/kernel-a/basins.pmtiles").status_code == 403

    def test_unknown_kernel_is_not_found(self, client, tile_root):
        _archive(tile_root, "kernel-a")
        client.cookies.set("solara-session-id", "session-a")

        assert client.get("/tiles/kernel-a/basins.pmtiles").status_code == 404

    def test_a_dead_kernel_stops_serving_its_files(self, client, tile_root):
        """Eviction removes the context; the files may outlive it briefly."""
        _archive(tile_root, "kernel-a")
        _register("kernel-a", "session-a")
        client.cookies.set("solara-session-id", "session-a")
        assert client.get("/tiles/kernel-a/basins.pmtiles").status_code == 200

        from solara.server import kernel_context

        del kernel_context.contexts["kernel-a"]

        assert client.get("/tiles/kernel-a/basins.pmtiles").status_code == 404


class TestTileArchiveServing:
    def test_supports_range_requests(self, client, tile_root):
        """PMTiles is read by byte range, so 206 is the normal case."""
        _archive(tile_root, "kernel-a", payload=b"0123456789")
        _register("kernel-a", "session-a")
        client.cookies.set("solara-session-id", "session-a")

        response = client.get(
            "/tiles/kernel-a/basins.pmtiles", headers={"Range": "bytes=2-5"}
        )

        assert response.status_code == 206
        assert response.content == b"2345"
        assert response.headers["content-range"] == "bytes 2-5/10"

    def test_advertises_range_support(self, client, tile_root):
        _archive(tile_root, "kernel-a")
        _register("kernel-a", "session-a")
        client.cookies.set("solara-session-id", "session-a")

        response = client.get("/tiles/kernel-a/basins.pmtiles")

        assert response.headers["accept-ranges"] == "bytes"

    def test_missing_file_is_not_found(self, client, tile_root):
        (tile_root / "kernel-a").mkdir()
        _register("kernel-a", "session-a")
        client.cookies.set("solara-session-id", "session-a")

        assert client.get("/tiles/kernel-a/absent.pmtiles").status_code == 404

    def test_refuses_a_non_archive_suffix(self, client, tile_root):
        """The directory is ours, but only archives are ever served from it."""
        _archive(tile_root, "kernel-a", name="notes.txt")
        _register("kernel-a", "session-a")
        client.cookies.set("solara-session-id", "session-a")

        assert client.get("/tiles/kernel-a/notes.txt").status_code == 404


class TestResolveInSession:
    def test_resolves_a_plain_name(self, tile_root):
        assert resolve_in_session("kernel-a", "basins.pmtiles").name == "basins.pmtiles"

    @pytest.mark.parametrize(
        "filename",
        ["../escape.pmtiles", "../../etc/passwd", "/etc/passwd", "a/../../escape.pmtiles"],
    )
    def test_refuses_an_escape(self, tile_root, filename):
        with pytest.raises(ValueError, match="escapes"):
            resolve_in_session("kernel-a", filename)

    @pytest.mark.parametrize("session_id", ["", ".", "..", "a/b", "/abs", "a\\b"])
    def test_refuses_an_unsafe_session_id(self, tile_root, session_id):
        with pytest.raises(ValueError, match="unsafe session id"):
            resolve_in_session(session_id, "basins.pmtiles")


class TestSessionDirectories:
    def test_cleanup_never_wipes_the_shared_root(self, tile_root):
        """An empty id joins to TILE_ROOT itself, which rmtree would erase."""
        session_tile_dir("kernel-a")

        for unsafe in ("", ".", "..", "/", "a/b"):
            with pytest.raises(ValueError):
                cleanup_tile_dir(unsafe)

        assert (tile_root / "kernel-a").is_dir()

    def test_cleanup_removes_only_its_own_session(self, tile_root):
        session_tile_dir("kernel-a")
        session_tile_dir("kernel-b")

        cleanup_tile_dir("kernel-a")

        assert not (tile_root / "kernel-a").exists()
        assert (tile_root / "kernel-b").is_dir()

    def test_cleanup_is_safe_when_nothing_was_written(self, tile_root):
        cleanup_tile_dir("never-used")

    def test_tile_root_is_not_the_bare_temp_dir(self):
        """A stray rmtree of TILE_ROOT must not take /tmp with it."""
        assert TILE_ROOT.name == "sepal_gee_bundle_tiles"
