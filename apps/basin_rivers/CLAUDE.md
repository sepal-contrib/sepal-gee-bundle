# Basin Rivers — Upstream Watershed Delineation

## Purpose

Identify upstream watersheds from a user-selected point and compute forest change statistics per sub-catchment using WWF HydroSHEDS basins and Hansen GFC data.

## User Workflow

1. **Select pour point** — click on map or enter lat/lon manually
2. **Configure basin parameters** — HydroSHEDS level (5-12), year range, tree cover threshold
3. **Delineate upstream basins** — app traces upstream from the pour point through HydroSHEDS network
4. **Select catchments** — view all upstream catchments or filter specific sub-basins
5. **Compute statistics** — forest change zonal stats per catchment (loss by year, gain, stable forest, non-forest)
6. **View dashboard** — pie charts, bar charts, and tables of forest change per basin

## GEE Datasets

- **WWF HydroSHEDS**: `WWF/HydroSHEDS/v1/Basins/hybas_{level}` — levels 5-12
- **Hansen GFC**: `UMD/hansen/global_forest_change_2023_v1_11` — tree cover 2000, loss year, gain

## Core Algorithm

### Upstream Basin Delineation
1. Filter HydroSHEDS basin collection to the selected level
2. Find the basin containing the pour point
3. Iteratively trace upstream: for each basin, find all basins whose `NEXT_DOWN` matches current `HYBAS_ID`
4. Repeat up to 100 steps until no more upstream basins found
5. Merge all found basins into a single FeatureCollection

### Forest Change Classification
Given year range [start, end] and tree cover threshold:
- **Non-forest** (30): tree cover <= threshold and no gain; OR tree cover > threshold but loss before start year
- **Stable forest** (40): tree cover > threshold, no loss (or loss after end year)
- **Gain** (50): tree cover <= threshold with gain=1
- **Gain+Loss** (51): tree cover > threshold, gain=1, loss within [start, end]
- **Loss by year** (1-20+): tree cover > threshold, no gain, loss year within [start, end] — value = loss year

### Zonal Statistics
- `ee.Image.pixelArea()` divided by 10000 (to hectares)
- `reduceRegions` with `ee.Reducer.sum().group(1)` on the forest change image
- Grouped by change class, aggregated per `HYBAS_ID`

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lat/lon` | — | Pour point coordinates |
| `level` | 8 | HydroSHEDS basin level (5-12, higher = smaller catchments) |
| `years` | [2010, 2020] | Analysis year range |
| `thres` | 80 | GFC tree cover threshold (%) |
| `method` | — | "all" upstream or "filter" specific basins |

## Outputs

- **Map layers**: colored upstream catchments, pour point marker
- **Statistics**: per-catchment forest change areas in hectares
- **Dashboard**: grouped pie chart (by change class), bar charts, catchment comparison
- **Data**: zonal statistics DataFrame with basin ID, change class, area, year, colors

## Scripts Worth Preserving

- `get_upstream_basin_ids` — the iterative upstream tracing algorithm (core value of the app)
- `get_gfc` — forest change classification logic
- `calculate_statistics` — zonal stats with `reduceRegions` + group reducer
- `get_dataframe` / `get_overall_pie_df` — result parsing to pandas

## Migration Notes

- The upstream tracing uses `ee.List.sequence().iterate()` which is a known GEE anti-pattern for large watersheds — consider if there's a cleaner approach
- Basin coloring uses random colors; could be improved with deterministic palette
- Dashboard uses seaborn/plotly for charts — replace with appropriate Solara visualization
- The model mixes GEE logic with UI state; separate cleanly in migration
