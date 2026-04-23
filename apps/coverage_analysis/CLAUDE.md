# Coverage Analysis — Satellite Imagery Coverage & NDVI Statistics

## Purpose

Analyze satellite imagery availability and quality over an AOI. Computes cloud-free pixel counts, total scene coverage, NDVI median, and NDVI standard deviation across Landsat and Sentinel-2 collections. Supports full-period and annual temporal aggregation.

## User Workflow

1. **Select AOI** — via pysepal `AoiView` (methods restricted to `-SHAPE -POINTS`).
2. **Sensors & view** — sensors (L4/L5/L7/L8/S2), date range, SR vs TOA, Tier 2 toggle, measure, annual toggle, then click **Show on map**. The task builds the multi-sensor collection, counts images, composes the measure, and adds layers in one shot.
3. **Dashboard** — compute per-sensor and per-year image counts; open a modal with summary card + two bar charts + CSV download.
4. **Export** — `ExportLauncher` dialog (EE asset / Drive / SEPAL) with stats and temporal aggregation options.

The right panel has four sections: **AOI / Sensors & view / Dashboard / Export**.

## GEE Datasets (C02)

- **Landsat 4/5/7/8**: C02 (`T1_L2` for SR, `T1_TOA` for TOA), Tier 2 optional.
- **Sentinel-2**: `COPERNICUS/S2_SR_HARMONIZED` or `COPERNICUS/S2_HARMONIZED`.
- **S2 Cloud Probability**: `COPERNICUS/S2_CLOUD_PROBABILITY` (joined on `system:index`).

Legacy C01 IDs were migrated to C02: `C01/T1_SR` → `C02/T1_L2`, `C01/T1_TOA` → `C02/T1_TOA`. S2 uses the `_HARMONIZED` IDs.

## Architecture (migrated)

```
apps/coverage_analysis/
├── page.py                 # MapApp + NotificationProvider + 4 right-panel sections
├── model.py                # CoverageState — flat solara.reactive fields
├── params.py               # Dataset IDs, band maps, palettes, UI option lists
├── components/
│   ├── aoi_step.py         # AoiView (methods=["-SHAPE","-POINTS"])
│   ├── visualize_step.py   # sensors/dates/SR/T2 + measure/annual + "Show on map"
│   ├── dashboard_step.py   # Compute stats button + modal with summary/sensor bar/year bar + CSV
│   ├── dashboard/          # ipecharts charts + theme for the dashboard modal
│   │   ├── theme.py        # Sensor palette + use_echarts_theme()
│   │   ├── summary_card.py # _StatItem row
│   │   ├── sensor_bar.py   # Image count per sensor
│   │   └── year_bar.py     # Image count per year
│   └── export_step.py      # stats/temps/scale + ExportLauncher
└── scripts/
    ├── cloud_masking.py    # QA_PIXEL masks for Landsat C02; s2cloudless simple/full for S2
    ├── collection_builder.py  # build_collection, build_asset_name
    ├── analysis.py         # year_windows, reduce_measure, compose_measure, build_export_image
    └── dashboard_stats.py  # compute_dashboard_stats — per-sensor + per-year size() counts
```

## Dashboard

Separate "Compute dashboard stats" button (not folded into the visualize
task — image counts are cheap `size()` calls but we want to keep the
visualize path fast). On success, auto-opens a large modal
(`rv.Dialog(max_width="1400px", scrollable=True, eager=True)`) with:

- **SummaryCard** — `_StatItem` row: AOI area (ha), date range, total
  images, selected sensors, active measure.
- **SensorBar** — ipecharts bar chart, one bar per sensor (coloured per
  `theme.SENSOR_COLORS`). Rebuilds a per-sensor collection via
  `build_collection(..., sensors=[sensor])` and calls `.size().getInfo()`.
- **YearBar** — ipecharts bar chart, one bar per year. Uses
  `year_windows(start, end)` + `collection.filterDate(...).size()` on the
  merged collection.
- **Download CSV** — tidy `group,name,count` dataframe combining per-sensor
  and per-year rows.

### Wiring

- `model.CoverageState` grew a `dashboard_stats` reactive: dict with keys
  `per_sensor`, `per_year`, `totals`.
- `DashboardStep` receives `(state, legend_visible, sepal_map)`. Dialog
  hides the legend on open, restores it on close.
- Auto-opens whenever a fresh `dashboard_stats` dict arrives (watches
  `id(stats)`), matching the gfc / basin-rivers UX.
- Every chart `Option` includes `Toolbox(show=True, feature={"saveAsImage": ...})`
  so users get a PNG download per chart.
- `_DialogResizer` copied verbatim — bumps `tick` on open so ECharts
  re-measures inside the just-shown dialog.

## State (`CoverageState`)

Flat reactives: `aoi`, `start_date`, `end_date`, `sensors`, `surface_reflectance`, `include_tier2`, `measure`, `annual`, `stats`, `temps`, `scale`, `collection`, `result_image`, `result_band_names`, `loading`.

## Legacy → new file mapping

| Legacy (`coverage_analysis/component/`) | New |
|---|---|
| `scripts/bfast_preanalysis.analysis` | `scripts/collection_builder.build_collection` |
| `scripts/helpers.create_collection` + `addNDVI*` | folded into `collection_builder` |
| `scripts/cloud_masking.py` | `scripts/cloud_masking.py` (Landsat rewritten for C02 `QA_PIXEL`) |
| `scripts/display.py` | `components/visualize_step.py` + `scripts/analysis.compose_measure` |
| `scripts/exports.py` + `gdrive.py` + `download.py` | pysepal `ExportLauncher` + `scripts/analysis.build_export_image` |
| `parameter/values.py` / `viz.py` | `params.py` |
| `tile/selection.py` | `components/selection_step.py` |
| `tile/visualization.py` | `components/visualize_step.py` |
| `tile/export.py` | `components/export_step.py` |
| `widget/date_picker.py` | replaced with plain TextField (YYYY-MM-DD) |

## Tests

`tests/apps/coverage_analysis/test_scripts.py` — 14 passing:
- Params consistency (C02 asset IDs, NDVI band coverage, UI shapes).
- Collection builder helpers (`_landsat_id`, `_t2_id`, `build_asset_name`).
- `year_windows` (invalid ranges, single year, multi-year).
- `MEASURE_BAND` / `MEASURE_REDUCER` parity.
- `build_collection` smoke test with `ee` patched.

## Known limits / things to verify live

- **C02 band names for SR** are assumed: `SR_B3`, `SR_B4`, `SR_B5` (Landsat 8), `SR_B3`/`SR_B4` (L4/5/7). Verify against actual asset schemas on SEPAL.
- **S2 TOA shadow masking** uses the simple cloud-only mask because SCL is SR-only. `mask_s2_full` falls back via `ee.Algorithms.If` when SCL missing.
- **Date input** uses `TextField` (YYYY-MM-DD); no calendar picker yet. Could be upgraded to a pysepal date picker if one exists.
- **Export** uses a single `ExportSource` whose `resolve()` constructs the composite multi-band image on demand from current stats/temps/scale selections.
- **Visualization max values** for count measures default to 20/100 (annual/total) or 40/200 for "all" counts — legacy defaults; tune if needed.
- No legend component is wired (measures are continuous palettes). Could add pysepal `LegendComponent` with gradient entries later.
- The route in `app.py` was already registered.
