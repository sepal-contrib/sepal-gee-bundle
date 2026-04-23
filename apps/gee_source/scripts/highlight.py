"""Turn raw JavaScript into a syntax-highlighted HTML fragment."""

from __future__ import annotations

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

_STYLE = (
    "overflow: auto; max-height: 65vh; border-radius: 3px; "
    "border: 1px solid rgba(127, 127, 127, 0.4);"
)


def highlight_javascript(raw_code: str) -> str:
    """Format ``raw_code`` as pygments-highlighted HTML.

    Returns an empty string when there is nothing to highlight.
    """
    if not raw_code:
        return ""

    formatter = HtmlFormatter()
    lexer = get_lexer_by_name("javascript")
    formatted = highlight(raw_code, lexer, formatter)

    old_tag = '<div class="highlight">'
    new_tag = f'<div class="highlight pa-3 mt-2" style="{_STYLE}">'
    return formatted.replace(old_tag, new_tag)


def highlight_css() -> str:
    """Return the default pygments stylesheet as a CSS string."""
    return HtmlFormatter().get_style_defs(".highlight")
