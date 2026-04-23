# GFC — Global Forest Change Visualization & Export

## Purpose

Visualize and export forest change maps from the Hansen Global Forest Change dataset. Classifies pixels into forest, non-forest, gain, loss (by year), and gain+loss based on user-defined thresholds and year ranges.

## User Workflow

1. **Select AOI** — draw or upload an area of interest
2. **Set parameters** — tree cover threshold and year range
3. **Visualize** — display classified forest change map on the map
4. **Export** — export GeoTIFF to Google Drive, download to SEPAL, generate area statistics (CSV) and loss histogram

## GEE Datasets

- **Hansen GFC**: `UMD/hansen/global_forest_change_2024_v1_12` — tree cover 2000, loss year (1-24), gain

## Core Algorithm

Classification expression using tree cover threshold and year range [start, end]:
- **Non-forest** (30): tree cover <= threshold with no gain; OR tree cover > threshold but loss before start year
- **Stable forest** (40): tree cover > threshold with no loss (or loss after end year)
- **Gain** (50): tree cover <= threshold with gain=1; OR tree cover > threshold, gain=1, no loss
- **Gain+Loss** (51): tree cover > threshold, gain=1, loss within [start, end]
- **Loss year** (1-24): tree cover > threshold, no gain, loss within [start, end] — value = loss year code

The classification is implemented as a band math expression string, which is concise but hard to read. The basin-rivers app has the same logic written more clearly with `.where()` chains.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threshold` | 30 | GFC tree cover threshold (%) |
| `years` | [2001, 2020] | Year range for loss analysis |

## Outputs

- **Map layer**: classified GFC map with SLD styling (color per class)
- **GeoTIFF export**: via Google Drive → SEPAL download → merge tiles → apply colormap
- **CSV statistics**: pixel counts converted to hectares per class (reprojected to ESRI:54009 Mollweide)
- **Loss histogram**: bar chart of tree cover loss area per year
- **Area table**: summary table of forest/non-forest/gain/loss areas
- **PDF legend**: raster legend exported as PDF

## Scripts Worth Preserving

- `compute_ee_map` — the core GFC classification (band expression approach)
- `create_hist` — pixel counting + area calculation with Mollweide reprojection
- `plot_loss` — loss-by-year bar chart generation
- `area_table` — summary statistics table

The export pipeline (GEE → Drive → download → merge → colormap) is a common pattern but tightly coupled to the old gdrive helper. Replace with pysepal/GEEInterface export patterns.

## Dashboard

After `ResultsStep` computes stats, a **DashboardStep** button opens a large
modal (`rv.Dialog(max_width="1400px", scrollable=True, eager=True)`) with:

- **SummaryCard** — compact `_StatItem` row: AOI total area, stable forest
  (ha + %), forest loss (ha + %), gain, gain+loss, tree-cover threshold,
  year range.
- **OverallPie** — donut across the top-level classes (Stable forest /
  Non-forest / Gain / Gain+Loss / Loss). Colours come from `params.HEX_PALETTE`.
- **LossTrend** — bar chart of loss area per year, each bar tinted with the
  matching loss-year gradient colour (`theme.loss_year_color`).
- **Download CSV** — `solara.FileDownload` of the raw `stats_rows`.

### Wiring

- `model.GfcState` grew a `stats_rows: list` reactive. `results_step.py`
  writes to it when `compute_task` finishes.
- `page.py` passes `legend_visible` through to `ResultsStep` →
  `DashboardStep`. Dialog hides the legend on open, restores it on close.
- The inline `_LossChart` previously rendered in `results_step.py` was
  **removed** — loss-by-year lives only in the dashboard. `_StatsTable`
  remains in the right panel so basic numbers are visible without opening
  the modal.
- Auto-opens whenever a fresh `stats_rows` list arrives (watches
  `id(rows)`), matching the basin-rivers UX.

### Known-trap compatibility

Same traps as basin-rivers (see its CLAUDE "ipecharts traps" section):

- **`_DialogResizer`** — copied verbatim. Bumps `tick` on dialog open to
  fire a `window.resize` event so ECharts re-measures its container.
- **`Option.grid` = `Grid(...)`, never a dict** — enforced.
- **No click-to-select on the pie** — `EChartsWidget.element` returns a
  reacton Element with an incompatible `.on(...)` signature.
- **Every chart `Option` includes `Toolbox(show=True, feature={"saveAsImage": ...})`**
  so users get a PNG download per chart.
- **Chart wrapper classes**: `.gfc-echart-overall`, `.gfc-echart-loss-trend`.
  Keep in sync if we later wire a PDF report (basin-rivers' `EChartCapture`
  pattern).

## Migration Notes

- The GFC classification logic is essentially the same as basin-rivers `get_gfc` — consider a shared utility in `scripts/` or a common GFC helper
- Area statistics use rasterio + pyproj for local reprojection; this is a SEPAL-download-then-process pattern — evaluate if GEE-side `ee.Image.pixelArea()` + `reduceRegion` is sufficient
- SLD styling for the map is defined in `parameter/colors.py` — needed for visualization
- Uses deprecated `distutils.version.LooseVersion`
- Export flow is complex (GEE task → Drive → SEPAL → merge tiles) — simplify with modern pysepal export
