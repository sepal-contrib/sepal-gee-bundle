"""Tests for the per-session tile directories.

Both the session id and the archive path reach these helpers from a request
URL, and one of them reaches ``shutil.rmtree``, so most of this is about what
they refuse.
"""

from __future__ import annotations

import pytest

from apps._commons import tiles


@pytest.fixture(autouse=True)
def tile_root(tmp_path, monkeypatch):
    monkeypatch.setattr(tiles, "TILE_ROOT", tmp_path / "tiles")
    return tmp_path / "tiles"


# "" and "." both collapse to TILE_ROOT itself under Path.__truediv__, so both
# are as dangerous as each other for cleanup_tile_dir; "/etc/passwd" (absolute)
# and "../escape" (traversal) both leave TILE_ROOT entirely.
UNSAFE_SESSION_IDS = ["", ".", "..", "/etc/passwd", "../escape"]


def test_session_tile_dir_is_per_session_and_created():
    first = tiles.session_tile_dir("session-a")
    second = tiles.session_tile_dir("session-b")

    assert first.is_dir() and second.is_dir()
    assert first != second


def test_session_tile_dir_sits_under_the_root(tile_root):
    path = tiles.session_tile_dir("session-a")

    assert path == tile_root / "session-a"
    assert path.is_dir()


def test_cleanup_removes_the_session_directory():
    path = tiles.session_tile_dir("session-a")
    (path / "x.pmtiles").write_text("data")

    tiles.cleanup_tile_dir("session-a")

    assert not path.exists()


def test_cleanup_leaves_other_sessions_alone(tile_root):
    tiles.session_tile_dir("session-a")
    tiles.session_tile_dir("session-b")

    tiles.cleanup_tile_dir("session-a")

    assert not (tile_root / "session-a").exists()
    assert (tile_root / "session-b").is_dir()


def test_cleanup_is_safe_when_nothing_was_written():
    tiles.cleanup_tile_dir("never-used")


@pytest.mark.parametrize("bad_id", UNSAFE_SESSION_IDS)
def test_session_tile_dir_rejects_unsafe_ids(bad_id):
    with pytest.raises(ValueError, match="unsafe session id"):
        tiles.session_tile_dir(bad_id)


@pytest.mark.parametrize("bad_id", UNSAFE_SESSION_IDS)
def test_cleanup_tile_dir_rejects_unsafe_ids(bad_id):
    with pytest.raises(ValueError, match="unsafe session id"):
        tiles.cleanup_tile_dir(bad_id)


@pytest.mark.parametrize("bad_id", ["", "."])
def test_cleanup_with_root_collapsing_id_does_not_wipe_tile_root(tile_root, bad_id):
    tiles.session_tile_dir("session-a")

    with pytest.raises(ValueError):
        tiles.cleanup_tile_dir(bad_id)

    # The property that actually matters: other sessions survive a bad id.
    assert tile_root.is_dir()
    assert (tile_root / "session-a").is_dir()


def test_tile_root_is_not_the_bare_temp_dir(monkeypatch):
    """A stray rmtree of TILE_ROOT must not take the whole temp dir with it."""
    monkeypatch.undo()

    assert tiles.TILE_ROOT.name == "sepal_gee_bundle_tiles"


class TestResolveInSession:
    def test_resolves_a_plain_name(self, tile_root):
        assert tiles.resolve_in_session("session-a", "b.pmtiles").name == "b.pmtiles"

    def test_accepts_an_absolute_path_inside_the_session(self, tile_root):
        """The normal case: vectortileserver sends the archive's absolute path."""
        inside = tile_root / "session-a" / "b.pmtiles"

        assert tiles.resolve_in_session("session-a", str(inside)) == inside

    @pytest.mark.parametrize(
        "filename",
        ["../escape.pmtiles", "../../etc/passwd", "/etc/passwd", "a/../../escape.pmtiles"],
    )
    def test_refuses_an_escape(self, tile_root, filename):
        with pytest.raises(ValueError, match="escapes"):
            tiles.resolve_in_session("session-a", filename)

    def test_refuses_a_path_in_another_session(self, tile_root):
        other = tile_root / "session-b" / "b.pmtiles"

        with pytest.raises(ValueError, match="escapes"):
            tiles.resolve_in_session("session-a", str(other))

    @pytest.mark.parametrize("bad_id", UNSAFE_SESSION_IDS)
    def test_refuses_an_unsafe_session_id(self, tile_root, bad_id):
        with pytest.raises(ValueError, match="unsafe session id"):
            tiles.resolve_in_session(bad_id, "b.pmtiles")
