# GEE Source — Earth Engine App Source Extractor

## Purpose

Utility that extracts the JavaScript source code of a public **Earth Engine
App** given its public URL, shows it with syntax highlighting, and
optionally saves it to the user's SEPAL workspace under
`~/module_results/gee_source/<name>.js`.

This app does **not** use Earth Engine credentials, AOI, or a map. It is a
pure HTTP/HTML scraper backed by `requests` + `BeautifulSoup` + `pygments`.

## User Workflow

1. Paste a public Earth Engine App URL (e.g.
   `https://<user>.users.earthengine.app/view/<app-name>`).
2. Press **Extract source** — the app fetches the page, locates
   `init("https://...")` script tags, pulls the linked JSON payload, and
   concatenates `dependencies[path]` across every init call.
3. The raw JavaScript is rendered through pygments (JavaScript lexer) and
   shown below the input form.
4. The user edits the suggested filename and presses **Save to SEPAL** to
   write `<filename>.js` into `~/module_results/gee_source/`.

## Legacy Mapping

Original repo: https://github.com/sepal-contrib/gee_source
Local: `~/1_modules/gee_source/`

| Legacy file                              | Migrated to                                       |
|------------------------------------------|---------------------------------------------------|
| `component/scripts/jsext.py::jsext`      | `scripts/extract.py::extract_js_source` + helpers |
| `component/scripts/jsext.py::save`       | `scripts/save.py::save_code`                      |
| `component/scripts/pygments.py::html`    | `scripts/highlight.py::highlight_javascript`      |
| `component/model/model.py::Model`        | `model.py::GeeSourceState` (reactives)            |
| `component/tile/main_tile.py::MainTile`  | `components/extract_step.py`, `components/output_step.py` |
| `component/widget/code_window.py`        | `solara.HTML` rendering `highlight_javascript(...)` |
| `component/parameter/directory.py`       | `params.py::RESULT_DIR`                           |
| `sepal_ui.scripts.utils.normalize_str`   | `scripts/save.py::sanitize_filename`              |

## File Layout

```
apps/gee_source/
├── __init__.py
├── CLAUDE.md               # this file
├── logging_config.toml     # sepal_gee_bundle.gee_source logger
├── model.py                # GeeSourceState — reactives only
├── page.py                 # GeeSourcePage — plain Solara card layout
├── params.py               # RESULT_DIR, HTTP_TIMEOUT, USER_AGENT, OUTPUT_EXTENSION
├── components/
│   ├── __init__.py
│   ├── extract_step.py     # URL field + Extract (TaskButtonComponent)
│   └── output_step.py      # SaveControls + SourcePreview (+ OutputStep shim)
└── scripts/
    ├── __init__.py
    ├── extract.py          # fetch_app_html, parse_init_urls, extract_js_source
    ├── highlight.py        # highlight_javascript, highlight_css
    └── save.py             # sanitize_filename, save_code
```

## Parameters

| Constant             | Default                               | Meaning                                         |
|----------------------|---------------------------------------|-------------------------------------------------|
| `RESULT_DIR`         | `~/module_results/gee_source`         | Where `.js` files are saved                     |
| `HTTP_TIMEOUT`       | `30` seconds                          | Timeout for every HTTP call                     |
| `USER_AGENT`         | `sepal-gee-bundle/gee_source (...)`   | Presented to Earth Engine App hosts             |
| `OUTPUT_EXTENSION`   | `.js`                                 | Appended to the sanitized filename on save      |
| `EE_APP_URL_PREFIXES`| `("https://",)`                       | Prefix allowlist for input validation           |

## Architecture Notes

- **No map, no GEE, no AOI** — page uses a plain `solara.Column` with two
  cards instead of `MapAppComponent`. This matches the app's actual scope
  (a utility, not a pipeline).
- **Notifications** — `NotificationProvider()` mounted in `page.py`;
  components call `use_notifications()` for toasts. No inline
  `solara.Error` / `solara.Success`.
- **Async buttons** — both the extract and save actions use
  `TaskButtonComponent` + `use_task_button`, with `prefer_threaded=False`
  on every `use_task`. Blocking `requests`/file I/O is run via
  `asyncio.to_thread(...)`.
- **Pure scripts** — `extract_js_source`, `highlight_javascript`,
  `sanitize_filename`, `save_code` are all side-effect-free (or
  parametrised on `result_dir`) and have unit tests that never hit the
  network.

## Caveats

- Only public Earth Engine Apps render correctly. Apps that require
  Google OAuth return the sign-in page HTML, which has no `init("https://...")`
  script and therefore produces an empty result (the UI warns the user).
- Earth Engine Apps occasionally change their HTML structure — the
  scraper is best-effort and will return an empty string if the init
  payload disappears rather than crashing.
- `save_code` refuses to overwrite an existing file, mirroring the legacy
  behaviour. Pick a new filename or delete the old file manually.
