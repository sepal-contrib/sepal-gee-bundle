# Basin Rivers Dashboard (ipecharts) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Basin Rivers dashboard placeholder tables with a full interactive dashboard (ipecharts) matching the legacy plotly UX — overall donut, per-catchment donut, per-catchment bar (3 modes), loss trend line, and a settings card with variable/timespan/catchment filters.

**Architecture:** Pure data helpers in `scripts/statistics.py` reshape `zonal_df` per chart. Chart components in `components/dashboard/` each own an `EChartsWidget.element(...)` wired to Solara reactive state. `dashboard_step.py` composes them in a Vuetify flex layout matching legacy. Click-to-filter drives `state.selected_var`; settings card provides the same plus timespan + catchment multiselect.

**Tech Stack:** ipecharts (ECharts), solara + reacton.ipyvuetify, pandas, pysepal `ThemeToggle`. No plotly, no seaborn.

**Key improvements over legacy:**
- Deterministic catchment color palette (no `random.shuffle`).
- Pure dataframe reshaping functions (unit-testable) separated from chart rendering.
- Drop `eval()` for title lookup → dict.
- Click on an already-selected overall-pie slice resets to `"all"`.
- ECharts `emphasis` for slice highlight (no manual `pull` offsets).
- Toolbox with save-as-image on each chart.

---

## File Structure

**New:**
- `apps/basin_rivers/components/dashboard/__init__.py` — re-exports
- `apps/basin_rivers/components/dashboard/theme.py` — `use_echarts_theme` hook
- `apps/basin_rivers/components/dashboard/overall_pie.py` — overall donut + click handler
- `apps/basin_rivers/components/dashboard/catchment_pie.py` — per-basin donut
- `apps/basin_rivers/components/dashboard/catchment_bar.py` — per-basin bar (3 modes)
- `apps/basin_rivers/components/dashboard/loss_trend.py` — spline line chart
- `apps/basin_rivers/components/dashboard/settings_card.py` — controls
- `tests/apps/basin_rivers/test_dashboard_helpers.py` — unit tests for helpers

**Modified:**
- `apps/basin_rivers/model.py` — add `selected_var`, `selected_hybasid_chart`, `sett_timespan` reactive fields
- `apps/basin_rivers/params.py` — add `CATCH_COLOR_PALETTE`, `VARIABLE_LABELS`, chart title tables
- `apps/basin_rivers/scripts/statistics.py` — add `add_catchment_colors`, `get_overall_pie_df`, `get_catchment_pie_df`, `get_catchment_bar_df`, `get_loss_trend_df`
- `apps/basin_rivers/scripts/__init__.py` — export new helpers
- `apps/basin_rivers/components/__init__.py` — unchanged surface but `DashboardStep` signature changes
- `apps/basin_rivers/components/dashboard_step.py` — full rewrite as composer
- `apps/basin_rivers/components/delineation_step.py` — on stats finish, seed dashboard state
- `apps/basin_rivers/page.py` — pass `theme_toggle` to `DashboardStep`

---

## Task 1: Extend `params.py` with chart metadata

**Files:**
- Modify: `apps/basin_rivers/params.py`
- Test: `tests/apps/basin_rivers/test_scripts.py`

- [ ] **Step 1: Write failing tests for new params**

Append to `tests/apps/basin_rivers/test_scripts.py`:

```python
class TestDashboardParams:
    def test_catch_palette_unique_and_nonempty(self):
        from apps.basin_rivers.params import CATCH_COLOR_PALETTE

        assert len(CATCH_COLOR_PALETTE) >= 12
        assert len(set(CATCH_COLOR_PALETTE)) == len(CATCH_COLOR_PALETTE)
        for c in CATCH_COLOR_PALETTE:
            assert c.startswith("#") and len(c) == 7

    def test_variable_labels_cover_groups(self):
        from apps.basin_rivers.params import VARIABLE_LABELS

        for key in ["all", "forest", "loss", "gain", "non_forest", "gain_loss"]:
            assert key in VARIABLE_LABELS

    def test_chart_titles_have_per_variable_keys(self):
        from apps.basin_rivers.params import CATCH_PIE_TITLES, CATCH_BAR_TITLES

        for key in ["all", "forest", "loss", "gain", "non_forest", "gain_loss"]:
            assert key in CATCH_PIE_TITLES
            assert key in CATCH_BAR_TITLES
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_scripts.py::TestDashboardParams -v`
Expected: `ImportError: cannot import name 'CATCH_COLOR_PALETTE'`.

- [ ] **Step 3: Append constants to `apps/basin_rivers/params.py`**

At the end of the file:

```python
# --- Dashboard palette (deterministic, hls-like) ---
CATCH_COLOR_PALETTE = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000",
    "#aaffc3", "#808000", "#ffd8b1", "#000075", "#808080",
]

# --- Dashboard labels + titles ---
VARIABLE_LABELS = {
    "all": "All classes",
    "forest": "Stable forest",
    "loss": "Forest loss",
    "gain": "Forest gain",
    "non_forest": "Non-forest",
    "gain_loss": "Gain + loss",
}

CATCH_PIE_TITLES = {
    "all": "Watershed area ratio",
    "forest": "Forest area by catchment",
    "loss": "Loss area by catchment",
    "gain": "Gain area by catchment",
    "non_forest": "Non-forest area by catchment",
    "gain_loss": "Gain+loss area by catchment",
}

CATCH_BAR_TITLES = {
    "all": "Total area per catchment",
    "forest": "Forest area per catchment",
    "loss": "Loss area by year",
    "gain": "Gain area per catchment",
    "non_forest": "Non-forest area per catchment",
    "gain_loss": "Gain+loss area per catchment",
}
```

- [ ] **Step 4: Rerun tests and verify they pass**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_scripts.py::TestDashboardParams -v`
Expected: 3 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/basin_rivers/params.py tests/apps/basin_rivers/test_scripts.py
git commit -m "feat(basin_rivers): add dashboard palette and chart title tables"
```

---

## Task 2: Add `add_catchment_colors` helper

**Files:**
- Modify: `apps/basin_rivers/scripts/statistics.py`
- Modify: `apps/basin_rivers/scripts/__init__.py`
- Test: `tests/apps/basin_rivers/test_dashboard_helpers.py` (new)

- [ ] **Step 1: Write failing test**

Create `tests/apps/basin_rivers/test_dashboard_helpers.py`:

```python
"""Tests for Basin Rivers dashboard dataframe helpers."""

import pandas as pd
import pytest

from apps.basin_rivers.scripts.statistics import add_catchment_colors


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "basin": ["1", "1", "2", "2", "3"],
            "variable": [1, 40, 1, 30, 40],
            "area": [10.0, 20.0, 15.0, 25.0, 5.0],
            "group": ["loss", "forest", "loss", "non_forest", "forest"],
            "year": [2001, 0, 2001, 0, 0],
            "color": ["#a", "#b", "#a", "#c", "#b"],
        }
    )


class TestAddCatchmentColors:
    def test_adds_catch_color_column(self, sample_df):
        out = add_catchment_colors(sample_df)
        assert "catch_color" in out.columns

    def test_same_basin_same_color(self, sample_df):
        out = add_catchment_colors(sample_df)
        colors_by_basin = out.groupby("basin")["catch_color"].nunique()
        assert (colors_by_basin == 1).all()

    def test_different_basins_different_colors(self, sample_df):
        out = add_catchment_colors(sample_df)
        unique_colors = out.drop_duplicates("basin")["catch_color"].nunique()
        assert unique_colors == 3

    def test_deterministic(self, sample_df):
        a = add_catchment_colors(sample_df)["catch_color"].tolist()
        b = add_catchment_colors(sample_df)["catch_color"].tolist()
        assert a == b

    def test_more_basins_than_palette_cycles(self):
        many = pd.DataFrame({"basin": [str(i) for i in range(30)], "area": [1.0] * 30})
        out = add_catchment_colors(many)
        assert out["catch_color"].notna().all()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestAddCatchmentColors -v`
Expected: `ImportError: cannot import name 'add_catchment_colors'`.

- [ ] **Step 3: Implement helper**

Append to `apps/basin_rivers/scripts/statistics.py`:

```python
from apps.basin_rivers.params import CATCH_COLOR_PALETTE


def add_catchment_colors(df: pd.DataFrame) -> pd.DataFrame:
    """Add a deterministic `catch_color` column keyed on sorted basin id.

    The same basin always gets the same color across reloads. If there are more
    basins than palette entries, the palette cycles.
    """
    if df.empty or "basin" not in df.columns:
        return df.assign(catch_color=pd.Series(dtype=str))

    basins_sorted = sorted(df["basin"].astype(str).unique())
    palette = CATCH_COLOR_PALETTE
    mapping = {b: palette[i % len(palette)] for i, b in enumerate(basins_sorted)}
    out = df.copy()
    out["catch_color"] = out["basin"].astype(str).map(mapping)
    return out
```

Update `apps/basin_rivers/scripts/__init__.py`:

```python
from .gfc_classification import classify_gfc
from .statistics import (
    add_catchment_colors,
    compute_zonal_stats,
    parse_zonal_stats,
)
from .visualization import create_basins_layer, create_selection_layer
from .watershed import build_upstream_fc, get_hydroshed_collection, get_upstream_basin_ids

__all__ = [
    "add_catchment_colors",
    "build_upstream_fc",
    "classify_gfc",
    "compute_zonal_stats",
    "create_basins_layer",
    "create_selection_layer",
    "get_hydroshed_collection",
    "get_upstream_basin_ids",
    "parse_zonal_stats",
]
```

- [ ] **Step 4: Rerun tests**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestAddCatchmentColors -v`
Expected: 5 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/basin_rivers/scripts/statistics.py apps/basin_rivers/scripts/__init__.py tests/apps/basin_rivers/test_dashboard_helpers.py
git commit -m "feat(basin_rivers): deterministic per-catchment color palette"
```

---

## Task 3: Add `get_overall_pie_df` helper

**Files:**
- Modify: `apps/basin_rivers/scripts/statistics.py`
- Modify: `apps/basin_rivers/scripts/__init__.py`
- Test: `tests/apps/basin_rivers/test_dashboard_helpers.py`

- [ ] **Step 1: Write failing test**

Append to `tests/apps/basin_rivers/test_dashboard_helpers.py`:

```python
from apps.basin_rivers.scripts.statistics import get_overall_pie_df


class TestGetOverallPieDf:
    def test_groups_sum_area(self, sample_df):
        out = get_overall_pie_df(sample_df)
        expected_total = sample_df["area"].sum()
        assert out["area"].sum() == pytest.approx(expected_total)

    def test_one_row_per_group(self, sample_df):
        out = get_overall_pie_df(sample_df)
        assert out["group"].nunique() == len(out)

    def test_color_column_present(self, sample_df):
        out = get_overall_pie_df(sample_df)
        assert "color" in out.columns
        assert out["color"].notna().all()

    def test_empty_df_returns_empty(self):
        import pandas as pd
        out = get_overall_pie_df(pd.DataFrame(columns=["basin", "group", "area"]))
        assert out.empty
```

- [ ] **Step 2: Run test, see it fail**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetOverallPieDf -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

Append to `apps/basin_rivers/scripts/statistics.py`:

```python
def get_overall_pie_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate area per group (change class) for the overall donut."""
    if df.empty:
        return pd.DataFrame(columns=["group", "area", "color"])

    grouped = df.groupby("group", as_index=False)["area"].sum()
    grouped["color"] = grouped["group"].map(GFC_COLORS_DICT).fillna("#888888")
    return grouped.sort_values("area", ascending=False).reset_index(drop=True)
```

Add to `scripts/__init__.py` exports.

- [ ] **Step 4: Rerun tests**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetOverallPieDf -v`
Expected: 4 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/basin_rivers/scripts/statistics.py apps/basin_rivers/scripts/__init__.py tests/apps/basin_rivers/test_dashboard_helpers.py
git commit -m "feat(basin_rivers): overall-pie dataframe helper"
```

---

## Task 4: Add `get_catchment_pie_df` helper

**Files:**
- Modify: `apps/basin_rivers/scripts/statistics.py`
- Modify: `apps/basin_rivers/scripts/__init__.py`
- Test: `tests/apps/basin_rivers/test_dashboard_helpers.py`

- [ ] **Step 1: Write failing test**

Append:

```python
from apps.basin_rivers.scripts.statistics import get_catchment_pie_df


class TestGetCatchmentPieDf:
    @pytest.fixture
    def colored_df(self, sample_df):
        return add_catchment_colors(sample_df)

    def test_all_sums_all_groups(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="all")
        assert set(out["basin"]) == {"1", "2", "3"}
        assert out.loc[out.basin == "1", "area"].iloc[0] == 30.0

    def test_specific_class_filters(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="forest")
        assert set(out["basin"]) == {"1", "3"}
        assert out.loc[out.basin == "1", "area"].iloc[0] == 20.0

    def test_carries_catch_color(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="all")
        assert "catch_color" in out.columns
        assert out["catch_color"].notna().all()

    def test_unknown_var_returns_empty(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="nope")
        assert out.empty
```

- [ ] **Step 2: Run, see fail**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetCatchmentPieDf -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

Append to `scripts/statistics.py`:

```python
_VAR_KEYS = {"all", "forest", "loss", "gain", "non_forest", "gain_loss"}


def get_catchment_pie_df(df: pd.DataFrame, selected_var: str) -> pd.DataFrame:
    """Aggregate area per basin for the detail donut.

    - selected_var == "all" → sum over all groups.
    - specific class → filter rows with that group, then sum.
    Returns columns: basin, area, catch_color.
    """
    if df.empty or selected_var not in _VAR_KEYS:
        return pd.DataFrame(columns=["basin", "area", "catch_color"])

    work = df if selected_var == "all" else df[df["group"] == selected_var]
    if work.empty:
        return pd.DataFrame(columns=["basin", "area", "catch_color"])

    grouped = work.groupby("basin", as_index=False)["area"].sum()
    colors = work.drop_duplicates("basin")[["basin", "catch_color"]]
    return grouped.merge(colors, on="basin", how="left")
```

Export from `scripts/__init__.py`.

- [ ] **Step 4: Rerun**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetCatchmentPieDf -v`
Expected: 4 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/basin_rivers/scripts/statistics.py apps/basin_rivers/scripts/__init__.py tests/apps/basin_rivers/test_dashboard_helpers.py
git commit -m "feat(basin_rivers): catchment-pie dataframe helper"
```

---

## Task 5: Add `get_catchment_bar_df` helper

**Files:**
- Modify: `apps/basin_rivers/scripts/statistics.py`
- Modify: `apps/basin_rivers/scripts/__init__.py`
- Test: `tests/apps/basin_rivers/test_dashboard_helpers.py`

- [ ] **Step 1: Write failing test**

Append:

```python
from apps.basin_rivers.scripts.statistics import get_catchment_bar_df


class TestGetCatchmentBarDf:
    @pytest.fixture
    def colored_df(self, sample_df):
        return add_catchment_colors(sample_df)

    def test_all_mode_one_row_per_basin(self, colored_df):
        out, mode = get_catchment_bar_df(colored_df, "all", (2001, 2020))
        assert mode == "single"
        assert set(out["basin"]) == {"1", "2", "3"}
        assert list(out.columns) == ["basin", "area", "catch_color"]

    def test_class_mode_filters(self, colored_df):
        out, mode = get_catchment_bar_df(colored_df, "forest", (2001, 2020))
        assert mode == "single"
        assert set(out["basin"]) == {"1", "3"}

    def test_loss_mode_year_by_basin(self, colored_df):
        out, mode = get_catchment_bar_df(colored_df, "loss", (2001, 2020))
        assert mode == "stacked"
        assert set(out.columns) >= {"basin", "year", "area", "catch_color"}
        assert (out["year"] >= 2001).all() and (out["year"] <= 2020).all()

    def test_loss_mode_respects_timespan(self, colored_df):
        out, mode = get_catchment_bar_df(colored_df, "loss", (2002, 2020))
        assert out.empty or (out["year"] >= 2002).all()
```

- [ ] **Step 2: Run, see fail**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetCatchmentBarDf -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

Append to `scripts/statistics.py`:

```python
def get_catchment_bar_df(
    df: pd.DataFrame,
    selected_var: str,
    timespan: tuple[int, int],
) -> tuple[pd.DataFrame, str]:
    """Reshape zonal_df for the per-catchment bar chart.

    Returns (dataframe, mode):
      - mode="single": one row per basin with `area`. Used for "all" and any
        single-class selection.
      - mode="stacked": one row per (basin, year) with `area`. Used for "loss",
        filtered to the given timespan.
    """
    if df.empty or selected_var not in _VAR_KEYS:
        return pd.DataFrame(columns=["basin", "area", "catch_color"]), "single"

    if selected_var == "loss":
        from_, to = timespan
        mask = (df["group"] == "loss") & df["year"].between(from_, to)
        loss_df = df.loc[mask]
        if loss_df.empty:
            return pd.DataFrame(columns=["basin", "year", "area", "catch_color"]), "stacked"
        grouped = loss_df.groupby(["basin", "year"], as_index=False)["area"].sum()
        colors = loss_df.drop_duplicates("basin")[["basin", "catch_color"]]
        return grouped.merge(colors, on="basin", how="left"), "stacked"

    work = df if selected_var == "all" else df[df["group"] == selected_var]
    if work.empty:
        return pd.DataFrame(columns=["basin", "area", "catch_color"]), "single"
    grouped = work.groupby("basin", as_index=False)["area"].sum()
    colors = work.drop_duplicates("basin")[["basin", "catch_color"]]
    return grouped.merge(colors, on="basin", how="left"), "single"
```

Export from `scripts/__init__.py`.

- [ ] **Step 4: Rerun**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetCatchmentBarDf -v`
Expected: 4 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/basin_rivers/scripts/statistics.py apps/basin_rivers/scripts/__init__.py tests/apps/basin_rivers/test_dashboard_helpers.py
git commit -m "feat(basin_rivers): catchment-bar dataframe helper"
```

---

## Task 6: Add `get_loss_trend_df` helper

**Files:**
- Modify: `apps/basin_rivers/scripts/statistics.py`
- Modify: `apps/basin_rivers/scripts/__init__.py`
- Test: `tests/apps/basin_rivers/test_dashboard_helpers.py`

- [ ] **Step 1: Write failing test**

Append:

```python
from apps.basin_rivers.scripts.statistics import get_loss_trend_df


class TestGetLossTrendDf:
    @pytest.fixture
    def colored_df(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "basin": ["1", "1", "2", "2"],
                "variable": [1, 2, 1, 2],
                "area": [5.0, 10.0, 3.0, 8.0],
                "group": ["loss", "loss", "loss", "loss"],
                "year": [2001, 2002, 2001, 2002],
                "color": ["#a"] * 4,
            }
        )
        return add_catchment_colors(df)

    def test_filters_to_selected_basins(self, colored_df):
        out = get_loss_trend_df(colored_df, ["1"], (2001, 2020))
        assert set(out["basin"]) == {"1"}

    def test_filters_by_timespan(self, colored_df):
        out = get_loss_trend_df(colored_df, ["1", "2"], (2002, 2002))
        assert set(out["year"]) == {2002}

    def test_empty_selection(self, colored_df):
        out = get_loss_trend_df(colored_df, [], (2001, 2020))
        assert out.empty

    def test_returns_catch_color(self, colored_df):
        out = get_loss_trend_df(colored_df, ["1"], (2001, 2020))
        assert "catch_color" in out.columns
```

- [ ] **Step 2: Run, see fail**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetLossTrendDf -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

Append to `scripts/statistics.py`:

```python
def get_loss_trend_df(
    df: pd.DataFrame,
    basins: list[str],
    timespan: tuple[int, int],
) -> pd.DataFrame:
    """Per-basin, per-year loss areas for the trend line chart."""
    if df.empty or not basins:
        return pd.DataFrame(columns=["basin", "year", "area", "catch_color"])

    from_, to = timespan
    basin_strs = [str(b) for b in basins]
    mask = (
        (df["group"] == "loss")
        & df["year"].between(from_, to)
        & df["basin"].astype(str).isin(basin_strs)
    )
    loss = df.loc[mask]
    if loss.empty:
        return pd.DataFrame(columns=["basin", "year", "area", "catch_color"])

    grouped = loss.groupby(["basin", "year"], as_index=False)["area"].sum()
    colors = loss.drop_duplicates("basin")[["basin", "catch_color"]]
    return grouped.merge(colors, on="basin", how="left").sort_values(["basin", "year"])
```

Export from `scripts/__init__.py`.

- [ ] **Step 4: Rerun**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py::TestGetLossTrendDf -v`
Expected: 4 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/basin_rivers/scripts/statistics.py apps/basin_rivers/scripts/__init__.py tests/apps/basin_rivers/test_dashboard_helpers.py
git commit -m "feat(basin_rivers): loss-trend dataframe helper"
```

---

## Task 7: Extend `BasinRiversState` with dashboard reactive fields

**Files:**
- Modify: `apps/basin_rivers/model.py`

- [ ] **Step 1: Add reactive fields**

Edit `apps/basin_rivers/model.py`. Inside `BasinRiversState.__init__`, after the existing Task state block, add:

```python
        # --- Dashboard state ---
        self.selected_var = solara.reactive("all")
        self.selected_hybasid_chart = solara.reactive([])
        self.sett_timespan = solara.reactive((2010, 2020))
```

- [ ] **Step 2: Sanity-check import still works**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.model import BasinRiversState; s = BasinRiversState(); print(s.selected_var.value, s.sett_timespan.value)"`
Expected: `all (2010, 2020)`.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/model.py
git commit -m "feat(basin_rivers): add dashboard reactive state (selected_var, timespan, basin filter)"
```

---

## Task 8: Create `components/dashboard/__init__.py` and `theme.py`

**Files:**
- Create: `apps/basin_rivers/components/dashboard/__init__.py`
- Create: `apps/basin_rivers/components/dashboard/theme.py`

- [ ] **Step 1: Create theme hook**

Create `apps/basin_rivers/components/dashboard/theme.py`:

```python
"""Reactive ECharts theme tied to pysepal ThemeToggle."""

from typing import Literal

import solara

Theme = Literal["dark", "light"]


def use_echarts_theme(theme_toggle) -> Theme:
    """Return "dark" or "light" and track changes on ThemeToggle.dark."""
    theme, set_theme = solara.use_state("dark" if getattr(theme_toggle, "dark", False) else "light")

    def _observe():
        def handler(change):
            set_theme("dark" if change["new"] else "light")

        theme_toggle.observe(handler, "dark")
        return lambda: theme_toggle.unobserve(handler, "dark")

    solara.use_effect(_observe, [id(theme_toggle)])
    return theme
```

- [ ] **Step 2: Create package init**

Create `apps/basin_rivers/components/dashboard/__init__.py`:

```python
from .catchment_bar import CatchmentBar
from .catchment_pie import CatchmentPie
from .loss_trend import LossTrend
from .overall_pie import OverallPie
from .settings_card import SettingsCard
from .theme import use_echarts_theme

__all__ = [
    "CatchmentBar",
    "CatchmentPie",
    "LossTrend",
    "OverallPie",
    "SettingsCard",
    "use_echarts_theme",
]
```

Note: the imports will fail until later tasks create the modules. That's expected — we'll not import this package until Task 14.

- [ ] **Step 3: Commit (scaffold)**

```bash
git add apps/basin_rivers/components/dashboard/
git commit -m "feat(basin_rivers): dashboard package scaffold + echarts theme hook"
```

---

## Task 9: `OverallPie` component

**Files:**
- Create: `apps/basin_rivers/components/dashboard/overall_pie.py`

- [ ] **Step 1: Implement**

Create `apps/basin_rivers/components/dashboard/overall_pie.py`:

```python
"""Overall forest-change donut. Click a slice to set selected_var."""

import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Tooltip
from ipecharts.option.series import Pie

from apps.basin_rivers.scripts.statistics import get_overall_pie_df

from .theme import use_echarts_theme


@solara.component
def OverallPie(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)
    df = state.zonal_df.value
    selected = state.selected_var.value

    if df is None or df.empty:
        solara.Text("Run statistics to see the overall distribution.")
        return

    pie_df = get_overall_pie_df(df)
    data = [
        {
            "value": round(float(row["area"]), 2),
            "name": row["group"].replace("_", " ").title(),
            "itemStyle": {"color": row["color"]},
            "_group": row["group"],
        }
        for _, row in pie_df.iterrows()
    ]

    pie = Pie(
        radius=["50%", "70%"],
        data=data,
        label={"show": True, "formatter": "{b}: {d}%"},
        emphasis={"scale": True, "scaleSize": 10},
    )

    option = Option(
        title=Title(text="Overall forest change", left="center"),
        tooltip=Tooltip(trigger="item", formatter="{b}: {c} ha ({d}%)"),
        legend=Legend(orient="horizontal", bottom=0),
        series=[pie],
    )

    def on_click(params):
        group = (params or {}).get("data", {}).get("_group")
        if not group:
            return
        state.selected_var.value = "all" if selected == group else group

    chart = EChartsWidget.element(
        option=option, theme=theme, style={"height": "320px"}
    )
    solara.use_effect(
        lambda: chart.widget.on("click", None, on_click) if hasattr(chart, "widget") else None,
        [id(chart)],
    )
```

Note: `EChartsWidget.element(...)` returns a reacton element. The standard way to register click events in pysepal is to set them up after the underlying widget exists. We'll verify this at integration time; if `.widget` isn't accessible, we fall back to subscribing via a ref pattern. See Task 14 "Integration verification" for follow-up.

- [ ] **Step 2: Import-sanity check**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.components.dashboard.overall_pie import OverallPie; print(OverallPie)"`
Expected: prints a reacton component object, no ImportError.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/components/dashboard/overall_pie.py
git commit -m "feat(basin_rivers): OverallPie donut component"
```

---

## Task 10: `CatchmentPie` component

**Files:**
- Create: `apps/basin_rivers/components/dashboard/catchment_pie.py`

- [ ] **Step 1: Implement**

Create `apps/basin_rivers/components/dashboard/catchment_pie.py`:

```python
"""Per-catchment donut for the selected variable."""

import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Tooltip
from ipecharts.option.series import Pie

from apps.basin_rivers.params import CATCH_PIE_TITLES
from apps.basin_rivers.scripts.statistics import get_catchment_pie_df

from .theme import use_echarts_theme


@solara.component
def CatchmentPie(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)
    df = state.zonal_df.value
    selected = state.selected_var.value
    basins = state.selected_hybasid_chart.value

    if df is None or df.empty or not basins:
        solara.Text("Select catchments to see per-basin share.")
        return

    filtered = df[df["basin"].astype(str).isin([str(b) for b in basins])]
    pie_df = get_catchment_pie_df(filtered, selected)
    if pie_df.empty:
        solara.Text(f"No {selected.replace('_', ' ')} area in the selected basins.")
        return

    data = [
        {
            "value": round(float(row["area"]), 2),
            "name": str(row["basin"]),
            "itemStyle": {"color": row["catch_color"]},
        }
        for _, row in pie_df.iterrows()
    ]

    pie = Pie(
        radius=["50%", "70%"],
        data=data,
        label={"show": True, "formatter": "{b}: {d}%"},
    )

    option = Option(
        title=Title(text=CATCH_PIE_TITLES.get(selected, ""), left="center"),
        tooltip=Tooltip(trigger="item", formatter="Basin {b}: {c} ha ({d}%)"),
        legend=Legend(orient="vertical", right=0, top="middle"),
        series=[pie],
    )

    EChartsWidget.element(option=option, theme=theme, style={"height": "320px"})
```

- [ ] **Step 2: Import-sanity check**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.components.dashboard.catchment_pie import CatchmentPie; print(CatchmentPie)"`
Expected: prints component, no error.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/components/dashboard/catchment_pie.py
git commit -m "feat(basin_rivers): CatchmentPie donut component"
```

---

## Task 11: `CatchmentBar` component

**Files:**
- Create: `apps/basin_rivers/components/dashboard/catchment_bar.py`

- [ ] **Step 1: Implement**

Create `apps/basin_rivers/components/dashboard/catchment_bar.py`:

```python
"""Per-catchment bar chart. Three modes driven by selected_var."""

import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar

from apps.basin_rivers.params import CATCH_BAR_TITLES
from apps.basin_rivers.scripts.statistics import get_catchment_bar_df

from .theme import use_echarts_theme


@solara.component
def CatchmentBar(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)
    df = state.zonal_df.value
    selected = state.selected_var.value
    timespan = state.sett_timespan.value
    basins = state.selected_hybasid_chart.value

    if df is None or df.empty or not basins:
        solara.Text("Select catchments to see the bar chart.")
        return

    filtered = df[df["basin"].astype(str).isin([str(b) for b in basins])]
    bar_df, mode = get_catchment_bar_df(filtered, selected, tuple(timespan))
    title = CATCH_BAR_TITLES.get(selected, "")

    if bar_df.empty:
        solara.Text(f"No data for {selected.replace('_', ' ')} in this range.")
        return

    if mode == "single":
        data = [
            {
                "value": round(float(row["area"]), 2),
                "itemStyle": {"color": row["catch_color"]},
            }
            for _, row in bar_df.iterrows()
        ]
        categories = bar_df["basin"].astype(str).tolist()
        bar = Bar(data=data, label={"show": True, "position": "top"})
        option = Option(
            title=Title(text=title, left="center"),
            tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
            xAxis=XAxis(type="category", data=categories, name="Catchment"),
            yAxis=YAxis(type="value", name="Area (ha)"),
            series=[bar],
        )
    else:
        years = sorted(bar_df["year"].unique().tolist())
        series = []
        for basin_id in sorted(bar_df["basin"].astype(str).unique()):
            sub = bar_df[bar_df["basin"].astype(str) == basin_id]
            by_year = {int(y): float(a) for y, a in zip(sub["year"], sub["area"])}
            color = sub["catch_color"].iloc[0]
            series.append(
                Bar(
                    name=basin_id,
                    stack="total",
                    data=[round(by_year.get(y, 0.0), 2) for y in years],
                    itemStyle={"color": color},
                )
            )
        option = Option(
            title=Title(text=title, left="center"),
            tooltip=Tooltip(trigger="axis", axisPointer={"type": "shadow"}),
            legend=Legend(bottom=0),
            xAxis=XAxis(type="category", data=[str(y) for y in years], name="Year"),
            yAxis=YAxis(type="value", name="Loss (ha)"),
            series=series,
        )

    EChartsWidget.element(option=option, theme=theme, style={"height": "360px"})
```

- [ ] **Step 2: Import-sanity check**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.components.dashboard.catchment_bar import CatchmentBar; print(CatchmentBar)"`
Expected: prints component.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/components/dashboard/catchment_bar.py
git commit -m "feat(basin_rivers): CatchmentBar chart component with 3 modes"
```

---

## Task 12: `LossTrend` component

**Files:**
- Create: `apps/basin_rivers/components/dashboard/loss_trend.py`

- [ ] **Step 1: Implement**

Create `apps/basin_rivers/components/dashboard/loss_trend.py`:

```python
"""Spline line chart for forest loss trend per basin."""

import solara
from ipecharts import EChartsWidget
from ipecharts.option import Legend, Option, Title, Tooltip, XAxis, YAxis
from ipecharts.option.series import Line

from apps.basin_rivers.scripts.statistics import get_loss_trend_df

from .theme import use_echarts_theme


@solara.component
def LossTrend(state, theme_toggle):
    theme = use_echarts_theme(theme_toggle)
    df = state.zonal_df.value
    basins = state.selected_hybasid_chart.value
    timespan = state.sett_timespan.value

    if df is None or df.empty or not basins:
        return

    trend_df = get_loss_trend_df(df, list(basins), tuple(timespan))
    if trend_df.empty:
        solara.Text("No loss in the selected range.")
        return

    years = sorted(trend_df["year"].unique().tolist())
    series = []
    for basin_id in sorted(trend_df["basin"].astype(str).unique()):
        sub = trend_df[trend_df["basin"].astype(str) == basin_id]
        by_year = {int(y): float(a) for y, a in zip(sub["year"], sub["area"])}
        color = sub["catch_color"].iloc[0]
        series.append(
            Line(
                name=basin_id,
                smooth=True,
                showSymbol=True,
                data=[round(by_year.get(y, 0.0), 2) for y in years],
                lineStyle={"color": color},
                itemStyle={"color": color},
            )
        )

    option = Option(
        title=Title(text="Forest loss trend", left="center"),
        tooltip=Tooltip(trigger="axis"),
        legend=Legend(bottom=0),
        xAxis=XAxis(type="category", data=[str(y) for y in years], name="Year"),
        yAxis=YAxis(type="value", name="Loss (ha)"),
        series=series,
    )

    EChartsWidget.element(option=option, theme=theme, style={"height": "320px"})
```

- [ ] **Step 2: Import-sanity check**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.components.dashboard.loss_trend import LossTrend; print(LossTrend)"`
Expected: prints component.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/components/dashboard/loss_trend.py
git commit -m "feat(basin_rivers): LossTrend line chart component"
```

---

## Task 13: `SettingsCard` component

**Files:**
- Create: `apps/basin_rivers/components/dashboard/settings_card.py`

- [ ] **Step 1: Implement**

Create `apps/basin_rivers/components/dashboard/settings_card.py`:

```python
"""Dashboard settings: variable, timespan, catchment multi-select."""

import reacton.ipyvuetify as rv
import solara

from apps.basin_rivers.params import GFC_MAX_YEAR, VARIABLE_LABELS


@solara.component
def SettingsCard(state):
    """Controls for selected_var, sett_timespan, selected_hybasid_chart."""
    basins = state.hybasin_list.value

    with rv.Card(flat=True, class_="pa-3"):
        with rv.CardTitle():
            solara.Text("Dashboard settings")

        with rv.CardText():
            rv.Select(
                v_model=state.selected_var.value,
                on_v_model=state.selected_var.set,
                items=[{"text": label, "value": key} for key, label in VARIABLE_LABELS.items()],
                label="Variable",
                dense=True,
                outlined=True,
            )

            solara.Text("Timespan")
            year_min = 2001
            year_max = 2000 + GFC_MAX_YEAR
            rv.RangeSlider(
                v_model=list(state.sett_timespan.value),
                on_v_model=lambda v: state.sett_timespan.set(tuple(v)),
                min=year_min,
                max=year_max,
                step=1,
                thumb_label="always",
                dense=True,
                class_="mt-6",
            )

            rv.Select(
                v_model=list(state.selected_hybasid_chart.value),
                on_v_model=lambda v: state.selected_hybasid_chart.set(list(v)),
                items=[{"text": str(b), "value": b} for b in basins],
                label="Catchments",
                multiple=True,
                chips=True,
                deletable_chips=True,
                dense=True,
                outlined=True,
                class_="mt-3",
            )
```

- [ ] **Step 2: Import-sanity check**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.components.dashboard.settings_card import SettingsCard; print(SettingsCard)"`
Expected: prints component.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/components/dashboard/settings_card.py
git commit -m "feat(basin_rivers): SettingsCard with variable/timespan/basin controls"
```

---

## Task 14: Rewrite `DashboardStep` as composer

**Files:**
- Modify: `apps/basin_rivers/components/dashboard_step.py`

- [ ] **Step 1: Replace contents**

Overwrite `apps/basin_rivers/components/dashboard_step.py`:

```python
"""Dashboard step: settings card + four ipecharts charts."""

import reacton.ipyvuetify as rv
import solara

from .dashboard import CatchmentBar, CatchmentPie, LossTrend, OverallPie, SettingsCard


@solara.component
def DashboardStep(state, theme_toggle):
    df = state.zonal_df.value
    if df is None or df.empty:
        solara.Text("Run delineation and calculate statistics to see results.")
        return

    with rv.Layout(column=True):
        with rv.Layout(class_="d-flex flex-wrap mb-2"):
            with rv.Flex(sm12=True, md5=True):
                SettingsCard(state)
            with rv.Flex(sm12=True, md7=True):
                OverallPie(state, theme_toggle)

        with rv.Layout(class_="d-flex flex-wrap mb-2"):
            with rv.Flex(sm12=True, md5=True):
                CatchmentPie(state, theme_toggle)
            with rv.Flex(sm12=True, md7=True):
                CatchmentBar(state, theme_toggle)

        if state.selected_var.value == "loss":
            with rv.Flex(xs12=True):
                LossTrend(state, theme_toggle)
```

- [ ] **Step 2: Verify import chain**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.components import DashboardStep; print(DashboardStep)"`
Expected: prints component.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/components/dashboard_step.py
git commit -m "refactor(basin_rivers): DashboardStep composes ipecharts dashboard"
```

---

## Task 15: Seed dashboard state on stats finish + apply `catch_color`

**Files:**
- Modify: `apps/basin_rivers/components/delineation_step.py`

- [ ] **Step 1: Patch `_sync_stats`**

Open `apps/basin_rivers/components/delineation_step.py`. Find `_sync_stats` and replace it with:

```python
    def _sync_stats():
        if stats_task.pending or stats_task.cancelled:
            return
        if stats_task.error:
            notifications.error(f"Statistics failed: {stats_task.exception}")
            return
        if stats_task.finished and stats_task.value is not None:
            from apps.basin_rivers.scripts import add_catchment_colors

            df = add_catchment_colors(stats_task.value)
            state.zonal_df.value = df

            state.selected_var.value = "all"
            state.selected_hybasid_chart.value = [str(b) for b in state.hybasin_list.value]
            state.sett_timespan.value = (state.year_start.value, state.year_end.value)

            notifications.success(f"Statistics computed: {len(df)} rows")
            logger.info("Statistics computed: %d rows", len(df))
```

- [ ] **Step 2: Sanity check**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.components.delineation_step import DelineationStep; print(DelineationStep)"`
Expected: prints component.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/components/delineation_step.py
git commit -m "feat(basin_rivers): seed dashboard state when stats finish"
```

---

## Task 16: Pass `theme_toggle` into `DashboardStep` from `page.py`

**Files:**
- Modify: `apps/basin_rivers/page.py`

- [ ] **Step 1: Patch panel wiring**

In `apps/basin_rivers/page.py`, change the `Dashboard` panel entry from `[DashboardStep(state)]` to `[DashboardStep(state, theme_toggle)]`.

Specifically, edit:

```python
        {
            "title": "Dashboard",
            "icon": "mdi-chart-bar",
            "content": [DashboardStep(state)],
        },
```

to:

```python
        {
            "title": "Dashboard",
            "icon": "mdi-chart-bar",
            "content": [DashboardStep(state, theme_toggle)],
        },
```

- [ ] **Step 2: Verify page imports**

Run: `conda run -n sepal-gee-bundle python -c "from apps.basin_rivers.page import BasinRiversPage; print(BasinRiversPage)"`
Expected: prints component, no error.

- [ ] **Step 3: Commit**

```bash
git add apps/basin_rivers/page.py
git commit -m "feat(basin_rivers): wire theme_toggle into DashboardStep"
```

---

## Task 17: Full integration verification

**Files:**
- No code changes; runtime verification.

- [ ] **Step 1: Run all dashboard-helper unit tests**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/basin_rivers/test_dashboard_helpers.py tests/apps/basin_rivers/test_scripts.py -v`
Expected: all pass.

- [ ] **Step 2: Run ruff**

Run: `conda run -n sepal-gee-bundle ruff check apps/basin_rivers tests/apps/basin_rivers && conda run -n sepal-gee-bundle ruff format apps/basin_rivers tests/apps/basin_rivers`
Expected: clean, or auto-format changes only. If format made changes, add them and amend the last task's commit or make a follow-up commit.

- [ ] **Step 3: Start the Solara dev server**

Run: `cd /home/dguerrero/1_modules/sepal-gee-bundle && ./run_solara.sh` in a separate terminal (or use `run_in_background`).
Open `http://localhost:8765/basin-rivers`.

- [ ] **Step 4: Manual test checklist**

Walk through the UI:

1. Click a point on the map → lat/lon populate.
2. Click "Delineate Upstream Basins" → basins load, zoom adjusts.
3. Click "Calculate Statistics" → Dashboard panel populates.
4. In dashboard:
   - [ ] Settings card shows variable dropdown (default "All classes"), timespan slider, catchment multi-select (all selected).
   - [ ] Overall donut renders with 2–5 slices, each color from `GFC_COLORS_DICT`.
   - [ ] Catchment donut renders with one slice per basin, each with `catch_color`.
   - [ ] Catchment bar renders, x=basins, y=total area.
5. Change variable to "Loss":
   - [ ] Catchment donut retitles to "Loss area by catchment".
   - [ ] Catchment bar becomes stacked by year.
   - [ ] Loss trend line appears below.
6. Click a slice on the overall donut (e.g., "Forest"):
   - [ ] Variable select mirrors the change.
   - [ ] Detail panel updates accordingly.
7. Click the same slice again:
   - [ ] Variable resets to "all".
8. Toggle theme (sun/moon in top-right):
   - [ ] All charts re-theme within a second.

- [ ] **Step 5: If any chart misbehaves**

If `OverallPie` click handler doesn't fire, replace the `use_effect` pattern in `overall_pie.py` with a `solara.use_ref` + direct widget attachment during the render. Consult `~/1_modules/pysepal/docs/guides/ipecharts.md` § "Event Handling" for the exact pattern and fix. Commit the fix as `fix(basin_rivers): attach overall-pie click handler via ref`.

- [ ] **Step 6: Final commit (if any fixes)**

Amend or append as needed.

---

## Self-Review (plan author)

- **Spec coverage:**
  - `catch_color` deterministic — Task 1 + 2.
  - reactive state additions — Task 7.
  - overall donut with click → selected_var — Task 9.
  - per-catchment donut — Task 10.
  - per-catchment bar, 3 modes — Tasks 5 + 11.
  - loss-trend line — Tasks 6 + 12.
  - settings card — Tasks 1 (labels) + 13.
  - theme integration — Task 8 + threaded through 9/10/11/12.
  - layout (md5/md7 rows) — Task 14.
  - defaults on stats finish — Task 15.
  - wiring theme_toggle — Task 16.
  - integration + manual test — Task 17.

- **Placeholder scan:** none of the step code blocks contain TBD/TODO. Step 5 of Task 17 mentions a conditional fix but references the ipecharts guide for the exact pattern rather than leaving it vague.

- **Type consistency:** `get_catchment_bar_df` returns `(df, mode)` in Task 5 and is consumed with exactly that signature in Task 11. `add_catchment_colors` returns a new df in Task 2 and is used identically in Tasks 4, 5, 6, 15. `use_echarts_theme` returns `"dark" | "light"` in Task 8 and is passed to `EChartsWidget.element(theme=...)` in Tasks 9/10/11/12 — matches the ipecharts API.
