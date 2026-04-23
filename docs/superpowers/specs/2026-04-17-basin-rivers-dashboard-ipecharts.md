# Basin Rivers — Dashboard with ipecharts (Full Parity)

**Date:** 2026-04-17
**App:** `apps/basin_rivers`
**Scope:** Replace dashboard placeholder tables with a full interactive dashboard matching the legacy plotly/seaborn UX, implemented with ipecharts.

## Goals

1. Recreate the legacy `DashboardTile` layout (`OverallPieCard` + `DetailedStat`) using ipecharts.
2. Keep the drill-down interaction: clicking a slice of the overall donut filters the detail panel to that class.
3. Add the `StatSettingCard` controls: variable selector, timespan slider, catchment multi-select.
4. Respect `ThemeToggle` (dark/light) across all charts.

Out of scope: changing the delineation/statistics algorithms, export buttons, i18n of chart titles.

## Source of truth

Legacy reference:
- `~/1_modules/basin-rivers/component/tile/dashboard_tile.py`
- `~/1_modules/basin-rivers/component/tile/dashboard_view.py`
- `~/1_modules/basin-rivers/component/widget/stat_sett_card.py`
- `~/1_modules/basin-rivers/component/model/model.py` — `get_overall_pie_df`, `get_dataframe` (for `catch_color`)
- `~/1_modules/basin-rivers/component/parameter/fig_styles.py`

ipecharts guide: `~/1_modules/pysepal/docs/guides/ipecharts.md`

## Data model

Existing `state.zonal_df` from `parse_zonal_stats()` has columns:
`basin, variable, area, group, year, color` (class-level color).

Adds required:
- `catch_color` column — one deterministic hex per basin (replaces legacy `seaborn.color_palette("hls", n)` + `random.shuffle`). Use a fixed palette cycled by sorted basin id.

New reactive state fields in `BasinRiversState`:
- `selected_var: Reactive[str]` — `"all" | "forest" | "loss" | "gain" | "non_forest" | "gain_loss"`. Default `"all"`.
- `selected_hybasid_chart: Reactive[list[str]]` — basins to include in detail panel. Defaults to all basins when stats finish.
- `sett_timespan: Reactive[tuple[int, int]]` — `[year_start, year_end]` mirroring the analysis range, editable in the settings card.

## Layout (matches legacy)

```
Row 1: | SettingsCard (md5)            | OverallPie (md7) |
Row 2: | CatchmentPie  (md5)           | CatchmentBar (md7)|
Row 3 (only if selected_var == "loss") |
       | LossTrend (full width)                           |
```

Container: `rv.Layout class_="d-flex flex-wrap"` + `rv.Flex sm12 md5/md7` — same pattern as legacy.

## Charts

All via `EChartsWidget.element(...)` (reactive, per ipecharts guide). Each chart is mounted once; option data traitlets are mutated when state changes (the widget auto-rerenders). Theme is wired to `ThemeToggle`.

### 1. `OverallPie` (donut)

- Data: `df.groupby("group")["area"].sum()`, colored by `GFC_COLORS_DICT[group]`.
- Series: `Pie(radius=["50%", "70%"])`, labels = capitalized group, values = area.
- Interaction: `chart.on("click", None, handler)` → sets `state.selected_var` to the clicked group, or back to `"all"` if the current one is re-clicked.
- Title: "Overall Forest Change". Legend horizontal bottom.

### 2. `CatchmentPie` (donut)

- Input: filtered df per `selected_var`.
  - `"all"` → groupby basin sum area.
  - any class → rows with `group == selected_var`, groupby basin sum area.
- Colors per slice: `catch_color` per basin.
- Series: `Pie(radius=["50%", "70%"])`.
- Title reflects `selected_var` (e.g., "Forest area by catchment", "Loss area by catchment").

### 3. `CatchmentBar`

Three modes driven by `selected_var`:

- `"all"`: one bar per basin. `x=basin`, `y=sum(area)`, `itemStyle.color = catch_color`.
- `"loss"`: stacked bars, `x=year` (from `sett_timespan`), one `Bar(stack="total")` series per basin, colored by `catch_color`.
- other class: one bar per basin, `x=basin`, `y=area_in_class`, colored by `catch_color`.

Titles: "Total area", "Loss area by year", or `"{Class} area per catchment"`.

### 4. `LossTrend` (spline line)

- Only rendered when `selected_var == "loss"`.
- One `Line(smooth=True)` series per basin in `selected_hybasid_chart`.
- `x=year` (within `sett_timespan`), `y=loss area`, line/marker colored by `catch_color`.
- Title: "Forest loss trend".

## Settings card

A plain `solara.Column` (or `rv.Card`) with three controls:

1. **Variable select** — `rv.Select` with options: All, Forest, Loss, Gain, Non-forest, Gain+Loss. Bound to `state.selected_var`. Mirrors click behavior of overall pie.
2. **Timespan range slider** — `rv.RangeSlider` over `[GFC_MIN_YEAR_ABS, GFC_MAX_YEAR_ABS]` (i.e. 2001..last-analysis-year). Bound to `state.sett_timespan`. Default = `[state.year_start, state.year_end]`.
3. **Catchment multiselect** — `rv.Select(multiple=True, chips=True)` over `state.hybasin_list`. Bound to `state.selected_hybasid_chart`. Default = all.

## Theme integration

Per ipecharts guide § "Custom Theme Integration". Each `EChartsWidget.element(...)` gets `theme=get_theme()` and re-renders on `ThemeToggle.dark` changes.

Implementation: a small helper `use_echarts_theme(theme_toggle)` that returns a reactive value `"dark" | "light"`, threaded into each chart. Wire `theme_toggle` from `page.py` into `DashboardStep`.

## Script helpers (new)

`scripts/statistics.py` — add pure functions (no UI):

- `add_catchment_colors(df) -> DataFrame` — adds `catch_color` column; palette is a fixed 20-hex hls-like list, cycled by sorted basin id.
- `get_overall_pie_df(df) -> DataFrame` — `[group, area, color]` aggregated.
- `get_catchment_pie_df(df, selected_var) -> DataFrame` — `[basin, area, catch_color]`.
- `get_catchment_bar_df(df, selected_var, timespan) -> DataFrame` — shape varies by mode (documented in docstring).
- `get_loss_trend_df(df, basins, timespan) -> DataFrame` — `[basin, year, area, catch_color]`.

All functions are pure; they take a DataFrame and return a new one. No reactive state access.

## Component structure

```
apps/basin_rivers/components/
├── dashboard_step.py          # Container: settings card + 4 charts + layout
└── dashboard/
    ├── __init__.py
    ├── settings_card.py       # variable + timespan + basin multiselect
    ├── overall_pie.py         # OverallPie component (click → selected_var)
    ├── catchment_pie.py       # CatchmentPie component
    ├── catchment_bar.py       # CatchmentBar component (3 modes)
    ├── loss_trend.py          # LossTrend component (conditional)
    └── theme.py               # use_echarts_theme helper
```

## Wiring

- `page.py` passes `theme_toggle` into `DashboardStep(state, theme_toggle)`.
- `DelineationStep` after stats finish: set `state.selected_var = "all"`, `state.selected_hybasid_chart = list(state.hybasin_list)`, `state.sett_timespan = (state.year_start, state.year_end)`, and mutate `state.zonal_df` with `add_catchment_colors(df)` applied.
- `DashboardStep` renders the settings card + four chart components. Each chart owns its `EChartsWidget` option and updates it via Solara reactivity.

## Edge cases

- `zonal_df is None` or empty → show placeholder text, no charts mounted.
- Single basin → charts still render.
- `selected_hybasid_chart` empty → detail panel shows placeholder.
- `selected_var` re-clicked on overall pie → reset to `"all"`.
- Theme change mid-session → charts rerender with new theme.

## Tests

Unit (pytest, conda env `sepal-gee-bundle`):
- `add_catchment_colors`: deterministic palette, 1 color per basin, survives `df.groupby`.
- `get_overall_pie_df`: correct aggregation, color mapping.
- `get_catchment_pie_df`: mode-dependent filtering.
- `get_catchment_bar_df`: all/loss/class modes produce expected shapes.
- `get_loss_trend_df`: basin filtering and timespan filtering.

Integration: run the Solara app, trigger delineation + stats on a small AOI, verify all four charts render and the click-to-filter flow works.

## Non-goals

- Replacing the upstream delineation algorithm (`ee.List.iterate()`) — separate follow-up.
- i18n of titles.
- Export buttons.
