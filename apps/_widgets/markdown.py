"""Markdown helper that forces every link to open in a new tab."""

from __future__ import annotations

import re
from typing import Optional

import mistune
import solara

_LINK_RE = re.compile(r"<a\s+(?![^>]*\btarget=)", re.IGNORECASE)


def _render(text: str) -> str:
    html = mistune.html(text)
    return _LINK_RE.sub('<a target="_blank" rel="noopener noreferrer" ', html)


@solara.component
def MarkdownNewTab(text: str, style: Optional[str] = None):
    """Render Markdown with every `<a>` opening in a new tab.

    Drop-in replacement for `solara.Markdown` for trusted, app-authored
    content (About dialogs, references). Do not use for untrusted input.
    """
    html = _render(text)
    if style:
        html = f"<style>{style}</style>{html}"
    solara.HTML(tag="div", unsafe_innerHTML=html, classes=["markdown-new-tab"])
