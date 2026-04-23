"""Filename sanitisation and on-disk persistence for extracted sources."""

from __future__ import annotations

import re
from pathlib import Path

from apps.gee_source.params import OUTPUT_EXTENSION, RESULT_DIR

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

    basename = Path(name).name
    if basename.lower().endswith(OUTPUT_EXTENSION):
        basename = basename[: -len(OUTPUT_EXTENSION)]

    cleaned = _INVALID_CHARS.sub("_", basename)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned or "gee_source"


def save_code(code: str, filename: str, *, result_dir: Path | None = None) -> Path:
    """Write ``code`` to ``<result_dir>/<filename>.js`` and return the path.

    Args:
        code: JavaScript source to persist.
        filename: Raw filename from the UI; will be sanitized.
        result_dir: Override the default output directory (useful for tests).

    Raises:
        ValueError: If ``code`` is empty or the destination already exists.
    """
    if not code:
        raise ValueError("Cannot save empty source code.")

    target_dir = result_dir if result_dir is not None else RESULT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(filename)
    target = target_dir / f"{safe_name}{OUTPUT_EXTENSION}"
    if target.exists():
        raise ValueError(f'File already exists: "{target}"')

    target.write_text(code, encoding="utf-8")
    return target
