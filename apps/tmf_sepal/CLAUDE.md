# CLAUDE.md — tmf_sepal (sepal-gee-bundle app)

## Purpose

Thin pysepal-Solara wrapper around the **JRC Tropical Moist Forests (TMF)**
dataset — lets the user pick an AOI and a year range, renders the Degradation,
Deforestation or Annual Change layer on the map, and exports the image to
GEE asset / Google Drive / SEPAL via `ExportLauncher`.

Migrated from https://github.com/sepal-contrib/tmf_sepal — only the GEE
algorithm and parameters were preserved; all `sepal_ui` / traitlets UI code was
dropped in favour of pysepal/Solara patterns.

## Workflow

1. **AOI** — `AoiStep` (pysepal `AoiView`, `methods=["-SHAPE", "-POINTS"]`).
2. **Parameters** — pick a TMF layer (`DEG`/`DEF`/`CHG`/`TRANS`). The year-based
   layers take a start/end year in `1990..TMF_VERSION_YEAR`; the `TRANS`
   TransitionMap is whole-period and hides the year selects. Then click
   *Process & add layer*.
3. **Export** — choose a scale and use `ExportLauncher` to send the TMF image
   (and optionally the AOI boundary) to GEE / Drive / SEPAL.

Legend and notifications are wired through pysepal (`LegendComponent`,
`NotificationProvider` + `use_notifications`).

## GEE datasets

These collections share the `projects/JRC/TMF/v1_<YEAR>/...` prefix.
`TMF_VERSION_YEAR` (from `apps._commons.datasets`) controls which release is
used. Bump it there when the JRC publishes a newer version.

| Type  | Collection                                            | Band schema                                        |
|-------|-------------------------------------------------------|----------------------------------------------------|
| DEG   | `projects/JRC/TMF/v1_<YEAR>/DegradationYear`          | Single band: year of degradation event             |
| DEF   | `projects/JRC/TMF/v1_<YEAR>/DeforestationYear`        | Single band: year of deforestation event           |
| CHG   | `projects/JRC/TMF/v1_<YEAR>/AnnualChanges`            | One `DecYYYY` band per year (1990..`TMF_MAX_YEAR`) |
| TRANS | `projects/JRC/TMF/v1_<YEAR>/TransitionMap_Subtypes`   | Single band: ~84 transition subtype codes (10..94) |

Note: the bundle pins `v1_2025` via `apps._commons.datasets`. If an asset is not
available to the running GEE user, override the pinned year there.

## Algorithm

`scripts/tmf_process.build_tmf_image`:

- `DEG` / `DEF`: `collection.mosaic().clip(aoi)`, then `selfMask()` pixels whose
  year value is in `[year_start, year_end]`.
- `CHG`: compares the start-year class (`Dec<start>`) to the end-year class
  (`Dec<end>`) per pixel and remaps `(start*10 + end)` via
  `TMF_CHG_TRANSITION_REMAP` into a single `transition` band (codes 1..7, see
  `TMF_CHG_TRANSITION_CLASSES`). The map, legend, statistics dashboard, and
  exported asset all describe these 7 transition classes.
  (The legacy `[DecSTART, DecSTART, DecEND]` RGB composite was replaced — it
  could not match a discrete class legend.)
- `TRANS`: loads `TransitionMap_Subtypes`, mosaics, and remaps the ~84 subtype
  codes to the 9 JRC main classes via `TMF_SUBTYPE_TO_MAIN` into a single
  `transition_main` band (1..9, see `TMF_TRANSITION_MAIN_CLASSES`). Whole-period
  (1990..`TMF_VERSION_YEAR`); ignores the year range. Unlisted subtypes are masked.

`scripts/tmf_process.viz_params_for` returns the map visualization params:

- `DEG`/`DEF`: `{min, max, palette=[blue, yellow, red]}` over the year range.
- `CHG`: `{bands=["transition"], min=1, max=7, palette=<transition colors>}` — a
  categorical class map that matches `change_legend()` (the 7 transition classes).
- `TRANS`: `{bands=["transition_main"], min=1, max=9, palette=<official colors>}`
  — categorical, matches `transition_main_legend()` (the 9 JRC main classes).

## Parameters

Defined in `params.py`:

- `TMF_VERSION_YEAR` (default `2023`) — feeds `TMF_MAX_YEAR` and dataset IDs.
- `TMF_MIN_YEAR = 1990`, `TMF_MAX_YEAR = TMF_VERSION_YEAR`.
- `TMF_TYPES` — select items for the layer picker.
- `TMF_YEAR_PALETTE = ["#0000ff", "#ffff00", "#ff0000"]`.
- `TMF_CHG_CLASSES` — the 6 raw per-year AnnualChanges class codes; the inputs
  to the transition remap.
- `TMF_CHG_TRANSITION_CLASSES` / `TMF_CHG_TRANSITION_REMAP` — the 7 start->end
  transition classes (code, label, colour) and the `(start*10+end)->code` remap
  that drive the CHG map layer, its legend, the statistics dashboard, and the
  exported asset's viz.
- `TMF_TRANSITION_MAIN_CLASSES` / `TMF_SUBTYPE_TO_MAIN` — the 9 official JRC
  TransitionMap main classes (idx, label, colour; "Other" white -> grey for
  visibility) and the subtype->main recode used by the `TRANS` layer.
- `year_legend(...)` / `change_legend()` / `transition_main_legend()` — build
  `LegendData` for `LegendComponent` (the year gradient, the 7-class CHG, and the
  9-class TransitionMap legends respectively).
- `asset_basename(aoi_name, tmf_type, y0, y1)` — default export filename.

## File layout

```
apps/tmf_sepal/
├── __init__.py
├── CLAUDE.md              # this file
├── page.py                # TmfSepalPage — MapApp + right panel
├── model.py               # TmfSepalState (flat reactives)
├── params.py              # dataset IDs, viz params, legends
├── logging_config.toml
├── components/
│   ├── __init__.py
│   ├── aoi_step.py        # AoiView wrapper (container methods only)
│   ├── params_step.py     # type + year range + TaskButton → viz_task
│   └── export_step.py     # scale input + ExportLauncher
└── scripts/
    ├── __init__.py
    └── tmf_process.py     # build_tmf_image, viz_params_for (pure GEE)
```

## Legacy mapping

| Legacy (`tmf_sepal/component/`)                       | Replacement                                                |
|-------------------------------------------------------|------------------------------------------------------------|
| `model/process_model.py` (traitlets Model)            | `apps/tmf_sepal/model.py` (`solara.reactive`)              |
| `parameter/values.py`, `parameter/viz.py`             | `apps/tmf_sepal/params.py`                                 |
| `parameter/directory.py` (SEPAL dirs)                 | Dropped — handled by `ExportLauncher`                      |
| `scripts/default_process.py` (`create`)               | `scripts/tmf_process.build_tmf_image`                      |
| `scripts/display.py` (`display_result`)               | `params.viz_params_for` + `params_step` (via SepalMap)     |
| `scripts/exports.py` (`export_to_asset`, `export_to_sepal`) | `ExportLauncher` + `ExportSource`/`ResolvedExport`   |
| `scripts/gdrive.py`, `scripts/download.py`            | Dropped — pysepal export pipeline handles this             |
| `scripts/gee.py` (`wait_for_completion`, `search_task`, `is_asset`) | Dropped — pysepal handles task polling       |
| `tile/process_tile.py`                                | `components/params_step.py`                                |
| `tile/viz_tile.py`                                    | The `MapApp` central map (`SepalMap`)                      |
| `tile/export_tile.py`                                 | `components/export_step.py`                                |

## Caveats & things to verify live

- **TMF version bump** — legacy used `v1_2022`. We default to `v1_2023`. If the
  asset isn't readable by the current EE user, change `TMF_VERSION_YEAR` in
  `params.py`.
- **No C01→C02 migration needed** — the JRC TMF collections are not Landsat
  collections; the `v1_<YEAR>` IDs remain unchanged.
- **CHG bands** use the `Dec<YEAR>` naming convention from the JRC TMF
  AnnualChanges product. Verify the band names on the live asset — older
  versions sometimes rename these.
- **Export scale** defaults to 30 m (TMF native resolution is 30 m).
- **Statistics / tables** — the legacy app didn't compute area stats; we keep
  parity and only visualize + export.

## Dashboard

After `StatsStep` computes stats, a **DashboardStep** button opens a large
modal (`rv.Dialog(max_width="1400px", scrollable=True, eager=True)`) with:

- **SummaryCard** — compact `_StatItem` row: total area (degraded /
  deforested / classified, depending on layer), event year range / classes
  present, user-selected year range, and TMF layer type.
- **OverallPie** — donut of area shares. For **CHG** the slices are the
  seven `TMF_CHG_TRANSITION_CLASSES` (start->end transition classes). For
  **DEG/DEF** the slices are years, coloured along the
  `TMF_YEAR_PALETTE` gradient stretched to the data range. The legend uses
  `type="scroll"` so a wide year range paginates (`‹ … › 1/N`) instead of
  crowding the bottom of the chart.
- **YearTrend** — bar chart of area per year for **DEG/DEF** only (each
  bar tinted via the same year gradient). Hidden for **CHG** because
  stats_rows are keyed by class, not year.
- **Download CSV** — `solara.FileDownload` of the raw `stats_rows`.

### Wiring

- `model.TmfSepalState` grew a `stats_rows: list` reactive.
  `stats_step.py` writes to it when `compute_task` finishes.
- `page.py` passes `legend_visible` and `sepal_map` through to `StatsStep`
  → `DashboardStep`. The dialog hides the legend on open, restores it on
  close.
- The inline `_StatsTable` in `StatsStep` shows the raw numbers without
  opening the modal. The old inline `_StatsPie` donut was removed — the
  by-year/by-class charts now live **only** in the dashboard (no duplicate
  by-year chart in the right panel).
- `params_step`'s *Process & add layer* button clears `stats_rows` on click,
  so stale statistics from a previous layer / year range can't linger in the
  panel or auto-reopen the dashboard with outdated data.
- Auto-opens whenever a fresh `stats_rows` list arrives (watches
  `id(rows)`), matching the gfc / basin-rivers UX.

### Known-trap compatibility

Same rules as gfc / basin-rivers:

- **`_DialogResizer`** — copied verbatim. Bumps `tick` on dialog open to
  fire a `window.resize` event so ECharts re-measures its container.
- **`Option.grid` = `Grid(...)`, never a dict**.
- **No click-to-select on the pie** — incompatible `.on(...)` signature.
- **Every chart `Option` includes `Toolbox(show=True, feature={"saveAsImage": ...})`**.
- **Chart wrapper classes**: `.tmf-echart-overall`, `.tmf-echart-year-trend`.

## Tests

`tests/apps/tmf_sepal/test_params.py` — pure-Python checks on `params.py` and
`scripts.tmf_process.viz_params_for` (no live GEE).

Run:

```bash
conda run -n sepal-gee-bundle pytest tests/apps/tmf_sepal -v
conda run -n sepal-gee-bundle ruff check apps/tmf_sepal tests/apps/tmf_sepal
```
