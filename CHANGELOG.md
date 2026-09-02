## 0.3.2 (2026-09-02)

### Fix

- require pysepal 3.8.3
- move to pysepal 3.8.2 while 4.0 is a release candidate

## 0.3.1 (2026-08-20)

### Fix

- mount Earth Engine credentials so init_ee can initialize

## 0.3.0 (2026-08-20)

### Feat

- **basin_rivers**: render upstream basins as vector tiles
- **basin_rivers**: build basin tiles from batched Earth Engine fetches
- **basin_rivers**: add a tile style matching the dashboard colors
- log at startup that asgi.py mounted the tile route
- log why a tile request was served or refused
- serve per-session tile archives over an authorized route
- **aoi**: restrict AOI selection to GEE methods and drawing
- **tmf**: add TransitionMap layer; collapsible, width-capped legends
- **tmf**: render CHG as a start->end transition class map
- **maps**: add satellite basemap as a switchable secondary basemap
- **tmf,fcdm**: attach vis_params to exported assets

### Fix

- **basin_rivers**: select basin colors with filters, not a paint expression
- stop solara's gzip middleware compressing tile range responses
- run the dev script through asgi.py so the tile route exists
- **ci**: handle a service-account EARTHENGINE_TOKEN in dataset-check
- **ci**: write EARTHENGINE_TOKEN to credentials, not service-account.json
- scope markdown image style to .markdown-new-tab so it doesn't leak to all images
- clip AOI by geometry so Image.clip updates system:footprint
- **gee-source**: don't render the iframe when extraction yields no source

### Refactor

- **basin_rivers**: serve basin tiles through the authorized route
- **basin_rivers**: share the basin color assignment
- **gee_source**: save through the pysepal_api files API
- **coverage_analysis**: rename VizRequest to VisualizeRequest
- **alos_mosaics**: rename VizStep component to VisualizeStep
- **tmf**: drop duplicate by-year chart, tidy dashboard legend

### Perf

- **docker**: poll healthcheck every 30s instead of 1s
- **memory**: run under jemalloc to bound RSS

## 0.2.0 (2026-05-19)

### Feat

- **gfc**: add GFC_VIS_PARAMS and wire into GFC and basin_rivers exports
- **apps**: one-shot About dialogs, repo links, and select widget cleanup
- **gee_source**: MapApp layout with live-app + source iframes
- **fcdm**: calendar date pickers, slim sliders, and recent default dates
- **ux**: tree-cover preset chips with custom field for gfc and fcdm
- **_commons**: shared dataset registry + GFC primitives + weekly dataset-check
- **gee_source**: add EE Apps JavaScript source extractor
- **alos_mosaics**: add app tree (page.py already present)
- **tmf_sepal**: add TMF visualization + statistics dashboard
- **fcdm**: migrate from stub; expose custom forest-mask asset
- **coverage_analysis**: migrate from stub; fold selection into visualize; add dashboard
- **gfc**: basin-rivers-style dashboard + ipecharts loss chart
- **basin_rivers**: PDF report export from dashboard modal
- **basin_rivers**: thread legend_data reactive into DashboardStep
- **basin_rivers**: CSS class hooks on dashboard charts for PDF capture
- **pdf-report**: re-export public API from package __init__
- **pdf-report**: PdfReportButton Solara component + capture template
- **pdf-report**: build_pdf_report compose function with single long-page + A4 fallback
- **pdf-report**: LegendFlowable with native vector gradients and chips
- **pdf-report**: capture spec + PdfReportConfig dataclasses
- **pdf-report**: scaffold pdf_report package
- **pdf-report**: add reportlab runtime dep, pypdf dev dep
- **basin_rivers**: dashboard polish — card header, thicker donuts, conditional timespan
- **basin_rivers**: guard against too many upstream basins
- **basin_rivers**: open dashboard in fullscreen modal
- **basin_rivers**: wire theme_toggle into DashboardStep
- **basin_rivers**: seed dashboard state when stats finish
- **basin_rivers**: SettingsCard with variable/timespan/basin controls
- **basin_rivers**: LossTrend line chart component
- **basin_rivers**: CatchmentBar chart component with 3 modes
- **basin_rivers**: CatchmentPie donut component
- **basin_rivers**: OverallPie donut component
- **basin_rivers**: dashboard package scaffold + echarts theme hook
- **basin_rivers**: add dashboard reactive state (selected_var, timespan, basin filter)
- **basin_rivers**: loss-trend dataframe helper
- **basin_rivers**: catchment-bar dataframe helper
- **basin_rivers**: catchment-pie dataframe helper
- **basin_rivers**: overall-pie dataframe helper
- **basin_rivers**: deterministic per-catchment color palette
- **basin_rivers**: add dashboard palette and chart title tables
- integrate LegendComponent into GFC app
- add GFC_LEGEND constant for LegendComponent
- add LegendData dataclasses for reusable legend component
- Phase 0 infrastructure + Phase 1 GFC app migration
- scaffold sepal-gee-bundle with 4 stub apps

### Fix

- **gfc**: bump Hansen GFC to 2025_v1_13 and track max year for defaults
- **apps**: open About links in new tab, fix Doc/Bug links, FCDM legend & AOI
- **pdf-report**: preserve SVG natural dimensions, use actual canvas scale, log all values
- **pdf-report**: composite leaflet SVG overlays via native drawImage
- **pdf-report**: wire button click via ipyvue.use_event; inline spinner while building
- **pdf-report**: normalize leaflet SVG transforms; loading button; per-capture width_fraction; match CSV/PDF styling
- **pdf-report**: pad computed page height to prevent content spilling to a second page
- **pdf-report**: capture leaflet-container in fullscreen; native canvas for echarts; smaller echart PDF footprint
- **pdf-report**: harder echarts instance search + html2canvas fallback
- **pdf-report**: bypass AMD when loading html2canvas inside jupyter-vue
- **pdf-report**: reparent logger under 'sepalui' so errors surface in app logs
- **pdf-report**: add diagnostic logging + stricter html2canvas load check
- **basin_rivers**: UX polish round 2 — contextual hints, compact info rows, clean restart
- **basin_rivers**: review fixes — layer cleanup, basin-selection, validation, modal UX
- **basin_rivers**: drop click-to-select on OverallPie (reacton Element vs ipywidget mismatch)
- **basin_rivers**: declare ipecharts dep + hoist hooks above early return in OverallPie

### Refactor

- **gee_source**: persist extracted sources via SepalClient user-files
- set a minimun zoom level
- **gfc**: compute area stats on dashboard open instead of after visualize
- **basin_rivers**: drop filter-mode basin selector and noisy outlet toasts
- **pages**: migrate to session-scoped theme_state; default right panel unpinned
- **apps**: route params/scripts through _commons; add Landsat 9
- **basin_rivers**: separate trace from stats; compute-on-dashboard-open
- **alos_mosaics**: migrate page.py to session-scoped ThemeState
- **basin_rivers**: migrate page.py to session-scoped ThemeState
- **basin_rivers**: UX polish — blue palette, legend, styled chips, renamed terms
- **basin_rivers**: DashboardStep composes ipecharts dashboard
