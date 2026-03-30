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

## Architecture Rules

- **Fully independent apps** — no shared state between routes. Each app has its own `page.py`, `model.py`, and `scripts/`.
- **No cross-app imports** — apps must never import from each other. pysepal is the shared layer.
- **Pure Solara reactive** — use `solara.reactive()` for all state. No traitlets, no `observe()`, no `Model` base class.
- **GEEInterface async only** — all GEE calls go through `gee_interface` via `asyncio.to_thread()`. Never call `ee.*` directly in components. Never `await` GEEInterface async methods directly (cross-loop RuntimeError).
- **pysepal components only** — use `AoiView`, `AssetSelectComponent`, `SepalMap`, `MapApp`, etc. from pysepal. Do not invent or duplicate components that already exist in pysepal.
- **Right-side panel** — workflow steps go in `right_panel_content`, not `steps_data` (left drawer). Follows the sbae-design / spatial-risk pattern.
- **`pyproject.toml` is the dependency source of truth** — no `requirements.txt`.

## Project Structure

```
sepal-gee-bundle/
├── app.py                          # Entry point: routes + Solara setup
├── pyproject.toml                  # Dependencies (source of truth)
├── sepal_environment.yml           # Conda env (pip: -e .)
├── Dockerfile                      # micromamba + supervisord
├── docker-compose.yml
├── supervisord.conf                # Runs solara with --root-path=/sepal-gee-bundle
├── run_solara.sh                   # Local dev launcher
├── logging_config.toml
├── .env                            # Local dev config (not committed)
├── apps/
│   ├── fcdm/
│   │   ├── page.py                 # FcdmPage — @solara.component
│   │   ├── model.py                # FcdmState — solara.reactive() fields
│   │   └── scripts/                # GEE processing functions
│   ├── basin_rivers/
│   │   ├── page.py
│   │   ├── model.py
│   │   └── scripts/
│   ├── gfc/
│   │   ├── page.py
│   │   ├── model.py
│   │   └── scripts/
│   └── coverage_analysis/
│       ├── page.py
│       ├── model.py
│       └── scripts/
```

## Page Component Pattern

Every app page follows this skeleton:

```python
@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.<app_name>")
def AppPage():
    setup_theme_colors()
    theme_toggle = ThemeToggle()
    gee_interface = get_current_gee_interface()

    state = solara.use_memo(lambda: AppState(), [])
    sepal_map = solara.use_memo(
        lambda: SepalMap(gee_interface=gee_interface), [id(gee_interface)]
    )

    MapApp.element(
        app_title="...",
        main_map=[sepal_map],
        steps_data=[],
        right_panel_config={...},
        right_panel_content=[...],
        right_panel_open=True,
        theme_toggle=[theme_toggle],
    )
```

## GEE Task Pattern

GEE scripts are pure functions that receive `gee_interface` and return results. They run via `asyncio.to_thread()` inside `@solara.lab.use_task`:

```python
# In scripts/process.py
def compute_something(gee_interface, aoi, **params):
    import ee
    # ee.* calls are fine here — runs in gee_interface's thread
    image = ee.Image("...").clip(aoi)
    return gee_interface.get_info(image)

# In page.py
@solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=True)
async def run_analysis():
    result = await asyncio.to_thread(compute_something, gee_interface, state.aoi.value)
    state.result.set(result)
```

## ipyvuetify Rules

- Inside `with rv.Something():` context managers, always use `rv.Widget(...)`, never `v.Widget(...)` (silent failure).
- Do not use `with solara.Column():` inside `rv.` contexts — it captures children into its own tree.
- For `rv.Dialog` inside MapApp right panel, always add `eager=True`.

## Adding a New App

1. Create `apps/<app_name>/` with `__init__.py`, `page.py`, `model.py`, `scripts/__init__.py`
2. Follow the page component pattern above
3. Add one route line to `app.py`:
   ```python
   solara.Route(path="<route>", component=NewPage, label="Label")
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

Container exposes port 8765 with `--root-path=/sepal-gee-bundle`.

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
