# sepal-gee-bundle Design Spec

**Date**: 2026-03-27
**Status**: Approved

## Summary

Merge four lightweight GEE-based SEPAL modules (FCDM, Basin Rivers, GFC, Coverage Analysis) into a single Solara application served from one Docker container with multiple routes.

## Motivation

Four simple GEE apps share nearly identical Docker images and dependencies (pysepal, solara, earthengine-api). Running them as separate containers wastes resources. One container with four Solara routes is more efficient.

## Architecture

**Approach**: Package-per-app with shared `app.py` entry point (Approach B from brainstorming).

### Routes

| Route | App | Description |
|-------|-----|-------------|
| `/fcdm` | Forest Canopy Disturbance Monitoring | Delta-NBR disturbance detection |
| `/basin-rivers` | Basin Rivers | Upstream watershed + forest change stats |
| `/gfc` | Global Forest Change | Hansen forest mask visualization/export |
| `/coverage-analysis` | Coverage Analysis | Satellite coverage & NDVI stats |

### Key Decisions

- **No landing page** at `/` — routes accessed directly
- **Fully independent apps** — no shared state between routes
- **Right-side panel** for workflow steps (not left drawer), matching sbae-design/spatial-risk patterns
- **Pure Solara reactive** — no traitlets/observers from legacy code
- **GEEInterface async** — all GEE calls via `gee_interface.create_task()` / `asyncio.to_thread()` (follow-up PRs)
- **pysepal components only** — `AoiView`, `AssetSelectComponent`, `SepalMap`, `MapApp`, etc.

### Project Structure

```
sepal-gee-bundle/
├── app.py                          # Routes + Solara setup
├── pyproject.toml                  # Dependency source of truth
├── sepal_environment.yml           # Conda env
├── Dockerfile                      # micromamba + supervisord
├── docker-compose.yml
├── supervisord.conf
├── run_solara.sh
├── logging_config.toml
├── .env
├── apps/
│   ├── fcdm/
│   │   ├── page.py                 # FcdmPage component
│   │   ├── model.py                # FcdmState (solara.reactive)
│   │   └── scripts/                # GEE processing (follow-up)
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

### Page Component Pattern

Each page follows the same skeleton:

```python
@solara.component
@with_sepal_sessions(module_name="sepal_gee_bundle.<app>")
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

### Docker Stack

- **Base**: `mambaorg/micromamba:latest`
- **Process manager**: supervisord
- **Port**: 8765
- **Root path**: `/sepal-gee-bundle`
- **Conda env**: `sepal-gee-bundle` with Python 3.12
- **Install**: `pip install -e .` from pyproject.toml

### Multi-User Behavior

Each browser tab gets its own Solara kernel. Multiple tabs = multiple GEE sessions. This is identical to the cost of separate containers — the bundling saves container-level overhead, not per-user overhead.

## Scope: Initial PR

- Deployable skeleton — all 4 apps render `MapApp` with empty right-panel sections
- No GEE logic, no real UI components
- Docker stack ready to build and run

## Follow-Up PRs

- Per-app: real UI components, state wiring, GEE scripts
- GEE task patterns finalized after pysepal async API stabilizes
