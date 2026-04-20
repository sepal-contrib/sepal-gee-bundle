"""Native vector legend Flowable for reportlab PDFs.

Re-draws a ``LegendData``-shaped dict as reportlab drawing primitives so
gradients and chips print crisply at any zoom, without needing to capture
the overlay HTML.
"""

from __future__ import annotations

from reportlab.lib.colors import HexColor
from reportlab.platypus import Flowable

_TITLE_FONT = "Helvetica-Bold"
_TITLE_SIZE = 11
_LABEL_FONT = "Helvetica"
_LABEL_SIZE = 9
_SMALL_LABEL_SIZE = 8

_GRADIENT_TITLE_GAP = 12
_GRADIENT_BAR_HEIGHT = 12
_GRADIENT_LABEL_GAP = 12
_GRADIENT_BLOCK_PADDING = 6
_GRADIENT_STOPS = 120

_CHIP_SIZE = 10
_CHIP_ROW_HEIGHT = 18
_CHIPS_PER_ROW = 2

_TITLE_HEIGHT = 16
_BLOCK_GAP = 6


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Parse ``#rrggbb`` / ``rrggbb`` / ``#rgb`` / ``rgb`` into a 0-255 tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _expand_hex(hex_color: str) -> str:
    """Return a ``#rrggbb`` form, expanding 3-char shorthand if needed."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return f"#{h}"


def _sample_gradient(colors: list[str], t: float) -> str:
    """Sample a piecewise-linear color ramp at ``t`` in ``[0, 1]``."""
    if not colors:
        return "#000000"
    if len(colors) == 1:
        return colors[0]
    n = len(colors) - 1
    idx = max(0.0, min(1.0, t)) * n
    lo = int(idx)
    hi = min(lo + 1, n)
    frac = idx - lo
    r1, g1, b1 = _hex_to_rgb(colors[lo])
    r2, g2, b2 = _hex_to_rgb(colors[hi])
    r = int(round(r1 + (r2 - r1) * frac))
    g = int(round(g1 + (g2 - g1) * frac))
    b = int(round(b1 + (b2 - b1) * frac))
    return f"#{r:02x}{g:02x}{b:02x}"


class LegendFlowable(Flowable):
    """A reportlab Flowable that renders a LegendData dict.

    Expected dict shape (matches ``dataclasses.asdict(LegendData)``):

        {
            "gradients": [
                {"colors": ["#ff0", "#800"], "labels": ["2001", "2024"], "title": ""},
                ...
            ],
            "items": [{"label": "Forest", "color": "#064"}, ...],
        }
    """

    def __init__(self, legend_data: dict, title: str = "Legend") -> None:
        super().__init__()
        self.legend_data = legend_data or {}
        self.title = title
        self._width: float = 0.0
        self._height: float = 0.0

    # ---- reportlab Flowable API -------------------------------------------------

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:
        self._width = availWidth
        gradients = self.legend_data.get("gradients") or []
        items = self.legend_data.get("items") or []

        height = _TITLE_HEIGHT

        for g in gradients:
            height += _GRADIENT_BLOCK_PADDING
            if g.get("title"):
                height += _GRADIENT_TITLE_GAP
            height += _GRADIENT_BAR_HEIGHT
            height += _GRADIENT_LABEL_GAP

        if items:
            rows = (len(items) + _CHIPS_PER_ROW - 1) // _CHIPS_PER_ROW
            height += _BLOCK_GAP + rows * _CHIP_ROW_HEIGHT

        self._height = height
        return self._width, height

    def draw(self) -> None:
        c = self.canv
        y = self._height

        # Title
        y -= _TITLE_HEIGHT
        c.setFillColor(HexColor("#000000"))
        c.setFont(_TITLE_FONT, _TITLE_SIZE)
        c.drawString(0, y + 4, self.title)

        # Gradients
        for g in self.legend_data.get("gradients") or []:
            y -= _GRADIENT_BLOCK_PADDING

            g_title = g.get("title") or ""
            if g_title:
                y -= _GRADIENT_TITLE_GAP
                c.setFont(_LABEL_FONT, _LABEL_SIZE)
                c.setFillColor(HexColor("#000000"))
                c.drawString(0, y, g_title)

            colors = list(g.get("colors") or [])
            labels = list(g.get("labels") or [])

            y -= _GRADIENT_BAR_HEIGHT
            bar_w = self._width
            step = bar_w / _GRADIENT_STOPS
            for i in range(_GRADIENT_STOPS):
                t = i / max(_GRADIENT_STOPS - 1, 1)
                c.setFillColor(HexColor(_sample_gradient(colors, t)))
                c.rect(i * step, y, step + 0.5, _GRADIENT_BAR_HEIGHT, fill=1, stroke=0)

            y -= _GRADIENT_LABEL_GAP
            c.setFillColor(HexColor("#000000"))
            c.setFont(_LABEL_FONT, _SMALL_LABEL_SIZE)
            if labels:
                c.drawString(0, y + 2, labels[0])
                if len(labels) > 1:
                    end = labels[-1]
                    w = c.stringWidth(end, _LABEL_FONT, _SMALL_LABEL_SIZE)
                    c.drawString(bar_w - w, y + 2, end)

        # Discrete chips
        items = self.legend_data.get("items") or []
        if items:
            y -= _BLOCK_GAP
            col_width = self._width / _CHIPS_PER_ROW
            for i, item in enumerate(items):
                col = i % _CHIPS_PER_ROW
                row = i // _CHIPS_PER_ROW
                x = col * col_width
                row_y = y - row * _CHIP_ROW_HEIGHT

                color = _expand_hex(item.get("color") or "#000000")
                c.setFillColor(HexColor(color))
                c.rect(x, row_y - _CHIP_SIZE, _CHIP_SIZE, _CHIP_SIZE, fill=1, stroke=0)

                c.setFillColor(HexColor("#000000"))
                c.setFont(_LABEL_FONT, _LABEL_SIZE)
                c.drawString(
                    x + _CHIP_SIZE + 4, row_y - _CHIP_SIZE + 2, str(item.get("label", ""))
                )


__all__ = ["LegendFlowable"]
