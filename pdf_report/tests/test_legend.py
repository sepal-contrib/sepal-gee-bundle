"""Tests for LegendFlowable and color helpers."""

import io

import pytest
from reportlab.pdfgen import canvas as rl_canvas

from pdf_report.legend import (
    LegendFlowable,
    _hex_to_rgb,
    _sample_gradient,
)


class TestHexToRgb:
    def test_white(self):
        assert _hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_black(self):
        assert _hex_to_rgb("#000000") == (0, 0, 0)

    def test_with_and_without_hash(self):
        assert _hex_to_rgb("#ff8000") == _hex_to_rgb("ff8000") == (255, 128, 0)


class TestSampleGradient:
    def test_empty_returns_black(self):
        assert _sample_gradient([], 0.5) == "#000000"

    def test_single_color(self):
        assert _sample_gradient(["#112233"], 0.3) == "#112233"

    def test_endpoints_unchanged(self):
        colors = ["#000000", "#ffffff"]
        assert _sample_gradient(colors, 0.0) == "#000000"
        assert _sample_gradient(colors, 1.0) == "#ffffff"

    def test_midpoint_is_halfway(self):
        colors = ["#000000", "#ffffff"]
        mid = _sample_gradient(colors, 0.5)
        # interpolated gray: ~127/127/127
        assert mid.startswith("#7f") or mid.startswith("#80")

    def test_three_stops(self):
        colors = ["#000000", "#ff0000", "#ffffff"]
        assert _sample_gradient(colors, 0.0) == "#000000"
        assert _sample_gradient(colors, 0.5) == "#ff0000"
        assert _sample_gradient(colors, 1.0) == "#ffffff"


class TestLegendFlowable:
    def test_wrap_returns_positive_dims(self):
        data = {
            "gradients": [{"colors": ["#ff0", "#800"], "labels": ["2001", "2024"], "title": ""}],
            "items": [{"label": "Forest", "color": "#064"}, {"label": "Loss", "color": "#a22"}],
        }
        fl = LegendFlowable(data, title="Legend")
        w, h = fl.wrap(400, 9999)
        assert w == 400
        assert h > 0

    def test_draw_does_not_raise(self):
        data = {
            "gradients": [{"colors": ["#ff0", "#800"], "labels": ["2001", "2024"], "title": "Year"}],
            "items": [{"label": "Forest", "color": "#064"}],
        }
        fl = LegendFlowable(data, title="Legend")
        fl.wrap(400, 9999)
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=(400, 400))
        c.translate(0, 300)  # position like a platypus flowable
        fl.canv = c
        fl.draw()  # must not raise
        c.save()
        assert len(buf.getvalue()) > 0

    def test_empty_legend_still_draws(self):
        fl = LegendFlowable({}, title="Empty")
        fl.wrap(400, 9999)
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=(400, 400))
        c.translate(0, 300)
        fl.canv = c
        fl.draw()
        c.save()
