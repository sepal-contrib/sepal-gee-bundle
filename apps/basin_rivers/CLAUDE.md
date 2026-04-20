# Basin Rivers — Upstream Watershed Delineation

## Status

**Migration: COMPLETE.** Core workflow, dashboard, and polish are done. Runnable
at `http://localhost:8767/basin-rivers` via `./run_solara.sh`. 39 unit tests
passing, ruff clean.

## Purpose

Identify the upstream watershed of a user-chosen outlet (pour point) using WWF
HydroSHEDS basins, and compute per-catchment Hansen GFC forest-change statistics.

## User Workflow (implemented)

1. **Pick an outlet** — click on map or enter lat/lon manually (right-panel section "Outlet").
2. **Configure parameters** — HydroSHEDS level, year range, tree-cover threshold.
3. **Trace watershed** (button) — computes upstream `FeatureCollection`, classifies GFC
   pixels, renders the classification layer + basin polygons on the map, shows the
   map legend.
4. **Pick basin scope** — "All upstream basins" or "Filter specific basins".
5. **Calculate statistics** (button) — zonal stats, seeds the dashboard state.
6. **Open dashboard** (button) — fullscreen-ish modal (`max_width=1400px`) with
   settings card + overall donut + per-catchment donut + per-catchment bar, plus a
   conditional loss-trend line when variable == "loss".

## GEE Datasets

- **HydroSHEDS**: `WWF/HydroSHEDS/v1/Basins/hybas_{level}` — levels 5–12.
- **Hansen GFC**: `UMD/hansen/global_forest_change_2024_v1_12` (pinned in
  `params.py:GFC_DATASET`; 24 loss years, covers 2001–2024).

## Core Algorithm (unchanged from legacy)

### Upstream tracing (`scripts/watershed.py`)

1. Filter HydroSHEDS collection at `level`.
2. Find the basin containing the outlet geometry.
3. Iteratively trace upstream: for each basin, find all basins whose
   `NEXT_DOWN` matches current `HYBAS_ID`. Uses
   `ee.List.sequence().iterate()` (legacy anti-pattern for very large watersheds —
   see "Known limitations" below).
4. Merge all found basins into a single `FeatureCollection`.

### Forest-change classification (`scripts/gfc_classification.py`)

Encoded as a single `ee.Image` with integer values:

- `1..GFC_MAX_YEAR` — loss in year `2000 + v`
- `30` — non-forest (tree cover ≤ threshold and no gain, OR tree cover > threshold but loss before start year)
- `40` — stable forest
- `50` — gain (tree cover ≤ threshold, gain=1)
- `51` — gain + loss (tree cover > threshold, gain=1, loss within `[start, end]`)

### Zonal stats (`scripts/statistics.py`)

`pixelArea()/10000` + `reduceRegions(..., reducer=Reducer.sum().group(1))`
grouped by class code. Parsed into a tidy DataFrame with columns
`basin, variable, area, group, year, color`.
`add_catchment_colors` then adds `catch_color` (deterministic blue/teal
palette cycled by sorted basin id).

## File Layout

```
apps/basin_rivers/
├── CLAUDE.md                    # this file
├── page.py                      # entry; creates state, SepalMap, ThemeToggle, legend reactives, MapApp
├── model.py                     # BasinRiversState — all Solara reactives, one place
├── params.py                    # GFC_DATASET/SLD/LEGEND, CATCH_COLOR_PALETTE (blue family),
│                                # VARIABLE_LABELS, CATCH_{PIE,BAR}_TITLES,
│                                # MAX_CATCH_DISPLAY, BASIN_WARN_THRESHOLD
├── components/
│   ├── point_step.py            # outlet picker (Alert hint + compact ListItem display)
│   ├── params_step.py           # level / year range / treecover
│   ├── delineation_step.py      # two async tasks, GFC + basins map layers, legend wiring, DashboardStep
│   ├── dashboard_step.py        # modal (CardTitle + Divider, no Toolbar), CSV download, resize shim
│   └── dashboard/
│       ├── theme.py             # use_echarts_theme() hook
│       ├── overall_pie.py       # donut by class; emphasizes selected_var
│       ├── catchment_pie.py     # donut per basin for selected_var
│       ├── catchment_bar.py     # bar per basin (single/stacked modes)
│       ├── loss_trend.py        # spline line, only rendered when selected_var == "loss"
│       └── settings_card.py     # variable select, timespan (loss-only), catchments multiselect
└── scripts/
    ├── watershed.py             # get_upstream_basin_ids, build_upstream_fc, get_hydroshed_collection
    ├── gfc_classification.py    # classify_gfc (pure ee expression)
    ├── statistics.py            # compute_zonal_stats, parse_zonal_stats, add_catchment_colors,
    │                              get_{overall_pie,catchment_pie,catchment_bar,loss_trend}_df
    └── visualization.py         # create_basins_layer, create_selection_layer (GeoJSON GeoJSON layers)
```

## State (`model.py`)

`BasinRiversState` holds a flat set of `solara.reactive(...)` fields.
Dashboard uses the same object (no separate store). Key fields:

| Field | Default | Notes |
|---|---|---|
| `lat`, `lon`, `manual_coords` | None / False | outlet |
| `level` | 8 | HydroSHEDS |
| `year_start` | 2010 | — |
| `year_end` | 2000 + GFC_MAX_YEAR | latest available |
| `treecover` | 80 | % |
| `hybasin_list` | [] | all upstream HYBAS ids |
| `method` | "all" | or "filter" |
| `selected_basins` | [] | filter-mode selection |
| `upstream_fc`, `forest_change` | None | GEE objects kept in memory |
| `zonal_df` | None | pandas DataFrame after stats |
| `selected_var` | "all" | dashboard class filter |
| `selected_hybasid_chart` | [] | dashboard basin filter |
| `sett_timespan` | (year_start, year_end) | loss-year slider range |

## Dashboard wiring

- Page creates two reactives: `legend_data = use_reactive({})`, `legend_visible = use_reactive(False)`.
  Both are threaded to `DelineationStep` and then to `DashboardStep`.
- After delineation: `legend_visible.set(True)` + `legend_data.set(asdict(GFC_LEGEND))`.
  `LegendComponent(...)` is mounted at the end of `page.py`.
- When the dashboard modal opens, we call `legend_visible.set(False)` to keep the map
  legend from floating on top of the dialog; restored on close.
- `_sync_stats` seeds `selected_var="all"`, clamps `selected_hybasid_chart` to top
  `MAX_CATCH_DISPLAY` (10) basins by area when too many, and sets
  `sett_timespan = (year_start, year_end)`. A notification explains any cap.
- `_sync_delineation` warns when `len(hybas_ids) > BASIN_WARN_THRESHOLD` (50).

## ipecharts integration — non-obvious rules

These are the patterns that worked; **fresh agents have gotten bitten by all of them**.

### Hooks-before-early-return

All Solara hooks (`use_echarts_theme`, `use_ref`, `use_effect`, `use_memo`) must
be called unconditionally at the top of the component, **before** any early
`return`. `reacton/core.py` raises hooks-ordering errors otherwise. Every chart
component in `dashboard/` follows this.

### `.element()` returns a reacton `Element`, not the widget

Do **not** try to wire click handlers via `EChartsWidget.element(...).on("click", ...)`
or via a `use_ref` grabbing `.widget`. Reacton's `Element.on(event, handler)` is a
3-arg signature; the ipecharts click API is `widget.on("click", selector, handler)`
(4-arg on the underlying Jupyter widget). They are different objects. Click-to-select
was attempted and dropped in favour of the settings-card variable dropdown.
If it ever becomes a must-have, options are (a) subclass `EChartsWidget` and wire
events in `__init__`, or (b) create the widget via `use_memo` and mount it with a
solara display-wrapper — both are meaningful effort.

### `Option.grid` needs an `ipecharts.option.Grid`

```python
from ipecharts.option import Grid
option = Option(..., grid=Grid(left=50, right=20, top=50, bottom=60, containLabel=True))
```
Dict is rejected with `TraitError: The 'grid' trait of an Option instance expected a Grid or None, not the dict {...}`.

### Transparent chart background

`backgroundColor="#1e1e1e00"` on every `Option` so charts blend with both light
and dark card backgrounds. Copied from `~/1_modules/se.plan/component/scripts/plots.py`.

### Dialog resize trick

ECharts measures its canvas on first mount. When mounted inside an `rv.Dialog`
that's still animating open, it starts at 0 width. Fix lives in
`dashboard_step.py:_DialogResizer` — a `VuetifyTemplate` with a `tick` trait
whose Vue template dispatches `window.dispatchEvent(new Event("resize"))` on
change. Mounted inside the dialog body (`display:none`) with `eager=True` so it
exists in the DOM before the first open. `use_effect([open_dialog.value])` bumps
`tick` on open.

**Do not use** `pysepal.frontend.resize_trigger.rt` — its module-level
`display(rt)` only works in a Jupyter notebook; it is never mounted in a Solara
app so `rt.resize()` is a no-op.

### Theme integration

Each chart calls `theme = use_echarts_theme(theme_toggle)` then passes `theme=theme`
to `EChartsWidget.element(...)`. The hook observes `theme_toggle.dark` and returns
`"dark" | "light"`, re-rendering on change.

### SettingsCard signature

Takes `(state)` only, not `(state, theme_toggle)`. `SettingsCard` doesn't render
charts — just controls.

## Components conventions

- Use `solara.Button` for click handlers (`on_click=callable`). `rv.Btn(on_click=...)`
  is **not** a recognised reacton prop and fires nothing; ipyvuetify expects
  `.on_event("click", handler)` at the widget level. All buttons in this app use
  `solara.Button`.
- Layout grid: `rv.Container(fluid=True) > rv.Row > rv.Col(cols=12, md=5|md=7)`.
  Matches the legacy two-row dashboard layout.
- Compact info displays use `rv.ListItem(dense=True) > ListItemIcon / ListItemContent`
  with `caption` title + `body-2` subtitle — see `point_step.py` and the dashboard
  header. Don't use full-width `rv.Chip` for values that are just labels.

## Dashboard dialog — current shape

- `rv.Dialog(max_width="1400px", scrollable=True, eager=True)`.
- Header: `rv.CardTitle` with `mdi-chart-bar` icon + title, `rv.Spacer`, close
  `solara.Button(icon=True, icon_name="mdi-close")`. Followed by `rv.Divider`.
  **Not** a primary-colored `rv.Toolbar`.
- Body: `rv.CardText` with the resizer, a header row (upstream-basins count + CSV
  download), then 2×(md5 + md7) rows, plus the conditional loss-trend row.

## Outputs

- Map: GFC-classification raster layer (key `"GFC forest change"`) + basin
  polygon vector layer (key `"Upstream catchment"`) + outlet marker (key `"Outlet"`).
- `LegendComponent` on the map with a year gradient + 4 discrete classes.
- CSV download inside the dashboard (basin_rivers_stats.csv).
- No image exports of charts (ECharts' built-in toolbox is not enabled).

## Running

```bash
# activate env once
conda activate sepal-gee-bundle

# launch (port 8767)
./run_solara.sh
# open http://localhost:8767/basin-rivers

# tests
conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/ -v

# lint + format
conda run -n sepal-gee-bundle ruff check apps/basin_rivers tests/apps/basin_rivers
conda run -n sepal-gee-bundle ruff format apps/basin_rivers tests/apps/basin_rivers
```

Note: `run_solara.sh` does NOT use conda internally — it relies on `solara` being
on PATH via the activated env. If you see `ModuleNotFoundError: solara` at startup,
the env isn't activated; use `conda run -n sepal-gee-bundle solara run app.py --port 8767`
directly.

## Known limitations / follow-ups

- **Upstream tracing uses `ee.List.sequence(1, 100).iterate(...)`** — the legacy
  anti-pattern. Works, but large watersheds are slow and may hit GEE limits.
  Consider replacing with a smarter traversal or `ee.FeatureCollection.filter`
  recursion if it ever becomes a hot path.
- **Click-to-select on the overall pie is not implemented** (see "ipecharts
  integration" above).
- **No chart image export.** Enabling `Toolbox(show=True)` on each `Option` is a
  one-liner if needed.
- **Notification pill overlaps the dashboard modal** on open. That's a
  pysepal-level issue (notification UI z-index sits above `v-dialog`). Local
  workaround: when the dashboard opens we hide `legend_visible`, but the
  notifications layer is not ours to suspend. Upstream fix needed in
  `pysepal/solara/notifications/notification_ui.py` (lower z-index below 202,
  or expose a `suspend()`/`resume()` API).
- **Top-N basins cap** is applied only at seeding time. If the user expands the
  Catchments multi-select to include more than `MAX_CATCH_DISPLAY` basins, pies
  and bars will render all of them (may be visually crowded). No automatic
  "Others" fold yet.
- **Tests cover pure helpers only.** `_sync_delineation`, `_sync_stats`, and the
  modal/dialog wiring have no unit coverage. No end-to-end Solara component test.

## Bundle-level context

See `/home/dguerrero/1_modules/sepal-gee-bundle/CLAUDE.md` for:
- Repo structure and architecture rules (no cross-app imports, pysepal is the
  shared layer, ruff + pre-commit).
- Conda env name (`sepal-gee-bundle`), `pyproject.toml` as source of truth.
- Git rules (never commit to `release`; feature branches + PRs to `main`).

## Legacy reference

`~/1_modules/basin-rivers/` — original sepal_ui / plotly implementation. Still
useful for algorithmic questions and for the legacy colour translation
(`component/parameter/app.py:gfc_translation`). Do not copy its UI code.
