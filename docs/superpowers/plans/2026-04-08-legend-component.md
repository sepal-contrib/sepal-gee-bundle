# LegendComponent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable floating map legend component for pysepal Solara apps that supports gradient bars and discrete color chips, positioned bottom-center over the map.

**Architecture:** `@solara.component_vue` in pysepal with a Vue template that self-positions via CSS `position: fixed`. The Python side defines dataclasses (`LegendData`, `GradientEntry`, `DiscreteEntry`) serialized to dict for the Vue props. The component is rendered in the page alongside `MapApp.element()` and floats over the map area.

**Tech Stack:** Python dataclasses, `@solara.component_vue`, Vue 2 + Vuetify 2, CSS fixed positioning.

**Spec:** `docs/superpowers/specs/2026-04-07-legend-component-design.md`

---

## File Structure

```
pysepal/solara/components/
  legend.py          # LegendData, GradientEntry, DiscreteEntry, LegendComponent
  Legend.vue         # Vue template + scoped CSS (sibling to legend.py)

sepal-gee-bundle/
  apps/gfc/
    params.py        # Add GFC_LEGEND constant (modify)
    page.py          # Wire legend state + render LegendComponent (modify)
    components/
      params_step.py # Set legend on layer add, clear on new run (modify)
  tests/apps/gfc/
    test_legend.py   # Unit tests for LegendData serialization (create)
```

### Key constraint: MapApp only renders `main_map[0]`

MapApp.vue line 15: `<jupyter-widget :widget="main_map[0]">`. There is no slot for additional overlay widgets. The `LegendComponent` is rendered as a sibling to `MapApp.element()` in the Solara component tree. Its Vue template uses `position: fixed` to float over the map. The sidebar offset is read from the CSS variable `--drawer-width` that MapApp sets on `:root`.

---

## Task 1: Data model and serialization

**Files:**
- Create: `~/1_modules/pysepal/pysepal/solara/components/legend.py`
- Create: `~/1_modules/sepal-gee-bundle/tests/apps/gfc/test_legend.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for LegendData serialization."""

from dataclasses import asdict

from pysepal.solara.components.legend import (
    DiscreteEntry,
    GradientEntry,
    LegendData,
)


def test_empty_legend_serializes():
    data = LegendData()
    result = asdict(data)
    assert result == {"gradients": [], "items": []}


def test_discrete_only():
    data = LegendData(items=[DiscreteEntry("Forest", "#006400")])
    result = asdict(data)
    assert len(result["items"]) == 1
    assert result["items"][0] == {"label": "Forest", "color": "#006400"}
    assert result["gradients"] == []


def test_gradient_only():
    data = LegendData(
        gradients=[GradientEntry(colors=["#ffff00", "#8b0000"], labels=["2001", "2024"])]
    )
    result = asdict(data)
    assert len(result["gradients"]) == 1
    assert result["gradients"][0]["colors"] == ["#ffff00", "#8b0000"]
    assert result["gradients"][0]["labels"] == ["2001", "2024"]
    assert result["gradients"][0]["title"] == ""


def test_mixed_legend():
    data = LegendData(
        gradients=[
            GradientEntry(
                colors=["#ffff00", "#8b0000"],
                labels=["2001", "2024"],
                title="Forest loss year",
            )
        ],
        items=[
            DiscreteEntry("Forest", "#006400"),
            DiscreteEntry("Non forest", "#d3d3d3"),
        ],
    )
    result = asdict(data)
    assert len(result["gradients"]) == 1
    assert result["gradients"][0]["title"] == "Forest loss year"
    assert len(result["items"]) == 2


def test_multi_stop_gradient():
    data = LegendData(
        gradients=[
            GradientEntry(
                colors=["#0000ff", "#00ff00", "#ff0000"],
                labels=["-1", "0", "1"],
                title="NDVI",
            )
        ],
    )
    result = asdict(data)
    assert len(result["gradients"][0]["colors"]) == 3
    assert len(result["gradients"][0]["labels"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/gfc/test_legend.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pysepal.solara.components.legend'`

- [ ] **Step 3: Write the Python module with dataclasses only (no Vue component yet)**

Create `~/1_modules/pysepal/pysepal/solara/components/legend.py`:

```python
"""Reusable floating map legend for Solara apps.

Supports discrete color chips and continuous gradient bars.
Designed for bottom-center overlay on map-based pysepal apps.

Usage:
    from pysepal.solara.components.legend import (
        LegendComponent, LegendData, GradientEntry, DiscreteEntry,
    )
    from dataclasses import asdict

    legend = LegendData(
        gradients=[GradientEntry(colors=["#ffff00", "#8b0000"], labels=["2001", "2024"])],
        items=[DiscreteEntry("Forest", "#006400")],
    )
    LegendComponent(legend_data=asdict(legend))
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import solara


@dataclass
class GradientEntry:
    """A continuous color ramp with labeled endpoints."""

    colors: list[str]
    labels: list[str]
    title: str = ""


@dataclass
class DiscreteEntry:
    """A single labeled color chip."""

    label: str
    color: str


@dataclass
class LegendData:
    """Complete legend specification passed to LegendComponent."""

    gradients: list[GradientEntry] = field(default_factory=list)
    items: list[DiscreteEntry] = field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/gfc/test_legend.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add pysepal/solara/components/legend.py tests/apps/gfc/test_legend.py
git commit -m "feat: add LegendData dataclasses for reusable legend component"
```

---

## Task 2: Vue template

**Files:**
- Create: `~/1_modules/pysepal/pysepal/solara/components/Legend.vue`

- [ ] **Step 1: Create the Vue template**

Create `~/1_modules/pysepal/pysepal/solara/components/Legend.vue`:

```vue
<template>
  <div
    v-if="visible && hasContent"
    class="sepal-legend"
    :class="{ 'sepal-legend--collapsed': collapsed }"
  >
    <!-- Collapsed state: icon pill -->
    <div v-if="collapsed" class="sepal-legend__pill" @click="toggleCollapse">
      <v-icon small dark>mdi-map-legend</v-icon>
    </div>

    <!-- Expanded state -->
    <div v-else class="sepal-legend__body">
      <!-- Gradient sections -->
      <div
        v-for="(grad, gi) in parsedGradients"
        :key="'g-' + gi"
        class="sepal-legend__gradient-section"
      >
        <div v-if="grad.title" class="sepal-legend__gradient-title">
          {{ grad.title }}
        </div>
        <div
          class="sepal-legend__gradient-bar"
          :style="{ background: grad.cssGradient }"
        ></div>
        <div class="sepal-legend__gradient-labels">
          <span
            v-for="(lbl, li) in grad.labels"
            :key="'gl-' + li"
          >{{ lbl }}</span>
        </div>
      </div>

      <!-- Discrete items -->
      <div v-if="parsedItems.length > 0" class="sepal-legend__items">
        <div
          v-for="(item, ii) in parsedItems"
          :key="'i-' + ii"
          class="sepal-legend__item"
        >
          <span
            class="sepal-legend__chip"
            :style="{ backgroundColor: item.color }"
          ></span>
          <span class="sepal-legend__label">{{ item.label }}</span>
        </div>
      </div>

      <!-- Collapse toggle -->
      <button class="sepal-legend__toggle" @click="toggleCollapse">
        <v-icon x-small dark>mdi-chevron-down</v-icon>
      </button>
    </div>
  </div>
</template>

<script>
module.exports = {
  computed: {
    hasContent() {
      if (!this.legend_data) return false;
      var g = this.legend_data.gradients || [];
      var i = this.legend_data.items || [];
      return g.length > 0 || i.length > 0;
    },
    parsedGradients() {
      if (!this.legend_data || !this.legend_data.gradients) return [];
      return this.legend_data.gradients.map(function (g) {
        var stops = g.colors
          .map(function (c, i) {
            var pct = g.colors.length === 1 ? 0 : (i / (g.colors.length - 1)) * 100;
            return c + " " + pct + "%";
          })
          .join(", ");
        return {
          title: g.title || "",
          labels: g.labels || [],
          cssGradient: "linear-gradient(to right, " + stops + ")",
        };
      });
    },
    parsedItems() {
      if (!this.legend_data || !this.legend_data.items) return [];
      return this.legend_data.items;
    },
  },
  methods: {
    toggleCollapse() {
      this.collapsed = !this.collapsed;
    },
  },
};
</script>

<style scoped>
.sepal-legend {
  position: fixed;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  pointer-events: auto;
  font-family: Roboto, sans-serif;
}

.sepal-legend__pill {
  background: rgba(33, 33, 33, 0.85);
  backdrop-filter: blur(4px);
  border-radius: 16px;
  padding: 6px 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.sepal-legend__body {
  background: rgba(33, 33, 33, 0.85);
  backdrop-filter: blur(4px);
  border-radius: 8px;
  padding: 8px 14px;
  color: #fff;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 90vw;
  position: relative;
}

/* --- Gradient --- */
.sepal-legend__gradient-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sepal-legend__gradient-title {
  font-size: 11px;
  opacity: 0.8;
  text-align: center;
}

.sepal-legend__gradient-bar {
  height: 12px;
  border-radius: 3px;
  min-width: 200px;
}

.sepal-legend__gradient-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  opacity: 0.85;
}

/* --- Discrete items --- */
.sepal-legend__items {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  align-items: center;
}

.sepal-legend__item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.sepal-legend__chip {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  flex-shrink: 0;
}

.sepal-legend__label {
  white-space: nowrap;
  font-size: 12px;
}

/* --- Toggle --- */
.sepal-legend__toggle {
  position: absolute;
  top: 4px;
  right: 4px;
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.6;
  padding: 2px;
  line-height: 1;
}

.sepal-legend__toggle:hover {
  opacity: 1;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add pysepal/solara/components/Legend.vue
git commit -m "feat: add Legend.vue template with gradient bar and discrete chips"
```

---

## Task 3: Wire Vue template to Python component

**Files:**
- Modify: `~/1_modules/pysepal/pysepal/solara/components/legend.py`

- [ ] **Step 1: Add the `@solara.component_vue` definition to legend.py**

Append to the end of `~/1_modules/pysepal/pysepal/solara/components/legend.py`:

```python
@solara.component_vue("Legend.vue")
def LegendComponent(
    legend_data: dict = {},
    visible: bool = True,
    collapsed: bool = False,
    on_collapsed: Optional[Callable[[bool], None]] = None,
):
    """Floating map legend overlay.

    Renders at bottom-center of the viewport over the map area.
    Supports gradient bars and discrete color chips.

    Args:
        legend_data: Serialized LegendData (use dataclasses.asdict).
            Empty dict or missing keys = nothing rendered.
        visible: Show/hide the entire legend.
        collapsed: Collapsed state (icon pill only).
        on_collapsed: Callback when user toggles collapse.
    """
    pass
```

- [ ] **Step 2: Verify import works**

Run: `conda run -n sepal-gee-bundle python -c "from pysepal.solara.components.legend import LegendComponent, LegendData, GradientEntry, DiscreteEntry; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run existing tests still pass**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/gfc/test_legend.py -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add pysepal/solara/components/legend.py
git commit -m "feat: wire LegendComponent to Legend.vue via component_vue"
```

---

## Task 4: Add GFC_LEGEND constant to params.py

**Files:**
- Modify: `~/1_modules/sepal-gee-bundle/apps/gfc/params.py`

- [ ] **Step 1: Add the GFC legend data at the end of params.py**

Append after line 69 (`SLD_INTERVALS = _build_sld()`):

```python

# --- Legend data for LegendComponent ---
from pysepal.solara.components.legend import DiscreteEntry, GradientEntry, LegendData

GFC_LEGEND = LegendData(
    gradients=[
        GradientEntry(
            colors=[HEX_PALETTE[0], HEX_PALETTE[GFC_MAX_YEAR - 1]],
            labels=[str(2000 + 1), str(2000 + GFC_MAX_YEAR)],
            title="Forest loss year",
        ),
    ],
    items=[
        DiscreteEntry("Non forest", HEX_PALETTE[GFC_MAX_YEAR]),
        DiscreteEntry("Forest", HEX_PALETTE[GFC_MAX_YEAR + 1]),
        DiscreteEntry("Gains", HEX_PALETTE[GFC_MAX_YEAR + 2]),
        DiscreteEntry("Gain + loss", HEX_PALETTE[GFC_MAX_YEAR + 3]),
    ],
)
```

- [ ] **Step 2: Verify import**

Run: `conda run -n sepal-gee-bundle python -c "from apps.gfc.params import GFC_LEGEND; from dataclasses import asdict; d = asdict(GFC_LEGEND); print(len(d['gradients']), len(d['items']))"`
Expected: `1 4`

- [ ] **Step 3: Run ruff**

Run: `conda run -n sepal-gee-bundle ruff check apps/gfc/params.py`
Expected: All checks passed

- [ ] **Step 4: Commit**

```bash
git add apps/gfc/params.py
git commit -m "feat: add GFC_LEGEND constant for LegendComponent"
```

---

## Task 5: Integrate legend into GFC page

**Files:**
- Modify: `~/1_modules/sepal-gee-bundle/apps/gfc/page.py`
- Modify: `~/1_modules/sepal-gee-bundle/apps/gfc/components/params_step.py`

- [ ] **Step 1: Add legend state and component to page.py**

In `~/1_modules/sepal-gee-bundle/apps/gfc/page.py`, add imports at the top:

```python
from dataclasses import asdict

from pysepal.solara.components.legend import LegendComponent
```

Inside `GfcPage()`, after the `show_about` line (or where `sepal_map` is created), add legend reactive state:

```python
    legend_data = solara.use_reactive({})
    legend_visible = solara.use_reactive(False)
```

After the `MapApp.element(...)` call, render the legend:

```python
    LegendComponent(
        legend_data=legend_data.value,
        visible=legend_visible.value,
    )
```

Pass `legend_data` and `legend_visible` to `ParamsStep`:

Change the right_panel_content Parameters entry from:
```python
"content": [ParamsStep(state, sepal_map, gee_interface)],
```
to:
```python
"content": [ParamsStep(state, sepal_map, gee_interface, legend_data, legend_visible)],
```

- [ ] **Step 2: Update ParamsStep to control the legend**

In `~/1_modules/sepal-gee-bundle/apps/gfc/components/params_step.py`:

Add import:
```python
from dataclasses import asdict
from apps.gfc.params import GFC_LEGEND
```

Change the component signature:
```python
def ParamsStep(state, sepal_map, gee_interface, legend_data=None, legend_visible=None):
```

In `_start_viz()`, clear legend before starting:
```python
    def _start_viz():
        if state.aoi.value is None:
            state.error_message.value = "Please select an Area of Interest first."
            return
        cancel_reason.current = None
        state.loading.value = True
        state.error_message.value = None
        state.result_image.value = None
        if legend_visible is not None:
            legend_visible.set(False)
        viz_task(...)
```

In `_sync_viz()`, show legend on success:
```python
    def _sync_viz():
        state.loading.value = viz_task.pending
        if viz_task.pending or viz_task.cancelled:
            return
        if viz_task.error:
            state.error_message.value = str(viz_task.exception)
            return
        if viz_task.finished and viz_task.value is not None:
            state.error_message.value = None
            state.result_image.value = viz_task.value
            if legend_data is not None:
                legend_data.set(asdict(GFC_LEGEND))
            if legend_visible is not None:
                legend_visible.set(True)
```

- [ ] **Step 3: Run ruff on both files**

Run: `cd ~/1_modules/sepal-gee-bundle && conda run -n sepal-gee-bundle ruff check apps/gfc/page.py apps/gfc/components/params_step.py`
Expected: All checks passed

- [ ] **Step 4: Run existing tests**

Run: `conda run -n sepal-gee-bundle pytest tests/apps/gfc/ -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add apps/gfc/page.py apps/gfc/components/params_step.py
git commit -m "feat: integrate LegendComponent into GFC app"
```

---

## Task 6: Visual verification

**Files:** None (manual testing)

- [ ] **Step 1: Start the dev server**

Run: `conda activate sepal-gee-bundle && ./run_solara.sh`

- [ ] **Step 2: Verify the legend flow**

1. Open `http://localhost:8765/gfc`
2. Select an AOI
3. Set parameters and click "Add layer"
4. Verify: legend appears at bottom-center with gradient bar (yellow→darkred, "2001"→"2024") and 4 discrete chips
5. Click the collapse chevron — legend collapses to icon pill
6. Click the pill — legend expands back
7. Change AOI and click "Add layer" again — legend hides during processing, reappears with new layer

- [ ] **Step 3: Fix any CSS positioning issues**

If the legend is obscured by the sidebar or right panel, adjust the `left` calculation in `Legend.vue`. The sidebar width is available via the CSS variable `--drawer-width` set by MapApp:

```css
.sepal-legend {
  /* account for sidebar: center within remaining space */
  left: calc(var(--drawer-width, 60px) + (100vw - var(--drawer-width, 60px)) / 2);
}
```

- [ ] **Step 4: Commit any CSS fixes**

```bash
git add -A && git commit -m "fix: adjust legend positioning for sidebar offset"
```
