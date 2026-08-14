"""Filename sanitisation and SEPAL user-files persistence for extracted sources."""

from __future__ import annotations

import re
from typing import Any

from apps.gee_source.params import OUTPUT_EXTENSION

_INVALID_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    """Return a safe basename for the extracted ``.js`` file.

    - Strips any directory components.
    - Drops a trailing ``.js`` extension if present (it's re-added at save time).
    - Replaces every character outside ``[A-Za-z0-9._-]`` with ``_``.
    - Collapses repeated underscores and trims leading / trailing separators.
    - Falls back to ``gee_source`` if the input is empty after cleaning.
    """
    if not name:
        return "gee_source"

    basename = name.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    if basename.lower().endswith(OUTPUT_EXTENSION):
        basename = basename[: -len(OUTPUT_EXTENSION)]

    cleaned = _INVALID_CHARS.sub("_", basename)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned or "gee_source"


def _join_remote_path(folder: str, filename: str) -> str:
    return f"{folder.rstrip('/')}/{filename}"


def _remote_file_exists(sepal_client: Any, folder: str, filename: str) -> bool:
    return any(entry.name == filename for entry in sepal_client.files.list(folder))


def save_code(code: str, filename: str, *, sepal_client: Any) -> str:
    """Write ``code`` to ``SepalClient.results_path/<filename>.js``.

    Args:
        code: JavaScript source to persist.
        filename: Raw filename from the UI; will be sanitized.
        sepal_client: Session-bound SepalClient used for user-files access.

    Raises:
        ValueError: If ``code`` is empty, SepalClient is unavailable, or the
            destination already exists.
    """
    if not code:
        raise ValueError("Cannot save empty source code.")
    if sepal_client is None:
        raise ValueError("A SEPAL session is required to save user files.")

    results_dir = sepal_client.ensure_results_dir()
    if not results_dir:
        raise ValueError("SepalClient does not expose a module results path.")

    target_dir = str(results_dir)

    safe_name = sanitize_filename(filename)
    target_filename = f"{safe_name}{OUTPUT_EXTENSION}"
    target_path = _join_remote_path(target_dir, target_filename)

    if _remote_file_exists(sepal_client, target_dir, target_filename):
        raise ValueError(f'File already exists: "{target_path}"')

    sepal_client.files.write(
        target_path,
        code,
        overwrite=False,
    )
    return target_path
