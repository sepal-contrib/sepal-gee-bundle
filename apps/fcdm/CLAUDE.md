# FCDM — Forest Canopy Disturbance Monitoring

> Read the bundle CLAUDE at `/home/dguerrero/1_modules/sepal-gee-bundle/CLAUDE.md`
> and invoke the `pysepal` skill before editing. This file only documents
> fcdm-specific decisions and traps.

## Status

Migration **initial scaffold complete**. 21 pytest passing, ruff clean. Route
registered at `/fcdm`. Needs live GEE smoke test.

## Purpose

Detect forest canopy disturbance using Delta relative Normalized Burn Ratio
(Delta-rNBR) spectral change detection between a reference period and an
analysis period.

## User workflow

1. Select an **Area of Interest** (AoiView, `methods=["-SHAPE", "-POINTS"]`).
2. **Forest mask & sensors** — Hansen GFC / JRC TMF Roadless / no mask, plus
   multi-select sensors (Landsat 4/5/7/8, Sentinel-2).
3. **Dates & parameters** — reference and analysis date ranges, cloud buffer,
   kernel radius, DDR filter threshold/radius/offset.
4. **Run & export** — single task runs `run_fcdm(...)` to produce a
   `FcdmResult` (forest mask, reference/analysis rNBR, delta rNBR raw and
   DDR-filtered). Adds the AOI, forest mask and Delta-rNBR to the map.
   `ExportLauncher` exposes five image sources (delta filtered/raw,
   reference/analysis rNBR, forest mask).

## GEE datasets (migrated to C02)

| Sensor | TOA | SR |
|---|---|---|
| Landsat 4 | `LANDSAT/LT04/C02/T1_TOA` | `LANDSAT/LT04/C02/T1_L2` |
| Landsat 5 | `LANDSAT/LT05/C02/T1_TOA` | `LANDSAT/LT05/C02/T1_L2` |
| Landsat 7 | `LANDSAT/LE07/C02/T1_TOA` | `LANDSAT/LE07/C02/T1_L2` |
| Landsat 8 | `LANDSAT/LC08/C02/T1_TOA` | `LANDSAT/LC08/C02/T1_L2` |
| Sentinel-2 | `COPERNICUS/S2_HARMONIZED` | `COPERNICUS/S2_SR_HARMONIZED` |
| Hansen GFC | — | `UMD/hansen/global_forest_change_2024_v1_12` |
| JRC TMF | — | `projects/JRC/TMF/v1_2024/AnnualChanges` |

## File layout

```
apps/fcdm/
├── page.py                      # NotificationProvider + SepalMap + MapApp + 4-section right panel
├── model.py                     # FcdmState — flat reactives
├── params.py                    # Datasets, SENSORS band map (C02), defaults, viz
├── components/
│   ├── aoi_step.py              # AoiView with SHAPE/POINTS excluded
│   ├── forest_step.py           # forest mask source + GFC threshold + sensor multi-select
│   ├── params_step.py           # date fields + cloud/kernel/DDR sliders
│   └── run_step.py              # TaskButton + ExportLauncher; clears old layers on run
└── scripts/
    ├── forest_mask.py           # get_forest_mask — GFC / roadless / no_map / custom asset
    ├── cloud_masking.py         # QA_PIXEL-based Landsat + SCL-based S2 + iforce_pino_step1 preserved
    ├── collection.py            # build_collection — SR+TOA join for Landsat, cloud + forest masks
    └── nbr_pipeline.py          # compute_nbr, adjustment_kernel, capping, ddr_filter, run_fcdm
```

## Algorithm notes

- `run_fcdm` is a pure GEE graph builder: **no `.getInfo()`** inside. The
  expensive `getInfo()` on collection size from the legacy `launch_tile.py`
  is intentionally dropped — we don't block on collection emptiness any more.
  If needed, re-add via `await gee_interface.get_info_async(coll.size())` in
  the component.
- DDR filter and adjustment kernel preserved verbatim from legacy.
- `iforce_pino_step1` (JRC Sentinel-2 L1C cloud masking, Dario Simonetti) is
  kept in `cloud_masking.py` for future use but the default S2 masker is
  `masking_sentinel2_sr` (SCL band) because we default to `S2_SR_HARMONIZED`.
  IFORCE step2 was dropped — it required per-scene median composites that
  weren't used by the active pipeline.

## Legacy file mapping

| Legacy | New location |
|---|---|
| `component/parameter/dataset.py` | `params.py` (HANSEN_GFC, JRC_ROADLESS) |
| `component/parameter/sensors.py` | `params.py` SENSORS (C02 bands) |
| `component/parameter/ui_input.py` | `params.py` (FOREST_MAP_ITEMS, defaults) |
| `component/parameter/viz_params.py` | `params.py` (viz_forest_mask, DELTA_NBR_VIS) |
| `component/scripts/process_scripts.py` | split across `scripts/forest_mask.py`, `scripts/cloud_masking.py`, `scripts/collection.py`, `scripts/nbr_pipeline.py` |
| `component/tile/launch_tile.py` | `components/run_step.py` + `scripts/nbr_pipeline.run_fcdm` |
| `component/tile/sensor_tile.py` | `components/forest_step.py` |
| `component/tile/time_tile.py` | `components/params_step.py` |
| `component/tile/fcdm_tile.py` | `components/params_step.py` (parameters section) |
| `component/tile/basemap_tile.py` | dropped — basemap handled by SepalMap |
| `component/tile/questionnaire_tile.py` | dropped — replaced by steps + multi-select |
| `component/tile/result_tile.py` | `components/run_step.py` (ExportLauncher) |
| custom `ExportMap` widget | `pysepal.solara.components.export.ExportLauncher` |

## Known caveats for the user to verify live

- **C01 → C02 band renames**: Landsat SR band names changed. The pipeline
  reads `SR_B1..7`, `QA_PIXEL`, `ST_B6`/`ST_B10` instead of `B1..7`, `pixel_qa`,
  `B6`/`B10`. `simpleCloudScore` still comes from the TOA asset and is joined
  on `system:index` unchanged.
- **QA_PIXEL mask simplified**: legacy code used pixel_qa bits 3/5/6/7/8 + a
  separate `sr_cloud_qa` bit-4 shadow check. C02 has no `sr_cloud_qa`; we
  now mask on QA_PIXEL bits 1 (dilated cloud), 2 (cirrus), 3 (cloud),
  4 (cloud shadow). The `unsure_clouds` branch was dropped — revisit if
  users find the new mask too permissive.
- **Sentinel-2 L2A only**: default S2 source is `S2_SR_HARMONIZED` with the
  SCL masker. `iforce_pino_step1` is preserved if you want to switch to TOA.
- **Export scale**: all image exports default to 30 m. Sentinel-2 only
  should use 10 m — consider exposing a per-source scale later.
- **No blocking collection-size check**: the legacy UI raised if either
  reference or analysis collections were empty. The new pipeline is
  lazy — an empty collection produces a masked image and surfaces as
  "no tiles on the map" at visualization time. Rerun or change dates.

## Follow-ups

- Expose a custom-asset forest-mask option in the UI (state field
  `forest_map_asset` exists but no widget wires it yet).
- Add an ipecharts summary (area of detected disturbance by class) — not
  in the legacy but useful. Use `ipecharts`, not matplotlib.
- Add zonal statistics + CSV export (mirror basin_rivers dashboard
  pattern) if demand materialises.

## Legacy reference

`/home/dguerrero/1_modules/fcdm/` — original sepal_ui module. Useful for
algorithmic questions. Don't copy UI code.
