"""Tests for pdf_report capture-spec and config dataclasses."""

import pytest

from pdf_report.models import (
    EChartCapture,
    LegendCapture,
    MapCapture,
    PdfReportConfig,
    StatsTableCapture,
)


class TestMapCapture:
    def test_default_label_and_height(self):
        cap = MapCapture(selector=".my-map")
        assert cap.selector == ".my-map"
        assert cap.label == "Map"
        assert cap.height_mm is None

    def test_custom_fields(self):
        cap = MapCapture(selector=".m", label="Area of interest", height_mm=120.0)
        assert cap.label == "Area of interest"
        assert cap.height_mm == 120.0

    def test_empty_selector_rejected(self):
        with pytest.raises(ValueError, match="selector"):
            MapCapture(selector="")

    def test_is_frozen(self):
        cap = MapCapture(selector=".m")
        with pytest.raises((AttributeError, Exception)):
            cap.selector = ".other"


class TestEChartCapture:
    def test_defaults(self):
        cap = EChartCapture(selector=".chart")
        assert cap.label == ""
        assert cap.optional is False
        assert cap.pixel_ratio == 2

    def test_optional_flag(self):
        cap = EChartCapture(selector=".chart", optional=True)
        assert cap.optional is True

    def test_empty_selector_rejected(self):
        with pytest.raises(ValueError, match="selector"):
            EChartCapture(selector="")

    def test_pixel_ratio_floor(self):
        with pytest.raises(ValueError, match="pixel_ratio"):
            EChartCapture(selector=".c", pixel_ratio=0)


class TestLegendCapture:
    def test_construct(self):
        data = {"gradients": [], "items": []}
        cap = LegendCapture(legend_data=data)
        assert cap.legend_data is data
        assert cap.title == "Legend"

    def test_custom_title(self):
        cap = LegendCapture(legend_data={}, title="Forest change")
        assert cap.title == "Forest change"


class TestStatsTableCapture:
    def test_construct(self):
        cap = StatsTableCapture(rows=(("a", "1"), ("b", "2")))
        assert cap.rows == (("a", "1"), ("b", "2"))
        assert cap.title == ""


class TestPdfReportConfig:
    def test_minimal(self):
        cfg = PdfReportConfig(title="Report")
        assert cfg.title == "Report"
        assert cfg.subtitle == ""
        assert cfg.metadata == ()
        assert cfg.page_width_mm == 210.0
        assert cfg.margin_mm == 15.0
        assert cfg.include_timestamp is True

    def test_metadata_tuple(self):
        cfg = PdfReportConfig(
            title="T",
            metadata=(("Year", "2024"), ("Area", "1.2 Mha")),
        )
        assert cfg.metadata == (("Year", "2024"), ("Area", "1.2 Mha"))
