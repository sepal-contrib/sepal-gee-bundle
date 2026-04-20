"""Dataclasses for PDF report captures and config.

These are frozen, slotted, pure dataclasses with no runtime dependencies
on Solara, reportlab, or the browser. They describe what to capture and
how to render the report; the actual image bytes arrive later from the
browser capture pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True, slots=True)
class MapCapture:
    """Capture the live view of an ipyleaflet map via html2canvas."""

    selector: str
    label: str = "Map"
    height_mm: float | None = None

    def __post_init__(self) -> None:
        if not self.selector:
            raise ValueError("MapCapture.selector must be non-empty")


@dataclass(frozen=True, slots=True)
class EChartCapture:
    """Capture an ECharts widget via echarts.getInstanceByDom().getDataURL()."""

    selector: str
    label: str = ""
    optional: bool = False
    pixel_ratio: int = 2

    def __post_init__(self) -> None:
        if not self.selector:
            raise ValueError("EChartCapture.selector must be non-empty")
        if self.pixel_ratio < 1:
            raise ValueError("EChartCapture.pixel_ratio must be >= 1")


@dataclass(frozen=True, slots=True)
class LegendCapture:
    """Render a legend natively (vector) in the PDF from LegendData.

    Uses the same dict shape produced by ``dataclasses.asdict(LegendData)``
    from ``pysepal.solara.components.legend``. No DOM capture.
    """

    legend_data: dict
    title: str = "Legend"


@dataclass(frozen=True, slots=True)
class StatsTableCapture:
    """Render a two-column key/value table natively in the PDF."""

    rows: tuple[tuple[str, str], ...]
    title: str = ""


CaptureSpec = Union[MapCapture, EChartCapture, LegendCapture, StatsTableCapture]


@dataclass(frozen=True, slots=True)
class PdfReportConfig:
    """Top-level config for a PDF report (non-image content)."""

    title: str
    subtitle: str = ""
    metadata: tuple[tuple[str, str], ...] = ()
    page_width_mm: float = 210.0
    margin_mm: float = 15.0
    footer_text: str = "Generated via SEPAL • sepal.io"
    include_timestamp: bool = True


__all__ = [
    "CaptureSpec",
    "EChartCapture",
    "LegendCapture",
    "MapCapture",
    "PdfReportConfig",
    "StatsTableCapture",
]
