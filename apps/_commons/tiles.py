"""Per-session scratch directories for kernel-generated tile archives.

Tile servers running inside the kernel bind ``127.0.0.1``, which a remote
browser cannot reach. This bundle serves the archives itself instead (see
``asgi.py``), so the archives need a location the route can authorize: one
directory per kernel, and nothing shared between them.
"""

import shutil
import tempfile
from pathlib import Path

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
    if not session_id or session_id in (".", "..") or "/" in session_id or "\\" in session_id:
        raise ValueError(f"unsafe session id: {session_id!r}")

    return TILE_ROOT / session_id


def session_tile_dir(session_id: str) -> Path:
    """Directory holding one session's tile artifacts.

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


def resolve_in_session(session_id: str, filename: str) -> Path:
    """Resolve ``filename`` inside a session's directory, refusing any escape.

    Both components arrive from the request URL, so the resolved path is
    checked against the session directory rather than trusted: a ``..``
    segment, an absolute name or a symlink out of the directory all resolve
    somewhere else, and only containment proves they did not.

    Args:
        session_id: the Solara kernel id.
        filename: the requested archive name.

    Returns:
        the resolved path, guaranteed to sit under the session directory.

    Raises:
        ValueError: the id is unsafe, or the name resolves outside the session.
    """
    root = _session_dir(session_id).resolve()
    target = (root / filename).resolve()

    if target != root and root not in target.parents:
        raise ValueError(f"path escapes the session directory: {filename!r}")

    return target
