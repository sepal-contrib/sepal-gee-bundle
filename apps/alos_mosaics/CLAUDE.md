# CLAUDE.md — alos_mosaics (sepal-gee-bundle app)

## Purpose

Thin pysepal-Solara wrapper around the **JAXA ALOS PALSAR / PALSAR-2 yearly
mosaics** — lets the user pick an AOI and a year, runs the GEE pipeline
(calibration, optional speckle filter, LS mask, dB conversion, RFDI, GLCM
texture, optional FNF band), renders the chosen layer on the map, and
exports the selected bands to GEE / Drive / SEPAL via `ExportLauncher`.

Migrated from https://github.com/sepal-contrib/alos_mosaics — only the GEE
algorithm and parameters were preserved; all `sepal_ui` / traitlets UI code
was dropped in favour of pysepal / Solara patterns. The legacy repo listed
Planet API as a dependency but nothing in `component/` referenced it, so it
was dropped entirely.

## Workflow

1. **AOI** — `AoiStep` (pysepal `AoiView`, `methods=["-SHAPE", "-POINTS"]`).
2. **Visualization** — pick a year (`ALOS_YEARS`), speckle filter
   (`NONE` / `REFINED_LEE` / `QUEGAN`), toggle LS masking and dB scaling,
   pick `RGB` backscatter / `RFDI` / `FNF` (year ≤ 2017), press *Add layer
   to map*. The mosaic is built on GEE and rendered on the map in one step.
3. **Export** — toggle backscatter / RFDI / texture / aux / FNF bands, then
   use `ExportLauncher` for GEE / Drive / SEPAL targets (native 25 m).

Legend and notifications are wired through pysepal (`LegendComponent`,
`NotificationProvider` + `use_notifications`).

## GEE datasets

| Product | Collection | Notes |
|---------|-----------|-------|
| Yearly SAR mosaic | `JAXA/ALOS/PALSAR/YEARLY/SAR` | HH, HV, angle, date, qa |
| Yearly FNF | `JAXA/ALOS/PALSAR/YEARLY/FNF` | 1 = forest, 2 = non-forest, 3 = water. Discontinued after 2017. |

Years available: `2007, 2008, 2009, 2010, 2015, 2016, 2017, 2018, 2019, 2020`.

## Algorithm

`scripts/kc_mosaic.build_alos_mosaic` — ports the legacy `create()` function
line-for-line, minus the `output.add_live_msg` UI call:

1. Load the SAR collection, calibrate DN → gamma-naught, resample.
2. If `speckle_filter == QUEGAN`, apply the multi-temporal Quegan filter
   **on the collection**.
3. Filter the collection to the target year and pick the `.first()` image.
4. If `speckle_filter == REFINED_LEE`, apply Guido Lemoine's Refined Lee
   filter.
5. Optionally mask layover / shadow pixels (`qa == 100 | qa == 150`).
6. Add HH/HV ratio (`HHHV_ratio`) and `RFDI = normalizedDifference(HH, HV)`.
7. Compute GLCM texture (7-window) for HH and HV; add
   `HH_var/HH_idm/HH_diss` and `HV_var/HV_idm/HV_diss`.
8. If `db`, convert HH / HV to dB.
9. If the year is ≤ 2017, add the matching `fnf_<year>` band from the FNF
   collection.
10. `clip(region)`.

`scripts/kc_mosaic.select_viz_bands` + `viz_params_for` reproduce the legacy
`display_result` band/palette logic:

- `RGB + db`  → `VIS_PARAM_DB` on `[HH, HV, HHHV_ratio]`
- `RGB + pow` → `VIS_PARAM_POW` on `[HH, HV, HHHV_ratio]`
- `RFDI`      → `VIS_PARAM_RFDI` on `[RFDI]`
- `FNF`       → `VIS_PARAM_FNF` on `[fnf_<year>]`

`scripts/kc_mosaic.select_export_bands` mirrors the legacy `_select_layers`
in `tile/export.py`: toggles for backscatter / RFDI / texture / aux,
returning a single `ee.Image` (or `None` when no bands selected). FNF is
exported as a separate source when the toggle is on and the year ≤ 2017.

## Parameters (`params.py`)

- `ALOS_SAR_COLLECTION`, `ALOS_FNF_COLLECTION` — dataset IDs.
- `ALOS_YEARS`, `LAST_FNF_YEAR` — valid years.
- `SPECKLE_NONE`, `SPECKLE_REFINED_LEE`, `SPECKLE_QUEGAN` — filter enum.
- `SPECKLE_FILTERS`, `VIZ_LAYERS` — Select / Radio items.
- `VIS_PARAM_DB`, `VIS_PARAM_POW`, `VIS_PARAM_RFDI`, `VIS_PARAM_FNF` —
  visualization params (ported verbatim from legacy `parameter/viz.py`).
- `FNF_CLASSES`, `fnf_legend()`, `rfdi_legend()`, `rgb_legend()` — pysepal
  `LegendData` builders.
- `asset_name(...)` — default filename for exports (matches legacy
  `parameter.values.asset_name`).
- `fnf_available(year)` — convenience predicate.

## File layout

```
apps/alos_mosaics/
├── __init__.py
├── CLAUDE.md              # this file
├── page.py                # AlosMosaicsPage — MapApp + 4-section right panel
├── model.py               # AlosMosaicsState (flat reactives)
├── params.py              # dataset IDs, viz params, legends, naming
├── logging_config.toml
├── components/
│   ├── __init__.py
│   ├── aoi_step.py        # AoiView wrapper (container methods only)
│   ├── visualize_step.py  # year + speckle + ls_mask + db + RGB/RFDI/FNF radio + TaskButton
│   └── export_step.py     # band switches + ExportLauncher (fixed 25 m scale)
└── scripts/
    ├── __init__.py
    ├── _quegan.py         # multi-temporal speckle filter (verbatim)
    ├── _refined_lee.py    # Refined Lee filter (verbatim)
    └── kc_mosaic.py       # build_alos_mosaic, band/viz helpers
```

## Legacy mapping

| Legacy (`alos_mosaics/component/`)                          | Replacement                                              |
|-------------------------------------------------------------|----------------------------------------------------------|
| `model/process.py` (traitlets Model)                        | `apps/alos_mosaics/model.py` (`solara.reactive`)         |
| `parameter/values.py`, `parameter/viz.py`                   | `apps/alos_mosaics/params.py`                            |
| `parameter/directory.py` (SEPAL dirs)                       | Dropped — `ExportLauncher` handles target folders        |
| `scripts/kc_mosaic.py` (`create`)                           | `scripts/kc_mosaic.build_alos_mosaic`                    |
| `scripts/_quegan.py`, `scripts/_refined_lee.py`             | Ported verbatim to `scripts/_quegan.py`, `_refined_lee.py` |
| `scripts/display.py` (`display_result`)                     | `scripts.select_viz_bands` + `viz_params_for` + `visualize_step` |
| `scripts/exports.py` (`export_to_asset`, `export_to_sepal`) | `ExportLauncher` + `ExportSource` / `ResolvedExport`     |
| `scripts/gdrive.py`, `scripts/download.py`                  | Dropped — pysepal export pipeline handles this           |
| `scripts/gee.py`                                            | Dropped — pysepal handles task polling                   |
| `tile/process.py`                                           | Folded into `components/visualize_step.py`                     |
| `tile/visualization.py`                                     | `components/visualize_step.py`                                 |
| `tile/export.py`                                            | `components/export_step.py`                              |

## Caveats & things to verify live

- **Planet API** was listed as a dep in the legacy `module_monitor`; a grep of
  `component/` found zero references. It is NOT included here. If anyone
  later discovers Planet is actually needed, re-audit the legacy `utils/`
  folder.
- **No C01 → C02 migration** — the JAXA ALOS collections are not Landsat
  collections; the dataset IDs are stable.
- **FNF coverage** stops at 2017 (`LAST_FNF_YEAR = 2017`). The viz and
  export UIs disable the FNF toggle for years above that automatically.
- **Export scale** defaults to 25 m (native ALOS resolution).
- **GLCM texture** is computed on power-scaled `int16` bands (legacy
  behaviour). For very large AOIs this can tax the GEE tile quota.
- **Refined Lee / Quegan** are untouched direct ports — reference the
  legacy repo if you need to audit numerics.

## Tests

`tests/apps/alos_mosaics/test_params.py` — pure-Python checks on
`params.py` (dataset IDs, year list, speckle enums, legends, asset naming,
`fnf_available`). No live GEE.

Run:

```bash
conda run -n sepal-gee-bundle pytest tests/apps/alos_mosaics -v
conda run -n sepal-gee-bundle ruff check apps/alos_mosaics tests/apps/alos_mosaics
```
