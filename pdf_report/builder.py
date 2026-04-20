"""Pure compose function: turns capture specs + image bytes into a PDF.

No Solara imports, no browser dependencies. Unit-testable in isolation.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .legend import LegendFlowable
from .models import (
    CaptureSpec,
    EChartCapture,
    LegendCapture,
    MapCapture,
    PdfReportConfig,
    StatsTableCapture,
)

# Reportlab's hard page-size limit is about 200 inches ≈ 5080 mm.
# Stay comfortably under that; fall back to A4 multipage beyond.
_MAX_SINGLE_PAGE_HEIGHT_MM = 4800.0


def _styles() -> tuple[ParagraphStyle, ParagraphStyle, ParagraphStyle, ParagraphStyle]:
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "PdfReportTitle",
        parent=base["Heading1"],
        fontSize=18,
        leading=22,
        spaceAfter=4,
        alignment=TA_LEFT,
    )
    subtitle = ParagraphStyle(
        "PdfReportSubtitle",
        parent=base["Heading3"],
        fontSize=12,
        leading=14,
        spaceAfter=8,
        textColor=colors.HexColor("#555555"),
    )
    section = ParagraphStyle(
        "PdfReportSection",
        parent=base["Heading2"],
        fontSize=11,
        leading=13,
        spaceBefore=8,
        spaceAfter=4,
    )
    footer = ParagraphStyle(
        "PdfReportFooter",
        parent=base["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#888888"),
    )
    return title, subtitle, section, footer


def _metadata_table(metadata: tuple[tuple[str, str], ...], width_pt: float) -> Table | None:
    if not metadata:
        return None
    data = [[k, v] for k, v in metadata]
    t = Table(data, colWidths=[width_pt * 0.3, width_pt * 0.7])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def _stats_table(rows: tuple[tuple[str, str], ...], width_pt: float) -> Table:
    data = [[k, v] for k, v in rows]
    t = Table(data, colWidths=[width_pt * 0.5, width_pt * 0.5])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f3f3f3")]),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _scaled_image(
    png_bytes: bytes,
    target_width_pt: float,
    max_height_mm: float | None = None,
) -> Image:
    buf = io.BytesIO(png_bytes)
    img = Image(buf)
    orig_w = float(img.drawWidth) or 1.0
    orig_h = float(img.drawHeight) or 1.0
    aspect = orig_h / orig_w
    img.drawWidth = target_width_pt
    img.drawHeight = target_width_pt * aspect
    if max_height_mm is not None:
        cap = max_height_mm * mm
        if img.drawHeight > cap:
            scale = cap / img.drawHeight
            img.drawHeight = cap
            img.drawWidth = img.drawWidth * scale
    return img


def _flowables_for_capture(
    cap: CaptureSpec,
    image_bytes: dict[str, bytes],
    content_width_pt: float,
    section_style: ParagraphStyle,
) -> list:
    out: list = []

    if isinstance(cap, MapCapture):
        png = image_bytes.get(cap.selector)
        if png is None:
            raise ValueError(f"Missing image bytes for map selector {cap.selector!r}")
        if cap.label:
            out.append(Paragraph(cap.label, section_style))
        out.append(_scaled_image(png, content_width_pt, cap.height_mm))
        out.append(Spacer(1, 6))
        return out

    if isinstance(cap, EChartCapture):
        png = image_bytes.get(cap.selector)
        if png is None:
            if cap.optional:
                return out
            raise ValueError(f"Missing image bytes for echart selector {cap.selector!r}")
        if cap.label:
            out.append(Paragraph(cap.label, section_style))
        out.append(_scaled_image(png, content_width_pt))
        out.append(Spacer(1, 6))
        return out

    if isinstance(cap, LegendCapture):
        out.append(LegendFlowable(cap.legend_data, title=cap.title))
        out.append(Spacer(1, 6))
        return out

    if isinstance(cap, StatsTableCapture):
        if cap.title:
            out.append(Paragraph(cap.title, section_style))
        out.append(_stats_table(cap.rows, content_width_pt))
        out.append(Spacer(1, 6))
        return out

    raise TypeError(f"Unknown capture spec: {type(cap).__name__}")


def build_pdf_report(
    config: PdfReportConfig,
    captures: Iterable[CaptureSpec],
    image_bytes: dict[str, bytes],
) -> bytes:
    """Compose a single long-page PDF from capture specs + image bytes.

    Pure function. No Solara, no browser. Takes image bytes keyed by the
    selectors declared on the capture specs.
    """

    title_style, subtitle_style, section_style, footer_style = _styles()

    page_width_pt = config.page_width_mm * mm
    margin_pt = config.margin_mm * mm
    content_width_pt = page_width_pt - 2 * margin_pt

    flowables: list = [Paragraph(config.title, title_style)]
    if config.subtitle:
        flowables.append(Paragraph(config.subtitle, subtitle_style))

    meta = _metadata_table(config.metadata, content_width_pt)
    if meta is not None:
        flowables.append(meta)
        flowables.append(Spacer(1, 8))

    for cap in captures:
        flowables.extend(
            _flowables_for_capture(cap, image_bytes, content_width_pt, section_style)
        )

    footer_parts: list[str] = []
    if config.footer_text:
        footer_parts.append(config.footer_text)
    if config.include_timestamp:
        footer_parts.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    if footer_parts:
        flowables.append(Spacer(1, 8))
        flowables.append(Paragraph(" • ".join(footer_parts), footer_style))

    # Measure total height by asking each flowable to wrap itself.
    total_h = 0.0
    for fl in flowables:
        _w, h = fl.wrap(content_width_pt, 1_000_000)
        total_h += h

    page_height_pt = total_h + 2 * margin_pt
    max_height_pt = _MAX_SINGLE_PAGE_HEIGHT_MM * mm

    buf = io.BytesIO()
    if page_height_pt > max_height_pt:
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=margin_pt,
            rightMargin=margin_pt,
            topMargin=margin_pt,
            bottomMargin=margin_pt,
        )
    else:
        doc = SimpleDocTemplate(
            buf,
            pagesize=(page_width_pt, page_height_pt),
            leftMargin=margin_pt,
            rightMargin=margin_pt,
            topMargin=margin_pt,
            bottomMargin=margin_pt,
        )

    doc.build(flowables)
    return buf.getvalue()


__all__ = ["build_pdf_report"]
