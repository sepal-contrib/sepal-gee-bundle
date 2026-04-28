# `apps/_commons` — shared primitives

Pure constants and pure functions reused by ≥2 apps in the bundle. **No
state, no I/O, no UI components, and no imports from `apps/<app_name>/`.**

## Modules

- `datasets.py` — single source of truth for GEE dataset / sensor IDs that
  ≥2 apps share (Hansen GFC, JRC TMF, Landsat C02 family, Sentinel-2,
  ALOS PALSAR, HydroSHEDS). Per-app palettes and class codes stay in each
  app's own `params.py`.
- `dataset_check.py` — CLI / module entry point that probes the live
  Earth Engine catalog for newer versions and emits a markdown or JSON
  report (`python -m apps._commons.dataset_check [--json]`).
- `gfc.py` — GFC-domain primitives (palette, SLD, legend, classification).
  Re-exports `GFC_DATASET` / `GFC_MAX_YEAR` from `datasets.py`.

## Adding a new shared dataset

1. Add a `DatasetDescriptor` to `datasets.py`. Pick a probe strategy:
   - `version_pattern` — the asset id has a `{year}` (and optional
     `{minor}`) placeholder, and a new snapshot replaces the previous one.
   - `year_in_collection` — the collection grows by adding new images
     keyed on a `year` property (e.g. ALOS).
   - `static` — single asset id; the checker confirms it still resolves
     and flags `STALE_REVIEW` when the descriptor has not been
     human-reviewed for 180 days.
2. Re-export concrete constants near the bottom of `datasets.py`
   (`HANSEN_GFC_ID = ...`).
3. Add the descriptor to the `REGISTRY` tuple.
4. Update consumers to import from `apps._commons.datasets`.
5. Run `pytest tests/_commons -v` to confirm shape tests still pass.

## Adding a new Landsat platform

Edit `LANDSAT_PLATFORMS` in `datasets.py`. The C02 path templates
(`LANDSAT/{code}/C02/T1_TOA` and `T1_L2`) are shared, so a new platform
is one entry plus the band map (re-use `_LANDSAT_BANDS_NEW` for OLI-class
sensors).

## Running the staleness checker

Locally (requires Earth Engine credentials in the conda env):

```bash
conda run -n sepal-gee-bundle python -m apps._commons.dataset_check
conda run -n sepal-gee-bundle python -m apps._commons.dataset_check --json
```

Exit codes: `0` all green, `1` any non-OK, `2` auth or probe error.

## CI

`.github/workflows/dataset-check.yml` runs the checker weekly. Authentication
uses the `GEE_SERVICE_ACCOUNT_KEY` repo secret (paste the JSON of an EE-enabled
service account). When the run is non-zero, a single tracking issue titled
`[dataset-check] staleness report` is opened or updated; when everything
returns to OK, that issue is closed automatically.
