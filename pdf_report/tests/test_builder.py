"""Tests for build_pdf_report — pure compose function, no Solara/browser."""

import io

import pypdf
import pytest

from pdf_report.builder import build_pdf_report
from pdf_report.models import (
    EChartCapture,
    LegendCapture,
    MapCapture,
    PdfReportConfig,
    StatsTableCapture,
)


def _tiny_png() -> bytes:
    """Return a valid 2x2 RGB PNG as raw bytes, generated via Pillow."""
    from PIL import Image as PILImage

    img = PILImage.new("RGB", (2, 2), color=(255, 255, 255))
    img.putpixel((0, 0), (0, 0, 0))
    img.putpixel((1, 1), (0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_config() -> PdfReportConfig:
    return PdfReportConfig(
        title="Basin Rivers — Watershed Report",
        subtitle="Upstream delineation & forest change",
        metadata=(
            ("Outlet", "12.3456, -56.7890"),
            ("Year range", "2010-2024"),
            ("Tree cover threshold", "80%"),
        ),
    )


@pytest.fixture
def sample_captures():
    return [
        MapCapture(selector=".my-map", label="Map view"),
        LegendCapture(
            legend_data={
                "gradients": [{"colors": ["#ff0", "#800"], "labels": ["2001", "2024"], "title": ""}],
                "items": [{"label": "Forest", "color": "#064"}],
            },
            title="Legend",
        ),
        StatsTableCapture(
            title="Summary",
            rows=(("Stable forest", "120 ha"), ("Forest loss", "45 ha")),
        ),
        EChartCapture(selector=".chart-a", label="Chart A"),
        EChartCapture(selector=".chart-b", label="Chart B", optional=True),
    ]


def _images_for(selectors: list[str]) -> dict[str, bytes]:
    png = _tiny_png()
    return {s: png for s in selectors}


class TestBuildPdfReport:
    def test_returns_pdf_bytes(self, sample_config, sample_captures):
        images = _images_for([".my-map", ".chart-a", ".chart-b"])
        pdf_bytes = build_pdf_report(sample_config, sample_captures, images)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")

    def test_pdf_is_readable_and_has_pages(self, sample_config, sample_captures):
        images = _images_for([".my-map", ".chart-a", ".chart-b"])
        pdf_bytes = build_pdf_report(sample_config, sample_captures, images)
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1

    def test_text_content_includes_title_and_metadata(self, sample_config, sample_captures):
        images = _images_for([".my-map", ".chart-a", ".chart-b"])
        pdf_bytes = build_pdf_report(sample_config, sample_captures, images)
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "Basin Rivers" in text
        assert "Upstream delineation" in text
        assert "Outlet" in text
        assert "Year range" in text
        assert "Map view" in text
        assert "Chart A" in text
        assert "Summary" in text
        assert "Stable forest" in text

    def test_optional_echart_missing_is_skipped(self, sample_config, sample_captures):
        # Only provide images for the map + non-optional chart
        images = _images_for([".my-map", ".chart-a"])
        pdf_bytes = build_pdf_report(sample_config, sample_captures, images)
        assert pdf_bytes.startswith(b"%PDF-")
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "Chart A" in text
        assert "Chart B" not in text

    def test_missing_required_map_raises(self, sample_config, sample_captures):
        images = _images_for([".chart-a", ".chart-b"])  # no map
        with pytest.raises(ValueError, match="selector"):
            build_pdf_report(sample_config, sample_captures, images)

    def test_missing_required_echart_raises(self, sample_config):
        cap = [
            MapCapture(selector=".m"),
            EChartCapture(selector=".c"),  # not optional, but no bytes
        ]
        images = {".m": _tiny_png()}
        with pytest.raises(ValueError, match="selector"):
            build_pdf_report(sample_config, cap, images)

    def test_footer_timestamp_present(self, sample_config, sample_captures):
        images = _images_for([".my-map", ".chart-a", ".chart-b"])
        pdf_bytes = build_pdf_report(sample_config, sample_captures, images)
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "UTC" in text
        assert "SEPAL" in text

    def test_tall_content_falls_back_to_a4_multipage(self):
        # Config that would overflow the single-page cap
        cfg = PdfReportConfig(title="Overflow")
        # 200 tiny stats tables → tall content
        captures = [
            StatsTableCapture(title=f"S{i}", rows=(("k", "v"),) * 50)
            for i in range(200)
        ]
        pdf_bytes = build_pdf_report(cfg, captures, {})
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 2
