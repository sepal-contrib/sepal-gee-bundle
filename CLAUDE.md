# CLAUDE.md — sepal-gee-bundle

## Purpose

Bundle of lightweight GEE-based SEPAL applications sharing a single Solara container. Four independent apps served from one Docker image via separate routes.

## Routes

| Route | App | Legacy Repo | Description |
|-------|-----|-------------|-------------|
| `/fcdm` | Forest Canopy Disturbance Monitoring | [sepal-contrib/fcdm](https://github.com/sepal-contrib/fcdm) | Delta-NBR spectral change detection for forest disturbance |
| `/basin-rivers` | Basin Rivers | [sepal-contrib/basin-rivers](https://github.com/sepal-contrib/basin-rivers) | Upstream watershed delineation + forest change stats (HydroSHEDS + Hansen GFC) |
| `/gfc` | Global Forest Change | [sepal-contrib/gfc_wrapper_python](https://github.com/sepal-contrib/gfc_wrapper_python) | Hansen forest mask visualization and export |
| `/coverage-analysis` | Coverage Analysis | [sepal-contrib/coverage_analysis](https://github.com/sepal-contrib/coverage_analysis) | Satellite imagery coverage and NDVI statistics |
| `/tmf-sepal` | Tropical Moist Forests | [sepal-contrib/tmf_sepal](https://github.com/sepal-contrib/tmf_sepal) | JRC TMF Degradation / Deforestation / Annual Change visualization and export |
| `/alos-mosaics` | ALOS PALSAR mosaics | [sepal-contrib/alos_mosaics](https://github.com/sepal-contrib/alos_mosaics) | JAXA ALOS PALSAR / PALSAR-2 yearly mosaics + FNF visualization and export |

## Architecture Rules

- **Independent apps** — no shared UI or state between routes. Each app has its own `page.py`, `model.py`, `components/`, and `scripts/`.
- **No cross-app imports of UI or state** — apps must never import another app's `page.py`, `model.py`, or `components/`. State and UI stay independent.
- **Shared pure logic lives in `apps/_commons/`** — pure constants and pure functions (dataset IDs, class codes, color palettes, classification helpers, SLD builders, legend templates) belong here, not duplicated across apps. No state, no I/O, no UI components, and `_commons` must never import from `apps/<app_name>/`.
- **Promote stable commons to pysepal** — once a `_commons` module is field-tested and reusable beyond this bundle, graduate it into `pysepal` (e.g. `pysepal.gee.gfc`).
- **`pyproject.toml` is the dependency source of truth** — no `requirements.txt`.
- **Follow the `pysepal-app` skill** for all component, state, GEE, layout, ipyvuetify, logging, and i18n patterns. That skill is the single source of truth for how pysepal apps are built.
- **User workspace files go through `SepalClient`** — container apps must use the session `get_current_sepal_client()` / `SepalClient` for runtime user-file reads, writes, directory creation, and listing. Do not use `Path`, `os`, `shutil`, `glob`, or `open()` for SEPAL user workspace data; the container filesystem is only for app code and bundled read-only assets.

## Migration Strategy

Each app is being migrated from a legacy sepal_ui/traitlets repo into this Solara bundle. The approach:

- **Preserve functionality, not code** — we keep the GEE algorithms, datasets, parameters, and user workflows. We throw away the old GUI architecture entirely.
- **Use the `pysepal-app` skill** to scaffold each app's UI. Invoke it before building any app page.
- **Per-app CLAUDE.md** — each `apps/<name>/CLAUDE.md` documents the app's purpose, workflow, GEE logic, parameters, and which legacy scripts are worth preserving.
- **Scripts go in `apps/<name>/scripts/`** — pure functions that take `gee_interface` + parameters and return results. No UI imports, no traitlets, no side effects.
- **Legacy repos** are at `~/1_modules/{fcdm,basin-rivers,gfc_wrapper_python,coverage_analysis}/` for reference.

## Code Quality

### Ruff

Use `ruff` for linting and formatting. Configuration lives in `pyproject.toml`.

### Pre-commit

Use `pre-commit` with at minimum ruff hooks. Configuration lives in `.pre-commit-config.yaml`.

### Modular Design

- **Components are small and reusable** — one Solara component per file, one concern per component. No monolithic tiles.
- **Scripts are pure functions** — GEE processing functions take explicit inputs and return results. No global state, no UI dependencies.
- **State is a flat dataclass-like object** — `solara.reactive()` fields grouped in an AppState class per app. No nested models, no computed traitlets.
- **Separate concerns**: `page.py` (layout + wiring), `model.py` (state), `scripts/` (GEE logic), `components/` (reusable UI widgets if needed).

## Development Environment

- **Conda env name**: `sepal-gee-bundle`
- **Always use the conda env** — never system Python or `pip install --user`.
- Install: `conda create -n sepal-gee-bundle python=3.12 pip -c conda-forge`
- Install project + dev deps: `conda run -n sepal-gee-bundle pip install -e ".[dev]"`
- Run tests: `conda run -n sepal-gee-bundle pytest tests/ -v`
- Run ruff: `conda run -n sepal-gee-bundle ruff check . && conda run -n sepal-gee-bundle ruff format .`

## Project Structure

```
sepal-gee-bundle/
├── app.py                          # Entry point: routes + Solara setup
├── pyproject.toml                  # Dependencies (source of truth)
├── sepal_environment.yml           # Conda env (pip: -e .)
├── .pre-commit-config.yaml         # ruff lint+format, trailing whitespace, etc.
├── .env.example                    # Template for local dev config
├── Dockerfile                      # micromamba + supervisord
├── docker-compose.yml
├── supervisord.conf                # Runs solara with --root-path=/api/app-launcher/sepal-gee-bundle
├── run_solara.sh                   # Local dev launcher (reads .env)
├── logging_config.toml
├── .env                            # Local dev config (not committed)
├── tests/
│   ├── conftest.py                 # Shared fixtures (mock_gee_interface, etc.)
│   └── apps/{gfc,basin_rivers,coverage_analysis,fcdm}/
├── apps/
│   ├── _commons/                   # Shared pure-logic primitives (no state, no UI)
│   │   └── gfc.py                  # GFC dataset id, class codes, palette, SLD, legend, classify_gfc
│   ├── gfc/                        # ✅ MIGRATED
│   │   ├── CLAUDE.md
│   │   ├── page.py                 # GfcPage — wired to components
│   │   ├── model.py                # GfcState — aoi, treecover, year_start/end, result_image
│   │   ├── params.py               # Dataset ID, class codes, colors, SLD styling
│   │   ├── logging_config.toml
│   │   ├── components/
│   │   │   ├── aoi_step.py         # AoiView wrapper
│   │   │   ├── params_step.py      # Threshold + year range + visualize button
│   │   │   └── results_step.py     # Stats table + loss chart + export
│   │   └── scripts/
│   │       ├── gfc_classification.py  # classify_gfc() — .where() chain
│   │       └── statistics.py          # compute_area_stats() + parse_area_stats()
│   ├── fcdm/                       # ⬜ STUB — pending migration
│   │   ├── CLAUDE.md
│   │   ├── page.py
│   │   ├── model.py
│   │   ├── logging_config.toml
│   │   └── scripts/
│   ├── basin_rivers/               # ⬜ STUB — pending migration
│   │   ├── CLAUDE.md
│   │   ├── page.py
│   │   ├── model.py
│   │   ├── logging_config.toml
│   │   └── scripts/
│   └── coverage_analysis/          # ⬜ STUB — pending migration
│       ├── CLAUDE.md
│       ├── page.py
│       ├── model.py
│       ├── logging_config.toml
│       └── scripts/
```

## Migration Status

| App | Status | What's done | What's missing |
|-----|--------|-------------|----------------|
| **GFC** | ✅ Done | Model, params, scripts (classification + stats), components (aoi, params, results), page wired, tests (8 passing) | Live GEE testing |
| **Basin Rivers** | ⬜ Pending | CLAUDE.md with legacy analysis, stub page/model | params, scripts (watershed, gfc, stats, viz), components (point, params, delineation, dashboard), page wiring, tests |
| **Coverage Analysis** | ⬜ Pending | CLAUDE.md with legacy analysis, stub page/model | params (C01→C02 migration), scripts (cloud masking, collection builder, analysis, export), components, page wiring, tests |
| **FCDM** | ⬜ Pending | CLAUDE.md with legacy analysis, stub page/model | params (C01→C02 migration), scripts (forest mask, cloud masking, collection builder, NBR pipeline), components, page wiring, tests |
| **TMF SEPAL** | ✅ Done | Model, params, scripts (`build_tmf_image`, `viz_params_for`), components (aoi, params, export), page wired, tests (pure params/viz/legend) | Live GEE testing; confirm `v1_2023` asset availability for the running EE user |

Migration order: GFC ✅ → Basin Rivers → Coverage Analysis → FCDM

## Bundle-Specific Conventions

This project adapts the standard pysepal structure for a multi-app bundle:

- Each app lives under `apps/<app_name>/` (instead of the single-app `component/` tree).
- Each app has its own `page.py`, `model.py`, and `scripts/`.
- The entry point is `app.py` which registers all routes, not a per-app `solara_app.py`.
- **Apps are fully independent** — no shared navigation, no tabs. Each app is accessed directly by URL.
- **Routing**: `app.py` uses flat `solara.Route` entries with `layout=NoNavLayout` to suppress Solara's default tab navigation. Each route maps directly to an app page component.
- **SepalMap**: always use `SepalMap(gee_interface=gee_interface, fullscreen=True, theme_toggle=theme_toggle)`.
- **`starlette<1.0`** is pinned in `pyproject.toml` — solara is not yet compatible with Starlette 1.0.
- **`SOLARA_TEST=true`** in `.env` for local dev — bypasses SEPAL header auth, uses local EE credentials.

## Adding a New App

1. Create `apps/<app_name>/` with `__init__.py`, `page.py`, `model.py`, `scripts/__init__.py`
2. Follow the `pysepal-app` skill patterns for page component, state, and layout
3. Add one route line to `app.py`:
   ```python
   solara.Route(path="<route>", component=NewPage, layout=NoNavLayout)
   ```
4. Register in app-launcher's `apps.json` if it needs its own entry

## Running Locally

```bash
# With conda
conda activate sepal-gee-bundle
./run_solara.sh

# Or directly
solara run app.py --port 8765 --no-open
```

Apps available at `http://localhost:8765/fcdm`, `/basin-rivers`, `/gfc`, `/coverage-analysis`.

## Docker

```bash
docker compose build
docker compose up -d
```

Container exposes port 8765 with `--root-path=/api/app-launcher/sepal-gee-bundle` (matches the SEPAL gateway prefix used by app-launcher).

## Git Rules

- Never commit directly to `release` — use feature branches + PRs to `main`.
- Never push unless explicitly told to.
- Always check current branch before committing: `git branch --show-current`.

## Key References

- **pysepal source**: `~/1_modules/pysepal/` — Solara components, GEEInterface, session management
- **sbae-design**: `~/1_modules/sbae-design/` — reference Solara app (MapApp + right panel pattern)
- **spatial-risk**: `~/1_modules/spatial-risk-module/` — another reference (single right panel with internal tabs)
- **Design spec**: `docs/specs/2026-03-27-sepal-gee-bundle-design.md`
- **Legacy repos**: See Routes table above for original module source code
