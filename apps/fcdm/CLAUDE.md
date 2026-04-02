# FCDM — Forest Canopy Disturbance Monitoring

## Purpose

Detect and map forest canopy disturbances using Delta-rNBR (relative Normalized Burn Ratio) spectral change detection. Compares a reference period against an analysis period to identify where forest canopy has been disturbed.

## User Workflow

1. **Select AOI** — draw or upload an area of interest
2. **Configure forest mask** — choose how to define forest: GFC tree cover threshold, JRC Roadless map, no mask, or a custom binary asset
3. **Select sensors** — one or more of: Landsat 4/5/7/8, Sentinel-2
4. **Set date ranges** — a reference period (baseline) and an analysis period (investigation)
5. **Set algorithm parameters** — kernel radius, DDR filter threshold/radius/offset, cloud buffer
6. **Run analysis** — produces Delta-rNBR map on the map
7. **Export** — download selected layers (forest mask, reference rNBR, analysis rNBR, Delta-rNBR)

## GEE Datasets

- **Hansen GFC**: `UMD/hansen/global_forest_change_2020_v1_8` — tree cover 2000, loss year
- **JRC TMF**: `projects/JRC/TMF/v1_2020/AnnualChanges` — Roadless forest map
- **Landsat SR/TOA**: C01 T1 collections for L4, L5, L7, L8
- **Sentinel-2**: `COPERNICUS/S2` (TOA) and `COPERNICUS/S2_SR`

**Note**: Landsat collections use deprecated C01. Migration should consider upgrading to C02.

## Core Algorithm

1. **Forest mask**: built from GFC (tree cover >= threshold, excluding prior loss), JRC Roadless, or custom asset
2. **Cloud masking**: sensor-specific — Landsat uses pixel_qa + simpleCloudScore, Sentinel-2 uses IFORCE/PINO method (JRC, Dario Simonetti) with SCL and spectral rules
3. **NBR computation**: `(NIR - SWIR2) / (NIR + SWIR2)` per scene, plus yearday band
4. **Adjustment kernel**: self-referencing via focal median subtraction (configurable radius)
5. **Capping**: clamp NBR to [0, -1], invert sign
6. **Quality mosaic**: condense per-period to single image using `qualityMosaic("NBR")`
7. **Delta-rNBR**: analysis minus reference
8. **DDR filtering**: disturbing-density-related spatial filter — mask pixels without enough disturbance events within a kernel radius

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `forest_map` | `gfc` | Forest mask source: gfc, roadless, no_map, or asset ID |
| `forest_map_year` | 2000 | Year for forest mask baseline |
| `treecover` | 70 | GFC tree cover threshold (%) |
| `sensors` | [] | Selected sensors (multi-select) |
| `cloud_buffer` | 500 | Cloud mask buffer radius (meters) |
| `analysis_start/end` | — | Analysis period date range |
| `reference_start/end` | — | Reference period date range |
| `kernel_radius` | 150 | Adjustment kernel radius (meters, max 1000) |
| `filter_threshold` | 0.035 | DDR disturbance threshold |
| `filter_radius` | 80 | DDR kernel radius (meters, 10-500) |
| `cleaning_offset` | 3 | DDR minimum events per kernel (max 50) |

## Outputs

- **Map layers**: forest mask, reference rNBR, analysis rNBR, Delta-rNBR (palette: grey to red)
- **Export**: GeoTIFF of selected layers via GEE export widget

## Scripts Worth Preserving

The GEE processing logic in the legacy `process_scripts.py` is algorithmically valuable:
- `compute_nbr` — NBR + yearday computation
- `adjustment_kernel` — self-referencing kernel
- `capping` — value normalization
- `ddr_filter` — spatial density filtering
- `get_forest_mask` — forest mask construction from multiple sources
- `get_collection` — collection assembly with cloud + forest masking
- `IFORCE_PINO_step1/step2` — JRC Sentinel-2 cloud masking (Dario Simonetti)
- `masking_1QB`, `masking_L_1`, `masking_S_1` — per-sensor cloud masking
- `masking_2` — sensor error + forest masking

The sensor band mapping in `sensors.py` and viz params in `viz_params.py` are also needed.

## Migration Notes

- Band mappings use Landsat C01 — need updating to C02
- Cloud masking is complex but well-tested; preserve the logic, clean up the code
- The `launch_tile.py` orchestration flow shows the full pipeline end-to-end
- Export uses a custom `ExportMap` widget; replace with pysepal export patterns
