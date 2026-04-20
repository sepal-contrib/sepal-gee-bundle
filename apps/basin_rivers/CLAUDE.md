# Basin Rivers — Upstream Watershed Delineation

> Read the bundle CLAUDE at `/home/dguerrero/1_modules/sepal-gee-bundle/CLAUDE.md`
> and invoke the `pysepal` skill before editing. This file only documents
> basin-rivers-specific decisions and traps.

## Status

Migration **complete**. 39 pytest passing, ruff clean. Runs at
`http://localhost:8767/basin-rivers`.

## Purpose

Upstream watershed from a user-chosen outlet (pour point) using WWF HydroSHEDS,
plus per-catchment Hansen GFC forest-change stats.

## User workflow (as implemented)

1. Pick an outlet (map click or manual lat/lon) — right-panel "Outlet" section.
2. Configure level / year range / treecover — "Parameters".
3. **Trace watershed** — classifies GFC, adds map layers + legend.
4. Choose "All upstream basins" or "Filter specific basins".
5. **Calculate statistics** — zonal stats, seeds dashboard state.
6. **Open dashboard** — modal (`max_width=1400px`) with settings card + overall donut +
   per-catchment donut + per-catchment bar. Loss-trend line appears only when
   `selected_var == "loss"`.

## GEE datasets

- HydroSHEDS: `WWF/HydroSHEDS/v1/Basins/hybas_{level}` (levels 5–12).
- Hansen GFC: pinned in `params.py:GFC_DATASET` (currently 2024 v1.12, covers 2001–2024).

## Core algorithm

### Upstream tracing (`scripts/watershed.py`)

Iterative `ee.List.sequence(1, 100).iterate(...)` up the HydroSHEDS `NEXT_DOWN`
graph. Legacy anti-pattern, works but slow for very large watersheds — see
"Known limitations".

### Forest-change encoding (`scripts/gfc_classification.py`)

Single `ee.Image` with integer codes:

- `1..GFC_MAX_YEAR` → loss in year `2000 + v`
- `30` non-forest, `40` stable forest, `50` gain, `51` gain+loss

`GFC_MAX_YEAR` is set in `params.py` based on the dataset.

### Zonal stats (`scripts/statistics.py`)

`pixelArea()/10000 + reduceRegions(Reducer.sum().group(1))` → tidy DataFrame
(`basin, variable, area, group, year, color`). `add_catchment_colors` cycles a
deterministic blue/teal palette (`CATCH_COLOR_PALETTE`) by sorted basin id.

## File layout

```
apps/basin_rivers/
├── page.py                      # state + SepalMap + ThemeToggle + legend reactives + MapApp
├── model.py                     # BasinRiversState (single dataclass-ish of reactives)
├── params.py                    # GFC_DATASET/SLD/LEGEND, CATCH_COLOR_PALETTE,
│                                # VARIABLE_LABELS, CATCH_{PIE,BAR}_TITLES,
│                                # MAX_CATCH_DISPLAY, BASIN_WARN_THRESHOLD
├── components/
│   ├── point_step.py            # outlet picker
│   ├── params_step.py           # level / years / treecover
│   ├── delineation_step.py      # 2 tasks, map layers, legend on/off, seeds dashboard, renders DashboardStep
│   ├── dashboard_step.py        # button + modal + _DialogResizer + CSV download
│   └── dashboard/
│       ├── theme.py, overall_pie.py, catchment_pie.py,
│       │ catchment_bar.py, loss_trend.py, settings_card.py
└── scripts/
    ├── watershed.py, gfc_classification.py,
    │ statistics.py, visualization.py
```

## State schema (`model.py`)

Flat reactives on `BasinRiversState`. No nested sub-stores.

| Field | Default | Used by |
|---|---|---|
| `lat`, `lon`, `manual_coords` | None / False | point_step |
| `level`, `year_start`, `year_end`, `treecover` | 8, 2010, 2024, 80 | params_step |
| `hybasin_list`, `method`, `selected_basins` | [], "all", [] | delineation_step |
| `upstream_fc`, `forest_change` | None | in-memory GEE objects |
| `zonal_df` | None | dashboard source of truth |
| `selected_var`, `selected_hybasid_chart`, `sett_timespan` | "all", [], (year_start, year_end) | dashboard |

## Wiring specifics

- `page.py` owns `legend_data = use_reactive({})`, `legend_visible = use_reactive(False)`
  and passes both to `DelineationStep`, which forwards `legend_visible` to
  `DashboardStep`. `LegendComponent(...)` is mounted at the end of `page.py`.
- `_sync_delineation` sets the legend on, warns if `len(hybas_ids) > BASIN_WARN_THRESHOLD` (50).
- `_sync_stats` resets `selected_var` to `"all"`, respects filter-mode when seeding
  `selected_hybasid_chart`, and **caps it to top `MAX_CATCH_DISPLAY` (10) basins by area**
  when too many, with an info notification.
- On modal open, `DashboardStep` calls `legend_visible.set(False)` to stop the map
  legend from floating over the dialog; restores on close.

## Basin-rivers-specific ipecharts traps

Generic ipecharts usage is in the pysepal ipecharts guide; these are the things
that bit us here:

- **`Option.grid` needs an `ipecharts.option.Grid`**, not a dict. Raises `TraitError`
  if you pass a dict.
- **`EChartsWidget.element(...)` returns a reacton `Element`, not the Jupyter widget.**
  `Element.on(event, handler)` is a different signature from the ipecharts
  `widget.on("click", None, handler)` API — *don't* try to wire click events via
  `use_ref`-ing the return value. We dropped click-to-select on the overall pie
  for this reason. If you ever need it, subclass `EChartsWidget` and register the
  handler in `__init__`, or create the widget via `use_memo` and mount it manually.
- **Dialog + ECharts initial-width bug.** A chart mounted inside an opening
  `rv.Dialog` measures at zero width. Solution is in `dashboard_step.py:_DialogResizer`:
  a local `VuetifyTemplate` with a `tick` traitlet whose Vue template dispatches
  `window.dispatchEvent(new Event("resize"))` on change. Mounted inside the dialog body
  with `display:none` and `eager=True`. `use_effect([open_dialog.value])` bumps `tick`.
- **Do NOT use `pysepal.frontend.resize_trigger.rt` in Solara apps.** Its module-level
  `display(rt)` only mounts in a Jupyter notebook; in a Solara app the singleton is
  never in the DOM and `rt.resize()` is a no-op.

## Dashboard dialog shape

Card-style, not Toolbar-style:

- `rv.Dialog(max_width="1400px", scrollable=True, eager=True)`
- `rv.CardTitle`: `mdi-chart-bar` icon + title, `rv.Spacer`, close button.
- `rv.Divider`
- `rv.CardText`: `_DialogResizer` (hidden), header row (upstream-basins count +
  CSV download), then 2×(md5 + md7) chart rows, plus the conditional loss-trend row.

## Outputs

- Map layer keys: `"GFC forest change"` (raster), `"Upstream catchment"`
  (GeoJSON polygons), `"Outlet"` (marker).
- `LegendComponent` with a loss-year gradient + 4 discrete classes.
- CSV export of `zonal_df` via `solara.FileDownload` inside the dashboard.
- No chart image exports (ECharts `Toolbox(show=True)` not enabled).

## Running

Standard bundle commands (see bundle CLAUDE). Caveat: `./run_solara.sh` uses
whatever `solara` is on PATH — if the conda env isn't active you'll see
`ModuleNotFoundError: solara`. Run
`conda run -n sepal-gee-bundle solara run app.py --port 8767` to bypass.

## Known limitations / follow-ups

- Upstream tracing uses `ee.List.sequence(1, 100).iterate(...)` — legacy anti-pattern.
  Consider a smarter traversal if it becomes a hot path.
- No click-to-select on the overall pie (see ipecharts traps above).
- No chart image export (one-liner to enable `Toolbox`).
- **Notification pill overlaps the dashboard modal.** pysepal issue — the
  notification UI's z-index sits above `v-dialog` (202). Local workaround only
  hides our own legend. Fix is upstream in
  `pysepal/solara/notifications/notification_ui.py`.
- Top-N cap on basins applies only at seed time; if the user expands the
  Catchments multi-select beyond 10 the charts still render all of them (no
  automatic "Others" fold).
- Tests cover pure helpers only; no coverage of `_sync_delineation`, `_sync_stats`,
  or the modal wiring.

## Legacy reference

`~/1_modules/basin-rivers/` — original sepal_ui / plotly implementation. Useful
for algorithmic questions and the class-code translation table
(`component/parameter/app.py`). Don't copy UI code.

## PDF export

The dashboard modal's **Download PDF** button calls
`pdf_report.PdfReportButton`. It captures the live
map (via html2canvas) and each ECharts chart (via the native
`getDataURL()`), re-draws the legend natively in reportlab, and hands the
browser a PDF download.

The package lives in this repo at `/pdf_report/` and is expected to be
promoted into pysepal once it's been field-tested.

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
