# PdfReportButton — Reusable PDF Report Export for pysepal Solara Apps

**Date:** 2026-04-20
**Status:** Design
**Location:** `pysepal/solara/components/pdf_report/`
**First consumer:** `apps/basin_rivers` (dashboard modal)

## Purpose

A reusable Solara component that exports a one-shot PDF report from a running
pysepal map app. The report captures the **current state of the live
ipyleaflet map** (tiles, vector layers, markers) plus an arbitrary set of
ECharts widgets and textual metadata, and composes them into a **single long
page** PDF that the user downloads directly from the browser.

Designed to be dropped into any bundle app (basin-rivers, fcdm, gfc,
coverage-analysis, future apps) with minimal wiring — CSS classes on the
widgets to capture + a capture-spec list on the component.

## Non-goals

- **No server-side rendering** of the map (no tile fetching, no staticmap
  reconstruction). The browser captures what the user sees.
- **No headless browser dependency** (no playwright/chromium). Docker image
  size budget excludes that.
- **No live preview** of the PDF inside the app. Click-to-download only.
- **No multi-template / branded PDF themes.** One default layout (header +
  map + legend + stats + charts + footer), parameterized by text and data.
- **No streaming or async queue.** The build is synchronous and small
  (seconds); no progress bar beyond a spinner on the trigger button.
- **No persistence of PDFs to SEPAL workspace or Drive** in v1. Browser
  download only. A future `PdfReportExportTarget` could reuse the existing
  `export_engine` plumbing for that.

## Why Not Extend the Existing `export` Module

`pysepal/solara/components/export*.py` is scoped to **Earth Engine** result
exports (`ee.Image` / `ee.FeatureCollection` → GEE asset / Drive / SEPAL
workspace). It has nothing to say about client-side DOM capture, image
compositing, or PDF assembly. Overloading it with a second, structurally
different export modality would muddle its responsibilities. A new, focused
module is the right call.

## Why Not Pure Client-side (jsPDF) or HTML-only

- **Pure client-side with `jsPDF`** — laying out a multi-section PDF with
  pagination, native legend, and stats tables in JavaScript is painful and
  hard to unit-test. Python side already has `reportlab`, which handles
  pagination, vector drawing, and text layout cleanly.
- **HTML report** — zero deps but produces inconsistent page breaks across
  browsers when the user "Print → Save as PDF". A true PDF is what the user
  asked for.

## Dependency Changes

Runtime (added to bundle `pyproject.toml`):
- `reportlab>=4,<5` — ~3 MB, pure Python + prebuilt wheels for linux
  x86_64/arm64. No apt/conda packages needed.

Test-only (`dev` extra):
- `pypdf>=4` — tiny, for structural assertions on generated PDFs.

Client-side (loaded lazily at first click from cdnjs, cached thereafter):
- `html2canvas@1.4.1` — ~50 KB minified+gzipped. Captures live map DOM.

No npm/webpack/bundler changes. No new Vue components to ship. The capture
JS is a small inlined snippet in an `ipyvuetify.VuetifyTemplate`.

## Architecture

```
pysepal/solara/components/pdf_report/
├── __init__.py              # public re-exports
├── models.py                # dataclasses: PdfReportConfig, capture specs
├── button.py                # PdfReportButton Solara component + capture template
├── builder.py               # build_pdf_report(): pure function, bytes out
├── legend.py                # LegendFlowable for reportlab (native, vector)
└── tests/
    ├── test_builder.py      # feeds fixed images, asserts PDF structure via pypdf
    ├── test_legend.py       # LegendFlowable renders to a valid Drawing
    └── test_models.py       # dataclass validation
```

**Boundaries:**

- `models.py` and `builder.py` are **pure Python, no Solara imports**. They
  can be unit-tested in isolation with fixed PNG bytes.
- `legend.py` re-uses the existing `LegendData` / `GradientEntry` /
  `DiscreteEntry` dataclasses from `pysepal.solara.components.legend` — no
  duplication.
- `button.py` is the only Solara-aware file. It owns the click → capture →
  compose → download flow end-to-end.

Basin-rivers just imports `PdfReportButton` from
`pysepal.solara.components.pdf_report` and wires it into the dashboard modal
next to the existing `Download CSV` button.

## Data Model

```python
from dataclasses import dataclass, field
from typing import Literal

CaptureKind = Literal["map", "echart", "legend", "stats_table"]

@dataclass(frozen=True, slots=True)
class MapCapture:
    """Capture the current live view of an ipyleaflet map via html2canvas."""
    selector: str                  # CSS selector for the map root div
    label: str = "Map"             # caption printed above the image
    height_mm: float | None = None # if None, scale to page width preserving AR

@dataclass(frozen=True, slots=True)
class EChartCapture:
    """Capture an ipecharts widget via echarts.getInstanceByDom().getDataURL()."""
    selector: str                  # CSS selector for the chart container div
    label: str = ""                # optional caption printed above the chart
    optional: bool = False         # skip silently if the element is missing
    pixel_ratio: int = 2           # getDataURL pixelRatio (2 = retina-ish)

@dataclass(frozen=True, slots=True)
class LegendCapture:
    """Render a native (vector) legend from LegendData — no DOM capture.

    LegendData is the same dataclass used by LegendComponent; we re-draw it
    in reportlab Flowables. This avoids the "legend is hidden behind the
    modal" problem and also gives crisp vector output in the PDF.
    """
    legend_data: dict              # asdict(LegendData)
    title: str = "Legend"

@dataclass(frozen=True, slots=True)
class StatsTableCapture:
    """Native two-column key/value table (no DOM capture)."""
    rows: tuple[tuple[str, str], ...]
    title: str = ""

CaptureSpec = MapCapture | EChartCapture | LegendCapture | StatsTableCapture

@dataclass(frozen=True, slots=True)
class PdfReportConfig:
    """Top-level PDF configuration."""
    title: str
    subtitle: str = ""
    metadata: tuple[tuple[str, str], ...] = ()   # rendered as a header grid
    page_width_mm: float = 210.0                 # A4 width by default
    margin_mm: float = 15.0
    footer_text: str = "Generated via SEPAL • sepal.io"
    include_timestamp: bool = True
```

`PdfReportConfig` is immutable; it's the single source of truth for the
report's non-image content. Images come from the capture pipeline.

## Capture Flow (one round-trip)

1. User clicks `PdfReportButton`. Component sets a reactive `building=True`
   and mounts a hidden `VuetifyTemplate` with a `tick` traitlet.
2. The template's JS watches `tick`. On change, it:
   a. Lazy-loads `html2canvas` from cdnjs if `window.html2canvas` is
      undefined. The promise is memoized on `window.__pysepal_h2c__` so
      subsequent clicks skip the fetch.
   b. Iterates the `capture_specs` JSON (pushed in from Python). For each:
      - `kind == "map"`: `html2canvas(el, {useCORS: true, backgroundColor: "#fff", scale: 2})` → `canvas.toDataURL("image/png")`.
      - `kind == "echart"`: `echarts.getInstanceByDom(el).getDataURL({pixelRatio, backgroundColor: "#fff"})`.
      - `kind == "legend"` / `"stats_table"`: no capture; placeholder entry.
   c. Collects `{"<selector>": "<data_url>"}` into a single object.
   d. Writes the object to the synced traitlet `captured_images`.
3. Python `use_effect` on `captured_images` fires. It:
   a. Strips `data:image/png;base64,` prefixes and base64-decodes each entry.
   b. Calls `build_pdf_report(config, captures, captured_images) -> bytes`.
   c. Stores the bytes in `pdf_bytes_ref.current` and triggers the
      already-mounted `solara.FileDownload`'s download.
4. `building=False`. Traitlets are reset so a subsequent click re-runs.

```
  [click]
     │
     ▼
  Solara: building=True, push capture_specs + tick++
     │
     ▼
  VuetifyTemplate JS
     ├── ensure html2canvas loaded
     ├── for each spec: html2canvas OR echarts.getDataURL
     └── write captured_images = {selector → dataURL}
     │
     ▼
  Solara use_effect: build_pdf_report(...) → bytes
     │
     ▼
  FileDownload triggers browser download
     │
     ▼
  building=False; traitlets reset
```

Total time on a realistic dashboard: ~1.5 s (tile paint wait) + <1 s (PDF
compose) ≈ under 3 s.

## Builder (pure Python)

```python
def build_pdf_report(
    config: PdfReportConfig,
    captures: list[CaptureSpec],
    image_bytes: dict[str, bytes],   # selector → decoded PNG bytes
) -> bytes:
    """Compose a single-long-page PDF. No Solara, no JS."""
```

Uses `reportlab.platypus.SimpleDocTemplate` with `pagesize=(page_width_mm,
computed_height_mm)`. The height is the sum of Flowables + margins after a
first `wrap` pass — so **one tall page** is the default. If that height
exceeds reportlab's per-page maximum (~5.5 m at 72 dpi), we fall back to
multi-page A4 with `Platypus`'s normal flow; this is a safety net, not a
normal outcome.

Flowable composition order:
1. `Paragraph(config.title, TitleStyle)`
2. `Paragraph(config.subtitle, SubtitleStyle)` if non-empty
3. `MetadataTable(config.metadata)` — 2-column grid, unobtrusive
4. For each `CaptureSpec` in order:
   - `MapCapture` / `EChartCapture` → optional caption `Paragraph` +
     `reportlab.platypus.Image` (scaled to `page_width - 2*margin`).
   - `LegendCapture` → `LegendFlowable(legend_data, title)`.
   - `StatsTableCapture` → two-column `Table` with soft zebra striping.
5. Footer `Paragraph`: `footer_text` + timestamp (if enabled).

## LegendFlowable (native, vector)

`legend.py` exposes `LegendFlowable(legend_data: dict, title: str = "Legend")`
which subclasses `reportlab.platypus.Flowable`. On `.draw()` it:
- Renders the title as a bold Paragraph.
- For each gradient: a horizontal bar drawn with `canvas.linearGradient()`
  shim (reportlab has no native gradient, so we sample N stops and draw
  rectangles — 120 stops gives smooth output at typical PDF zoom).
- For each discrete entry: a filled square + label text.

Takes the same `asdict(LegendData)` dict that `LegendComponent` already
consumes. Zero duplication of the data model.

## PdfReportButton (Solara)

```python
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
    ...
```

Internal state (all `solara.use_reactive`):
- `building: bool` — drives the spinner and the hidden template's `tick`.
- `captured_images: dict[str, str]` — synced traitlet written by JS.
- `pdf_bytes_ref` — `solara.use_ref(None)` holding the composed bytes.
- `error: str | None` — last error; surfaced via the `pysepal` notification
  system if present, otherwise inline below the button.

Three DOM additions:
- The button itself (reuses `solara.Button` styling).
- A hidden `VuetifyTemplate` (the capture engine). `display: none`.
- A hidden `solara.FileDownload` pre-wired with `data=lambda:
  pdf_bytes_ref.current`; its auto-click is triggered by a `ref.click()`
  call once `captured_images` arrives and the build succeeds.

## Basin Rivers Wiring

Tag the chart divs (one-line change each):

```python
# catchment_pie.py, overall_pie.py, catchment_bar.py, loss_trend.py
# Add a `classes=["br-echart-<key>"]` to the ECharts widget's outer div.
```

Tag the `SepalMap` root. `SepalMap` already has a unique `_id` CSS class
(`map._id`) applied via `add_class`. We pass that into the MapCapture
selector: `MapCapture(selector=f".{sepal_map._id}")`.

In `dashboard_step.py`, add:

```python
from dataclasses import asdict
from pysepal.solara.components.pdf_report import (
    PdfReportButton, PdfReportConfig,
    MapCapture, EChartCapture, LegendCapture, StatsTableCapture,
)

# Inside _DashboardContent, next to the existing FileDownload row:
PdfReportButton(
    filename="basin_rivers_report.pdf",
    config=PdfReportConfig(
        title="Basin Rivers — Watershed Report",
        subtitle="Upstream delineation & forest change",
        metadata=(
            ("Outlet", f"{state.lat.value:.4f}, {state.lon.value:.4f}"),
            ("HydroSHEDS level", str(state.level.value)),
            ("Year range", f"{state.year_start.value}–{state.year_end.value}"),
            ("Tree cover threshold", f"{state.treecover.value}%"),
            ("Upstream basins", str(n_basins)),
            ("Watershed area", _fmt_area(total_area)),
        ),
    ),
    captures=(
        MapCapture(selector=f".{sepal_map._id}", label="Map view"),
        LegendCapture(legend_data=legend_data_dict, title="Legend"),
        StatsTableCapture(
            title="Summary",
            rows=(
                ("Stable forest", f"{_fmt_area(forest_area)} ({forest_pct:.1f}%)"),
                ("Forest loss",   f"{_fmt_area(loss_area)} ({loss_pct:.1f}%)"),
            ),
        ),
        EChartCapture(selector=".br-echart-overall",        label="Forest composition"),
        EChartCapture(selector=".br-echart-catchment-pie",  label="Per-catchment share"),
        EChartCapture(selector=".br-echart-catchment-bar",  label="Per-catchment breakdown"),
        EChartCapture(selector=".br-echart-loss-trend",     label="Loss over time",
                      optional=True),
    ),
)
```

The page flow needs `legend_data` passed from `page.py` → `DelineationStep`
→ `DashboardStep`. Today the dashboard only receives `legend_visible`. We
extend the prop list to pass `legend_data` too.

## Error Handling

Three categories, each with explicit UX:

1. **Client-side capture failure** (CORS-blocked tile, missing selector,
   ECharts not initialized, html2canvas load failure).
   - JS writes `{"__error__": "<human message>", "__failed__": [<sel>...]}`
     into `captured_images` instead of a normal payload.
   - Python detects the sentinel, surfaces via `pysepal.solara.notifications`
     if present (`notifications.error(...)`), else inline below the button.
   - Button un-spins. No partial PDF is offered.

2. **Python compose failure** (bad base64, reportlab exception).
   - Caught in the `use_effect`; message + `logger.exception` via
     `pysepal.logger`. Same notification surface.

3. **Partial / optional captures** (`optional=True` and element missing).
   - Silently skipped in the capture pipeline; the compose step never sees
     them. A non-optional missing capture is a hard error per category 1.

**Timeouts.** Client-side capture has a 15 s wall-clock per selector
(`Promise.race` with a rejector). Python side has no timeout; compose is
synchronous and typically <1 s for realistic payloads.

**CORS note.** The default CartoDB and GEE tile URLs are CORS-enabled
(`Access-Control-Allow-Origin: *`). The bundle's `SepalMap` basemaps and
`EELayer` URLs both fall into this set. If a future app adds a non-CORS
basemap, html2canvas will log a partial capture (it tries gracefully); the
test plan includes a manual check for a non-CORS basemap.

## Testing

**Unit (pure Python, fast):**

- `test_builder.py` — fixtures: a small PNG (checkerboard), a `LegendData`
  with one gradient + two discrete entries, a metadata grid, two
  `StatsTableCapture`s. Assert:
  - `build_pdf_report()` returns non-empty `bytes` starting with `%PDF-`.
  - `pypdf.PdfReader(io.BytesIO(bytes)).pages` has ≥1 page.
  - Extracted text contains the title, subtitle, all metadata keys, and all
    section labels.
  - Multi-page fallback triggers when content height > reportlab max.

- `test_legend.py` — asserts `LegendFlowable.wrap(width, avail)` returns a
  plausible `(width, height)` and that `draw()` renders without exception
  onto a test canvas.

- `test_models.py` — dataclass invariants: `EChartCapture.pixel_ratio >= 1`;
  `MapCapture.selector` non-empty; `PdfReportConfig.metadata` accepts
  tuples-of-tuples.

**Integration (Solara-aware, mocked):**

- `test_button_wiring.py` — renders `PdfReportButton` with a mock
  `captures` list, simulates a traitlet write of captured images, asserts
  `pdf_bytes_ref.current` becomes non-None and the file download is armed.
  Does not exercise JS.

**Manual smoke (per-app, documented in each app's CLAUDE.md):**

- Open the app's dashboard, click the button, verify:
  - PDF opens in a viewer with correct title + metadata.
  - Map image shows current state (tiles + vector layers + markers).
  - Legend is rendered natively (crisp text, no pixelation under zoom).
  - All charts appear in the declared order.

No e2e browser test in v1. Playwright was evaluated and rejected for the
~200 MB Docker cost.

## API Summary

Public (re-exported from `pysepal.solara.components.pdf_report`):

- `PdfReportButton` — Solara component.
- `PdfReportConfig` — top-level config dataclass.
- `MapCapture`, `EChartCapture`, `LegendCapture`, `StatsTableCapture` —
  capture spec dataclasses.
- `build_pdf_report` — pure builder function, for callers that want to
  compose PDFs without the button.

Internal (not re-exported):

- `LegendFlowable` — reportlab Flowable; used by `build_pdf_report`.
- Capture template class in `button.py`.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| html2canvas silently produces a blank map (e.g., tile still loading) | JS pre-check: wait until `document.querySelectorAll('.leaflet-tile-loaded').length === total_tiles` with a 5 s ceiling before capture. |
| ECharts widget found but `getInstanceByDom` returns `null` (chart not yet initialized) | Retry up to 500 ms; report a clear error if still null. |
| reportlab binary wheel not available for a target platform | Pure-Python fallback in reportlab works (just slower); covered automatically. |
| Legend overlay is hidden when dashboard modal is open | Legend is **re-drawn natively** from `LegendData`, not captured from DOM — problem sidestepped. |
| GEE tile CORS change in the future | Manual smoke test in per-app CLAUDE.md; JS error is explicit and surfaced. |
| Dashboard modal shrinks chart on small viewports, capture is low-res | `pixel_ratio=2` default; user's monitor DPI is captured at 2x effective. |
| Very large watersheds produce tall PDFs | Page-height cap in builder; auto-flow to multi-page beyond the cap. |

## Open Questions (decided during brainstorming)

- **Placement**: generic (`pysepal.solara.components.pdf_report`), not app-local.
- **Layout**: single long page, map on top, dashboard below.
- **Deps**: small-Python (`reportlab`), no headless browser, no npm build.
- **Legend handling**: native redraw, not DOM capture.
- **Scope**: basin-rivers is first consumer; other bundle apps wire in later.
- **Storage**: browser download only for v1; SEPAL workspace persistence is
  a future extension that can reuse `export_engine`.

## Follow-ups (explicitly out of v1 scope)

- HTML preview mode (render the same Flowables to HTML for in-app preview).
- SEPAL workspace / Drive persistence via `export_engine`.
- Multi-theme / branded PDF templates (SEPAL logo variants, colors).
- i18n for PDF labels (current English strings are hard-coded; we pass
  labels through config already, so apps can localize at the call site).
- Chart image export from the button row (reusing the ECharts capture).
