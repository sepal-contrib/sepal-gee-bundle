# Coverage Analysis — Satellite Imagery Coverage & NDVI Statistics

## Purpose

Analyze satellite imagery availability and quality over an AOI. Computes cloud-free pixel counts, total scene coverage, NDVI median, and NDVI standard deviation across Landsat and Sentinel-2 collections. Supports full-period and annual temporal aggregation.

## User Workflow

1. **Select AOI** — draw or upload an area of interest
2. **Configure sensors & dates** — select sensors (L4/L5/L7/L8/S2), date range, surface reflectance vs TOA, include Tier 2 toggle
3. **Choose measure** — cloud-free pixel count, total pixel count, NDVI median, or NDVI std dev
4. **Run analysis** — computes coverage/NDVI image(s), displays on map
5. **Export** — export to GEE asset or download to SEPAL as GeoTIFF; options for total or annual aggregation

## GEE Datasets

- **Landsat 4/5/7/8**: C01 T1 SR and TOA collections (+ optional T2)
- **Sentinel-2**: `COPERNICUS/S2` (TOA) and `COPERNICUS/S2_SR`
- **S2 Cloud Probability**: `COPERNICUS/S2_CLOUD_PROBABILITY` (joined with S2 for cloud masking)

**Note**: All Landsat collections use deprecated C01. Migration should consider upgrading to C02.

## Core Algorithm

### Collection Building
1. For each selected sensor, create filtered ImageCollection (bounds + dates)
2. Optionally merge Tier 2 data
3. Apply sensor-specific cloud masking:
   - **Landsat SR**: pixel_qa bitwise cloud/shadow extraction
   - **Landsat TOA**: BQA bitwise extraction
   - **Sentinel-2**: s2cloudless probability threshold (CLD_PRB_THRESH=30) with optional shadow detection via directional distance transform
4. Add NDVI band: `normalizedDifference(NIR, Red)` with sensor-appropriate band names
5. Merge all sensor collections

### Measures
- **pixel_count**: count of cloud-free observations per pixel (`.count()`)
- **pixel_count_all**: count of all observations including cloudy (total scene coverage)
- **ndvi_median**: median NDVI across cloud-free observations
- **ndvi_stdDev**: standard deviation of NDVI

### Temporal Modes
- **Total**: single composite over the full date range
- **Annual**: split into per-year composites

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `start` | — | Start date |
| `end` | — | End date |
| `sensors` | [] | Selected sensors: l4, l5, l7, l8, s2 |
| `sr` | False | Use Surface Reflectance (True) or TOA (False) |
| `t2` | False | Include Tier 2 imagery |
| `measure` | pixel_count | What to compute |
| `annual` | False | Annual vs full-period aggregation |
| `scale` | 30 | Export scale in meters |
| `stats` | [count] | Which statistics to export |
| `temps` | [total_exp] | Temporal aggregation for export |

## Outputs

- **Map layers**: coverage/NDVI images per year or total, with colorbar
- **GEE Asset export**: image exported to user's GEE asset folder
- **SEPAL download**: GeoTIFF via Drive → download → merge tiles
- **Visualization**: color-mapped layers on SepalMap

## Scripts Worth Preserving

- `bfast_preanalysis.analysis` — collection building with multi-sensor merging (the core data pipeline)
- `cloud_masking.cloud_mask_S2` — s2cloudless-based masking
- `cloud_masking.cloud_mask_S2_SR` — full shadow detection with directional distance transform
- `helpers.create_collection` — Landsat collection creation with T2 merge and cloud masking
- `helpers.addNDVI*` — per-sensor NDVI band addition

## Migration Notes

- The collection building logic is scattered across `bfast_preanalysis.py` and `helpers.py` — consolidate into cleaner functions
- Cloud masking has two S2 methods (`cloud_mask_S2` simple, `cloud_mask_S2_SR` full with shadow) — the SR version is more complete
- Export flow uses the same GEE → Drive → SEPAL pattern as GFC — replace with pysepal export
- The `display.py` module manually manages map layers; replace with SepalMap patterns
- Landsat C01 collections need upgrading to C02
- `bfast_preanalysis` name is misleading — it's really just "build a multi-sensor collection"
