# PdfReportButton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable `PdfReportButton` Solara component in pysepal that captures a live ipyleaflet map + ECharts widgets in the browser and composes a single long-page PDF in Python with reportlab, and wire it into the basin-rivers dashboard modal as the first consumer.

**Architecture:** Hybrid client/server. Browser side (`html2canvas` loaded from CDN + ECharts native `getDataURL`) captures images and posts them back to Python via a Vuetify-template traitlet. Python side (`reportlab`) composes a PDF, base64-encodes it, pushes it back to the template which triggers an anchor-click download. Legend is re-drawn natively (vector) in Python from the same `LegendData` dataclass the Vue legend uses; no DOM capture for the legend.

**Tech Stack:** Python 3.12, Solara, reacton, ipyvuetify, traitlets, reportlab ≥4, pypdf (tests only), html2canvas 1.4.1 (client, CDN). Spec: `docs/superpowers/specs/2026-04-20-pdf-report-export-design.md`.

---

## File Structure

**pysepal repo** (`~/1_modules/pysepal/`):

- Modify: `pyproject.toml` — add `reportlab>=4,<5` to runtime deps; add `pypdf>=4` to `dev` extra.
- Create: `pysepal/solara/components/pdf_report/__init__.py` — public re-exports.
- Create: `pysepal/solara/components/pdf_report/models.py` — capture spec dataclasses + `PdfReportConfig`.
- Create: `pysepal/solara/components/pdf_report/legend.py` — `LegendFlowable` + color interpolation helpers.
- Create: `pysepal/solara/components/pdf_report/builder.py` — `build_pdf_report()` pure function.
- Create: `pysepal/solara/components/pdf_report/button.py` — `PdfReportButton` Solara component + internal `_CaptureTemplate`.
- Create: `pysepal/solara/components/pdf_report/tests/__init__.py` — empty.
- Create: `pysepal/solara/components/pdf_report/tests/test_models.py`.
- Create: `pysepal/solara/components/pdf_report/tests/test_legend.py`.
- Create: `pysepal/solara/components/pdf_report/tests/test_builder.py`.
- Create: `pysepal/solara/components/pdf_report/tests/test_button.py`.

**sepal-gee-bundle repo** (`~/1_modules/sepal-gee-bundle/`):

- Modify: `apps/basin_rivers/components/dashboard/overall_pie.py` — wrap chart in a div with class `br-echart-overall`.
- Modify: `apps/basin_rivers/components/dashboard/catchment_pie.py` — wrap with class `br-echart-catchment-pie`.
- Modify: `apps/basin_rivers/components/dashboard/catchment_bar.py` — wrap with class `br-echart-catchment-bar`.
- Modify: `apps/basin_rivers/components/dashboard/loss_trend.py` — wrap with class `br-echart-loss-trend`.
- Modify: `apps/basin_rivers/components/delineation_step.py` — forward `legend_data` reactive to `DashboardStep`.
- Modify: `apps/basin_rivers/components/dashboard_step.py` — accept `legend_data`, render `PdfReportButton` in the modal next to the CSV download.
- Modify: `apps/basin_rivers/CLAUDE.md` — append a short "PDF export" section with the manual smoke test.

No bundle `pyproject.toml` changes: `reportlab` and `pypdf` become transitive deps via the pysepal install.

---

## Task 1: Add dependencies and verify install

**Files:**
- Modify: `/home/dguerrero/1_modules/pysepal/pyproject.toml`

- [ ] **Step 1: Add `reportlab` to pysepal runtime deps**

Edit `/home/dguerrero/1_modules/pysepal/pyproject.toml`. Inside the `[project] dependencies = [...]` list, add one entry at the end of the existing list (just before the closing `]`):

```toml
    "reportlab>=4,<5",
```

- [ ] **Step 2: Add `pypdf` to pysepal `dev` extra**

In the same file, inside `[project.optional-dependencies].dev = [...]`, add:

```toml
    "pypdf>=4",
```

- [ ] **Step 3: Install the deps in the conda env**

Run:

```bash
conda run -n sepal-gee-bundle pip install -e "/home/dguerrero/1_modules/pysepal[dev]"
```

Expected: pip resolves and installs `reportlab` and `pypdf` without errors. If `reportlab` needs a compiler on this platform it will use a prebuilt wheel; no extra system deps required on Ubuntu x86_64.

- [ ] **Step 4: Verify both imports**

Run:

```bash
conda run -n sepal-gee-bundle python -c "import reportlab, pypdf; print(reportlab.Version, pypdf.__version__)"
```

Expected: prints a reportlab version starting with `4.` and a pypdf version starting with `4.` or `5.`, on one line, with no traceback.

- [ ] **Step 5: Commit**

```bash
cd /home/dguerrero/1_modules/pysepal
git add pyproject.toml
git commit -m "feat(pdf-report): add reportlab runtime dep, pypdf dev dep"
```

---

## Task 2: Scaffold the `pdf_report` package

**Files:**
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/__init__.py`
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/models.py` (empty)
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/legend.py` (empty)
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/builder.py` (empty)
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/button.py` (empty)
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/__init__.py` (empty)

- [ ] **Step 1: Create the package directory**

```bash
mkdir -p /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests
```

- [ ] **Step 2: Create empty stub files**

Create six empty files at the paths above. The package `__init__.py` starts as a single docstring:

`/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/__init__.py`:

```python
"""Reusable PDF report export for pysepal Solara apps.

Captures the live ipyleaflet map (via html2canvas) and ECharts widgets
(via getDataURL) in the browser, and composes a single long-page PDF in
Python with reportlab. Legends are re-drawn natively (vector) from the
same LegendData dataclass used by LegendComponent — no DOM capture for
the legend.

Public API is re-exported here; see the submodules for implementation.
"""
```

The other five files (`models.py`, `legend.py`, `builder.py`, `button.py`, `tests/__init__.py`) start empty. They will be filled in the following tasks.

- [ ] **Step 3: Verify the package is importable**

```bash
conda run -n sepal-gee-bundle python -c "import pysepal.solara.components.pdf_report; print('ok')"
```

Expected: prints `ok` with no traceback.

- [ ] **Step 4: Commit**

```bash
cd /home/dguerrero/1_modules/pysepal
git add pysepal/solara/components/pdf_report/
git commit -m "feat(pdf-report): scaffold pdf_report package"
```

---

## Task 3: Implement `models.py` (dataclasses)

**Files:**
- Create (contents): `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/models.py`
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Write `tests/test_models.py`:

```python
"""Tests for pdf_report capture-spec and config dataclasses."""

import pytest

from pysepal.solara.components.pdf_report.models import (
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_models.py -v
```

Expected: all tests fail with `ImportError` or `ModuleNotFoundError` because `models.py` is empty.

- [ ] **Step 3: Implement `models.py`**

Write to `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/models.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_models.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/dguerrero/1_modules/pysepal
git add pysepal/solara/components/pdf_report/models.py pysepal/solara/components/pdf_report/tests/test_models.py
git commit -m "feat(pdf-report): capture spec + PdfReportConfig dataclasses"
```

---

## Task 4: Implement `legend.py` (native vector legend Flowable)

**Files:**
- Create (contents): `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/legend.py`
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_legend.py`

- [ ] **Step 1: Write the failing tests**

Write `tests/test_legend.py`:

```python
"""Tests for LegendFlowable and color helpers."""

import io

import pytest
from reportlab.pdfgen import canvas as rl_canvas

from pysepal.solara.components.pdf_report.legend import (
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_legend.py -v
```

Expected: all tests fail with `ImportError`.

- [ ] **Step 3: Implement `legend.py`**

Write to `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/legend.py`:

```python
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
    """Parse a ``#rrggbb`` or ``rrggbb`` string into a 0-255 RGB tuple."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


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

                color = item.get("color") or "#000000"
                c.setFillColor(HexColor(color))
                c.rect(x, row_y - _CHIP_SIZE, _CHIP_SIZE, _CHIP_SIZE, fill=1, stroke=0)

                c.setFillColor(HexColor("#000000"))
                c.setFont(_LABEL_FONT, _LABEL_SIZE)
                c.drawString(x + _CHIP_SIZE + 4, row_y - _CHIP_SIZE + 2, str(item.get("label", "")))


__all__ = ["LegendFlowable"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_legend.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/dguerrero/1_modules/pysepal
git add pysepal/solara/components/pdf_report/legend.py pysepal/solara/components/pdf_report/tests/test_legend.py
git commit -m "feat(pdf-report): LegendFlowable with native vector gradients and chips"
```

---

## Task 5: Implement `builder.py` (pure compose function)

**Files:**
- Create (contents): `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/builder.py`
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_builder.py`

- [ ] **Step 1: Write the failing tests**

Write `tests/test_builder.py`:

```python
"""Tests for build_pdf_report — pure compose function, no Solara/browser."""

import io

import pypdf
import pytest

from pysepal.solara.components.pdf_report.builder import build_pdf_report
from pysepal.solara.components.pdf_report.models import (
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_builder.py -v
```

Expected: all tests fail with `ImportError`.

- [ ] **Step 3: Implement `builder.py`**

Write to `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/builder.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_builder.py -v
```

Expected: all tests pass. If `test_tall_content_falls_back_to_a4_multipage` is slow (>5s), that's acceptable — it's intentionally building a large document.

- [ ] **Step 5: Commit**

```bash
cd /home/dguerrero/1_modules/pysepal
git add pysepal/solara/components/pdf_report/builder.py pysepal/solara/components/pdf_report/tests/test_builder.py
git commit -m "feat(pdf-report): build_pdf_report compose function with single long-page + A4 fallback"
```

---

## Task 6: Implement `button.py` (Solara component + capture template)

**Files:**
- Create (contents): `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/button.py`
- Create: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_button.py`

Button testing is shallow by design — the capture flow is JS + browser, not directly unit-testable. The test just asserts the module imports cleanly and that the helper that serializes capture specs behaves correctly.

- [ ] **Step 1: Write the failing test**

Write `tests/test_button.py`:

```python
"""Import + helper tests for PdfReportButton.

The browser capture flow (html2canvas + ECharts getDataURL) is not
covered here — it's exercised via the per-app manual smoke test.
"""

import json

import pytest


def test_module_imports():
    from pysepal.solara.components.pdf_report.button import PdfReportButton  # noqa: F401


def test_serialize_capture_specs_map_and_echart():
    from pysepal.solara.components.pdf_report.button import _serialize_capture_specs
    from pysepal.solara.components.pdf_report.models import (
        EChartCapture,
        LegendCapture,
        MapCapture,
        StatsTableCapture,
    )

    captures = [
        MapCapture(selector=".m"),
        EChartCapture(selector=".c1", optional=False, pixel_ratio=2),
        EChartCapture(selector=".c2", optional=True, pixel_ratio=3),
        LegendCapture(legend_data={}),   # native; not serialized
        StatsTableCapture(rows=()),       # native; not serialized
    ]
    payload = json.loads(_serialize_capture_specs(captures))
    assert payload == [
        {"kind": "map", "selector": ".m"},
        {"kind": "echart", "selector": ".c1", "optional": False, "pixel_ratio": 2},
        {"kind": "echart", "selector": ".c2", "optional": True, "pixel_ratio": 3},
    ]


def test_decode_image_map_strips_data_url_prefix_and_sentinels():
    import base64

    from pysepal.solara.components.pdf_report.button import _decode_image_map

    raw = b"hello"
    b64 = base64.b64encode(raw).decode("ascii")
    captured = {
        ".x": f"data:image/png;base64,{b64}",
        ".y": b64,  # without prefix
        "__error__": "nope",
    }
    out = _decode_image_map(captured)
    assert out == {".x": raw, ".y": raw}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_button.py -v
```

Expected: all tests fail with `ImportError`.

- [ ] **Step 3: Implement `button.py`**

Write to `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/button.py`:

```python
"""PdfReportButton — Solara trigger for the pdf_report capture pipeline.

Flow:
    click → set building=True and bump a capture ``tick``
         → a hidden VuetifyTemplate lazy-loads html2canvas, walks the
           capture spec list, writes a ``{selector: dataURL}`` dict
           into ``captured_images`` traitlet
         → a solara.use_effect sees the dict change, base64-decodes it,
           calls build_pdf_report(), base64-encodes the result, and sets
           a ``pdf_base64`` + ``download_tick`` pair on the template
         → the template's JS watcher on ``download_tick`` creates a
           Blob anchor and auto-clicks it to download the PDF.

Error surface: any failure in the JS phase writes ``__error__`` into
``captured_images``; Python surfaces the message via the pysepal
notification system if present, else via the module logger.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Sequence

import ipyvuetify as ipv
import reacton.ipyvuetify as rv
import solara
from traitlets import Dict, Int, Unicode

from pysepal.solara.notifications import use_notifications
from pysepal.solara.notifications.notifier import NoopNotifier

from .builder import build_pdf_report
from .models import (
    CaptureSpec,
    EChartCapture,
    MapCapture,
    PdfReportConfig,
)

log = logging.getLogger(__name__)

_HTML2CANVAS_URL = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"

_CAPTURE_TEMPLATE = """
<script class="pdf-report-capture">
{
    data() {
        return { _pysepal_busy: false };
    },
    watch: {
        tick() { this._runCapture(); },
        download_tick() { this._triggerDownload(); }
    },
    methods: {
        _loadHtml2Canvas() {
            if (window.html2canvas) return Promise.resolve(window.html2canvas);
            if (window.__pysepal_h2c_promise__) return window.__pysepal_h2c_promise__;
            window.__pysepal_h2c_promise__ = new Promise((resolve, reject) => {
                const s = document.createElement('script');
                s.src = '__H2C_URL__';
                s.onload = () => resolve(window.html2canvas);
                s.onerror = () => reject(new Error('failed to load html2canvas'));
                document.head.appendChild(s);
            });
            return window.__pysepal_h2c_promise__;
        },
        async _waitForTiles(root, timeoutMs) {
            const deadline = Date.now() + timeoutMs;
            while (Date.now() < deadline) {
                const tiles = root.querySelectorAll('.leaflet-tile');
                const loaded = root.querySelectorAll('.leaflet-tile-loaded');
                if (tiles.length === 0) return;
                if (loaded.length === tiles.length) return;
                await new Promise(r => setTimeout(r, 150));
            }
        },
        async _withTimeout(p, ms, label) {
            let to;
            const timeout = new Promise((_, reject) => {
                to = setTimeout(() => reject(new Error(label + ' timed out')), ms);
            });
            try { return await Promise.race([p, timeout]); }
            finally { clearTimeout(to); }
        },
        async _captureMap(spec) {
            const h2c = await this._loadHtml2Canvas();
            const el = document.querySelector(spec.selector);
            if (!el) throw new Error('selector not found: ' + spec.selector);
            await this._waitForTiles(el, 5000);
            const canvas = await this._withTimeout(
                h2c(el, { useCORS: true, backgroundColor: '#ffffff', scale: 2, logging: false }),
                15000,
                'map capture ' + spec.selector
            );
            return canvas.toDataURL('image/png');
        },
        async _findEchartsInstance(el) {
            const deadline = Date.now() + 500;
            while (Date.now() < deadline) {
                if (window.echarts) {
                    let inst = window.echarts.getInstanceByDom(el);
                    if (!inst) {
                        const child = el.querySelector('[_echarts_instance_]');
                        if (child) inst = window.echarts.getInstanceByDom(child);
                    }
                    if (inst) return inst;
                }
                await new Promise(r => setTimeout(r, 50));
            }
            return null;
        },
        async _captureEchart(spec) {
            const el = document.querySelector(spec.selector);
            if (!el) {
                if (spec.optional) return null;
                throw new Error('selector not found: ' + spec.selector);
            }
            const inst = await this._findEchartsInstance(el);
            if (!inst) {
                if (spec.optional) return null;
                throw new Error('ECharts instance not found for selector: ' + spec.selector);
            }
            return inst.getDataURL({
                pixelRatio: spec.pixel_ratio || 2,
                backgroundColor: '#ffffff',
            });
        },
        async _runCapture() {
            if (this._pysepal_busy) return;
            this._pysepal_busy = true;
            let specs = [];
            try { specs = JSON.parse(this.capture_specs || '[]'); }
            catch (_e) { specs = []; }
            const results = {};
            try {
                for (const spec of specs) {
                    let url = null;
                    if (spec.kind === 'map') url = await this._captureMap(spec);
                    else if (spec.kind === 'echart') url = await this._captureEchart(spec);
                    if (url) results[spec.selector] = url;
                }
                this.captured_images = results;
            } catch (e) {
                this.captured_images = { __error__: String(e && e.message || e) };
            } finally {
                this._pysepal_busy = false;
            }
        },
        _triggerDownload() {
            const b64 = this.pdf_base64;
            if (!b64) return;
            const link = document.createElement('a');
            link.href = 'data:application/pdf;base64,' + b64;
            link.download = this.filename || 'report.pdf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
}
</script>
""".replace("__H2C_URL__", _HTML2CANVAS_URL)


class _CaptureTemplate(ipv.VuetifyTemplate):
    tick = Int(0).tag(sync=True)
    capture_specs = Unicode("[]").tag(sync=True)
    captured_images = Dict({}).tag(sync=True)
    pdf_base64 = Unicode("").tag(sync=True)
    download_tick = Int(0).tag(sync=True)
    filename = Unicode("report.pdf").tag(sync=True)
    template = Unicode(_CAPTURE_TEMPLATE).tag(sync=True)


def _serialize_capture_specs(captures: Sequence[CaptureSpec]) -> str:
    """Serialize only the capture specs that need browser-side capture."""
    payload: list[dict] = []
    for c in captures:
        if isinstance(c, MapCapture):
            payload.append({"kind": "map", "selector": c.selector})
        elif isinstance(c, EChartCapture):
            payload.append(
                {
                    "kind": "echart",
                    "selector": c.selector,
                    "optional": c.optional,
                    "pixel_ratio": c.pixel_ratio,
                }
            )
        # LegendCapture / StatsTableCapture are rendered natively; not serialized.
    return json.dumps(payload)


def _decode_image_map(captured: dict[str, str]) -> dict[str, bytes]:
    """Strip data-URL prefixes and base64-decode. Sentinel keys (``__*``) are dropped."""
    out: dict[str, bytes] = {}
    for sel, data_url in captured.items():
        if sel.startswith("__"):
            continue
        if not isinstance(data_url, str) or not data_url:
            continue
        b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        out[sel] = base64.b64decode(b64)
    return out


@solara.component
def PdfReportButton(
    filename: str,
    config: PdfReportConfig,
    captures: Sequence[CaptureSpec],
    label: str = "Download PDF",
    icon_name: str = "mdi-file-pdf-box",
    color: str = "primary",
    block: bool = False,
    small: bool = True,
    classes: Sequence[str] = (),
) -> None:
    """Render a button that captures map+charts and downloads a PDF."""

    building = solara.use_reactive(False)
    captured_state = solara.use_reactive({})
    captures_list = list(captures)

    capture_engine = solara.use_memo(lambda: _CaptureTemplate(), [])
    capture_engine.filename = filename
    capture_engine.capture_specs = _serialize_capture_specs(captures_list)

    notifications = use_notifications()
    has_notifications = not isinstance(notifications, NoopNotifier)

    def _notify_error(msg: str) -> None:
        if has_notifications:
            notifications.error(msg)
        log.error(msg)

    def _observe():
        def _on_change(change: dict) -> None:
            new = change.get("new") or {}
            captured_state.set(dict(new))

        capture_engine.observe(_on_change, names="captured_images")
        return lambda: capture_engine.unobserve(_on_change, names="captured_images")

    solara.use_effect(_observe, [])

    def _handle_captured() -> None:
        captured = captured_state.value or {}
        if not captured:
            return
        try:
            if "__error__" in captured:
                _notify_error(f"PDF capture failed: {captured['__error__']}")
                return
            image_bytes = _decode_image_map(captured)
            pdf_bytes = build_pdf_report(config, captures_list, image_bytes)
            capture_engine.pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
            capture_engine.download_tick = capture_engine.download_tick + 1
        except Exception as exc:  # noqa: BLE001 - user-facing error surface
            log.exception("PDF build failed")
            _notify_error(f"PDF build failed: {exc}")
        finally:
            building.set(False)
            captured_state.set({})
            capture_engine.captured_images = {}

    solara.use_effect(_handle_captured, [captured_state.value])

    def _start() -> None:
        if building.value:
            return
        building.set(True)
        capture_engine.tick = capture_engine.tick + 1

    solara.Button(
        label=label,
        icon_name=icon_name,
        on_click=_start,
        color=color,
        block=block,
        small=small,
        disabled=building.value,
        classes=list(classes),
    )

    rv.Html(tag="div", children=[capture_engine], style_="display:none;")


__all__ = ["PdfReportButton"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/test_button.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/dguerrero/1_modules/pysepal
git add pysepal/solara/components/pdf_report/button.py pysepal/solara/components/pdf_report/tests/test_button.py
git commit -m "feat(pdf-report): PdfReportButton Solara component + capture template"
```

---

## Task 7: Re-export public API from package `__init__.py`

**Files:**
- Modify: `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/__init__.py`

- [ ] **Step 1: Extend `__init__.py` with re-exports**

Open `/home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/__init__.py` and append (keeping the existing module docstring):

```python
from .builder import build_pdf_report
from .button import PdfReportButton
from .models import (
    CaptureSpec,
    EChartCapture,
    LegendCapture,
    MapCapture,
    PdfReportConfig,
    StatsTableCapture,
)

__all__ = [
    "CaptureSpec",
    "EChartCapture",
    "LegendCapture",
    "MapCapture",
    "PdfReportButton",
    "PdfReportConfig",
    "StatsTableCapture",
    "build_pdf_report",
]
```

- [ ] **Step 2: Verify the public API is importable**

```bash
conda run -n sepal-gee-bundle python -c "from pysepal.solara.components.pdf_report import PdfReportButton, PdfReportConfig, MapCapture, EChartCapture, LegendCapture, StatsTableCapture, build_pdf_report; print('ok')"
```

Expected: prints `ok` with no traceback.

- [ ] **Step 3: Run the full pdf_report test suite**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/ -v
```

Expected: all tests (models + legend + builder + button) pass.

- [ ] **Step 4: Commit**

```bash
cd /home/dguerrero/1_modules/pysepal
git add pysepal/solara/components/pdf_report/__init__.py
git commit -m "feat(pdf-report): re-export public API from package __init__"
```

---

## Task 8: Tag basin-rivers dashboard chart divs with CSS classes

**Files:**
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard/overall_pie.py`
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard/catchment_pie.py`
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard/catchment_bar.py`
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard/loss_trend.py`

The `EChartsWidget.element(...)` return value is a reacton Element wrapping an ipywidget. Wrapping in `rv.Html(tag="div", class_="br-echart-...", children=[...])` gives the capture selector a stable hook, and the inner widget still mounts normally.

- [ ] **Step 1: Modify `overall_pie.py`**

Open `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard/overall_pie.py`. Find the final `EChartsWidget.element(...)` call (the last statement in the `OverallPie` component) and wrap it in an `rv.Html` with a CSS class.

Before:

```python
    EChartsWidget.element(option=option, theme=theme, style={"height": "340px", "width": "100%"})
```

After:

```python
    import reacton.ipyvuetify as rv  # add at top of file if not already imported

    with rv.Html(tag="div", class_="br-echart-overall", style_="width:100%;"):
        EChartsWidget.element(
            option=option, theme=theme, style={"height": "340px", "width": "100%"}
        )
```

If `reacton.ipyvuetify as rv` is already imported, do not re-import. Move the `import` to the existing import block at the top of the file.

- [ ] **Step 2: Modify `catchment_pie.py`**

Same pattern. Wrap the final `EChartsWidget.element(...)` in `with rv.Html(tag="div", class_="br-echart-catchment-pie", style_="width:100%;"): ...`. Add the `reacton.ipyvuetify as rv` import if missing (it is — the file currently has no rv import).

- [ ] **Step 3: Modify `catchment_bar.py`**

Same pattern with class `br-echart-catchment-bar`.

- [ ] **Step 4: Modify `loss_trend.py`**

Same pattern with class `br-echart-loss-trend`.

- [ ] **Step 5: Run basin-rivers app and verify charts still render**

Start the app:

```bash
conda run -n sepal-gee-bundle solara run /home/dguerrero/1_modules/sepal-gee-bundle/app.py --port 8767 --no-open
```

Open `http://localhost:8767/basin-rivers` in a browser. Run a watershed (pick a pour point, trace, compute stats, open dashboard). Verify: all charts render as before. In DevTools Elements panel, confirm each chart's container has the expected class (`br-echart-overall`, `br-echart-catchment-pie`, `br-echart-catchment-bar`, `br-echart-loss-trend` when loss is selected). Stop the server with Ctrl-C.

- [ ] **Step 6: Commit**

```bash
cd /home/dguerrero/1_modules/sepal-gee-bundle
git add apps/basin_rivers/components/dashboard/overall_pie.py \
        apps/basin_rivers/components/dashboard/catchment_pie.py \
        apps/basin_rivers/components/dashboard/catchment_bar.py \
        apps/basin_rivers/components/dashboard/loss_trend.py
git commit -m "feat(basin_rivers): CSS class hooks on dashboard charts for PDF capture"
```

---

## Task 9: Thread `legend_data` into `DashboardStep`

**Files:**
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/delineation_step.py` (line ~332)
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard_step.py` (component signature + prop flow)

`DelineationStep` already receives `legend_data` from `page.py` but only forwards `legend_visible` to `DashboardStep`. The `PdfReportButton` in the dashboard needs the current legend data to build a `LegendCapture`.

- [ ] **Step 1: Forward `legend_data` from `DelineationStep` to `DashboardStep`**

In `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/delineation_step.py`, find the final line inside the outermost `with solara.Column()` block:

Before:

```python
            DashboardStep(state, theme_toggle, legend_visible)
```

After:

```python
            DashboardStep(state, theme_toggle, legend_visible, legend_data)
```

- [ ] **Step 2: Accept `legend_data` in `DashboardStep`**

In `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard_step.py`, extend the component signature.

Before:

```python
@solara.component
def DashboardStep(state, theme_toggle, legend_visible=None):
```

After:

```python
@solara.component
def DashboardStep(state, theme_toggle, legend_visible=None, legend_data=None):
```

- [ ] **Step 3: Thread `legend_data` into `_DashboardContent`**

Still in `dashboard_step.py`, find the call inside the dialog body:

Before:

```python
                _DashboardContent(state, theme_toggle)
```

After:

```python
                _DashboardContent(state, theme_toggle, legend_data)
```

And extend `_DashboardContent`'s signature:

Before:

```python
@solara.component
def _DashboardContent(state, theme_toggle):
```

After:

```python
@solara.component
def _DashboardContent(state, theme_toggle, legend_data=None):
```

- [ ] **Step 4: Smoke-verify the app still runs**

```bash
conda run -n sepal-gee-bundle solara run /home/dguerrero/1_modules/sepal-gee-bundle/app.py --port 8767 --no-open
```

Open `http://localhost:8767/basin-rivers`, run a full workflow, open dashboard. No visible change yet — we've only threaded the prop. The dashboard should render identically. Stop the server.

- [ ] **Step 5: Commit**

```bash
cd /home/dguerrero/1_modules/sepal-gee-bundle
git add apps/basin_rivers/components/delineation_step.py \
        apps/basin_rivers/components/dashboard_step.py
git commit -m "feat(basin_rivers): thread legend_data reactive into DashboardStep"
```

---

## Task 10: Add `PdfReportButton` to the dashboard modal

**Files:**
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/components/dashboard_step.py` (imports, `_DashboardContent` body)
- Modify: `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/CLAUDE.md` (short "PDF export" section)

- [ ] **Step 1: Add imports**

At the top of `dashboard_step.py`, after the existing imports:

```python
from pysepal.solara.components.pdf_report import (
    EChartCapture,
    LegendCapture,
    MapCapture,
    PdfReportButton,
    PdfReportConfig,
    StatsTableCapture,
)
```

- [ ] **Step 2: Thread `sepal_map` into `DashboardStep`**

The button needs the map's unique CSS class (`sepal_map._id`). Currently `DashboardStep` does not receive the map. Update its signature to accept it, and update the caller in `delineation_step.py`.

In `dashboard_step.py`:

Before:

```python
@solara.component
def DashboardStep(state, theme_toggle, legend_visible=None, legend_data=None):
```

After:

```python
@solara.component
def DashboardStep(state, theme_toggle, legend_visible=None, legend_data=None, sepal_map=None):
```

And in the caller (`delineation_step.py`), update the call inside the Column block:

Before:

```python
            DashboardStep(state, theme_toggle, legend_visible, legend_data)
```

After:

```python
            DashboardStep(state, theme_toggle, legend_visible, legend_data, sepal_map)
```

Also thread `sepal_map` into `_DashboardContent` from the dialog body.

Before:

```python
                _DashboardContent(state, theme_toggle, legend_data)
```

After:

```python
                _DashboardContent(state, theme_toggle, legend_data, sepal_map)
```

Extend `_DashboardContent`'s signature:

Before:

```python
@solara.component
def _DashboardContent(state, theme_toggle, legend_data=None):
```

After:

```python
@solara.component
def _DashboardContent(state, theme_toggle, legend_data=None, sepal_map=None):
```

- [ ] **Step 3: Render the `PdfReportButton` next to the CSV download**

In `_DashboardContent`, find the final row that contains the `solara.FileDownload` for CSV:

Before:

```python
        with rv.Row(dense=True, class_="mt-3", justify="end"):
            with rv.Col(cols="auto"):
                solara.FileDownload(
                    data=lambda: _csv_bytes(state.zonal_df.value),
                    filename="basin_rivers_stats.csv",
                    mime_type="text/csv",
                    label="Download CSV",
                )
```

After:

```python
        with rv.Row(dense=True, class_="mt-3", justify="end"):
            with rv.Col(cols="auto"):
                solara.FileDownload(
                    data=lambda: _csv_bytes(state.zonal_df.value),
                    filename="basin_rivers_stats.csv",
                    mime_type="text/csv",
                    label="Download CSV",
                )
            with rv.Col(cols="auto"):
                if sepal_map is not None:
                    PdfReportButton(
                        filename="basin_rivers_report.pdf",
                        config=PdfReportConfig(
                            title="Basin Rivers — Watershed Report",
                            subtitle="Upstream delineation & forest change",
                            metadata=(
                                ("Outlet", f"{state.lat.value:.4f}, {state.lon.value:.4f}"
                                    if state.lat.value is not None and state.lon.value is not None
                                    else "—"),
                                ("HydroSHEDS level", str(state.level.value)),
                                ("Year range",
                                    f"{state.year_start.value}-{state.year_end.value}"),
                                ("Tree cover threshold", f"{state.treecover.value}%"),
                                ("Upstream basins", str(n_basins)),
                                ("Watershed area", _fmt_area(total_area)),
                                ("Stable forest",
                                    f"{_fmt_area(forest_area)} ({forest_pct:.1f}%)"),
                                ("Forest loss",
                                    f"{_fmt_area(loss_area)} ({loss_pct:.1f}%)"),
                            ),
                        ),
                        captures=(
                            MapCapture(selector=f".{sepal_map._id}", label="Map view"),
                            LegendCapture(
                                legend_data=(legend_data.value if legend_data is not None else {}),
                                title="Legend",
                            ),
                            StatsTableCapture(
                                title="Summary",
                                rows=(
                                    ("Stable forest",
                                        f"{_fmt_area(forest_area)} ({forest_pct:.1f}%)"),
                                    ("Forest loss",
                                        f"{_fmt_area(loss_area)} ({loss_pct:.1f}%)"),
                                ),
                            ),
                            EChartCapture(
                                selector=".br-echart-overall", label="Forest composition"
                            ),
                            EChartCapture(
                                selector=".br-echart-catchment-pie",
                                label="Per-catchment share",
                            ),
                            EChartCapture(
                                selector=".br-echart-catchment-bar",
                                label="Per-catchment breakdown",
                            ),
                            EChartCapture(
                                selector=".br-echart-loss-trend",
                                label="Loss over time",
                                optional=True,
                            ),
                        ),
                        label="Download PDF",
                    )
```

(The `if state.lat.value is not None and ...` ternary inside the metadata tuple keeps the tuple constant even if the user got here through an unusual path; the current wiring guarantees non-None, but this avoids a crash if assumptions change.)

- [ ] **Step 4: Manual smoke test**

Start the app:

```bash
conda run -n sepal-gee-bundle solara run /home/dguerrero/1_modules/sepal-gee-bundle/app.py --port 8767 --no-open
```

Open `http://localhost:8767/basin-rivers`, run the full workflow (outlet → trace → stats → open dashboard), click **Download PDF**. Verify:

1. The button shows disabled state briefly, then a PDF is downloaded.
2. Open the PDF. It should contain, in order:
   - Title + subtitle.
   - A metadata block with Outlet / Year range / Upstream basins / Watershed area / …
   - The map image (tiles + upstream catchment polygon + outlet marker visible).
   - A native legend (gradient + chips, crisp vector).
   - The Summary stats table.
   - The four charts (or three, if loss-trend is not shown).
   - Footer with "SEPAL" + UTC timestamp.
3. Legend text remains crisp under PDF zoom (vector, not pixelated).
4. No errors in browser console, no errors in server log.

If capture fails with a CORS-related message, confirm that the current basemap is `CartoDB.DarkMatter` or `CartoDB.Positron` (both CORS-enabled) and that the GFC layer is visible (GEE tile server sets CORS headers). Stop the server.

- [ ] **Step 5: Document the smoke test in the app CLAUDE.md**

Append to `/home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/CLAUDE.md`:

```markdown
## PDF export

The dashboard modal's **Download PDF** button calls
`pysepal.solara.components.pdf_report.PdfReportButton`. It captures the live
map (via html2canvas) and each ECharts chart (via the native
`getDataURL()`), re-draws the legend natively in reportlab, and hands the
browser a PDF download.

### Smoke test

1. Start the app (`conda run -n sepal-gee-bundle solara run app.py --port 8767`).
2. Pick an outlet, trace watershed, compute stats, open dashboard.
3. Click **Download PDF**.
4. Open the PDF and verify:
   - Title, metadata block, map image with layers + marker, native legend,
     summary table, all four charts (three if loss-trend is hidden),
     footer with SEPAL + UTC timestamp.
   - Legend text is crisp (vector) under PDF zoom.

### Trap: capture selectors

The capture spec uses CSS selectors — `.br-echart-overall`, etc. — that
correspond to the `class_` on each chart's wrapper `rv.Html` div. If you
rename a chart wrapper class, update the corresponding `EChartCapture` in
`dashboard_step.py`. The map selector uses `sepal_map._id`, which is set
automatically by `SepalMap.__init__`.
```

- [ ] **Step 6: Commit**

```bash
cd /home/dguerrero/1_modules/sepal-gee-bundle
git add apps/basin_rivers/components/dashboard_step.py \
        apps/basin_rivers/components/delineation_step.py \
        apps/basin_rivers/CLAUDE.md
git commit -m "feat(basin_rivers): PDF report export from dashboard modal"
```

---

## Post-implementation verification

- [ ] **Full pysepal test suite for pdf_report**

```bash
conda run -n sepal-gee-bundle pytest /home/dguerrero/1_modules/pysepal/pysepal/solara/components/pdf_report/tests/ -v
```

Expected: all tests pass.

- [ ] **Bundle lint**

```bash
conda run -n sepal-gee-bundle ruff check /home/dguerrero/1_modules/sepal-gee-bundle/apps/basin_rivers/
```

Expected: no new violations.

- [ ] **pysepal lint**

```bash
cd /home/dguerrero/1_modules/pysepal && conda run -n sepal-gee-bundle ruff check pysepal/solara/components/pdf_report/
```

Expected: no violations.

---

## Spec coverage check

| Spec item | Task |
|---|---|
| reportlab runtime dep, pypdf dev dep | 1 |
| Package scaffold at `pysepal/solara/components/pdf_report/` | 2, 7 |
| `MapCapture` / `EChartCapture` / `LegendCapture` / `StatsTableCapture` / `PdfReportConfig` | 3 |
| `LegendFlowable` (native vector) + helpers | 4 |
| `build_pdf_report()` pure compose + A4 multipage fallback | 5 |
| `PdfReportButton` + capture template + one-round-trip JS flow | 6 |
| Public API re-exports | 7 |
| Basin-rivers chart CSS classes | 8 |
| `legend_data` threading to dashboard | 9 |
| Button wired into dashboard modal + smoke-test docs | 10 |

