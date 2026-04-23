# LegendComponent — Reusable Map Legend for pysepal Solara Apps

**Date:** 2026-04-07
**Status:** Design
**Location:** `pysepal/solara/components/legend.py` + `pysepal/solara/components/vue/Legend.vue`

## Purpose

A reusable Solara component that renders a floating legend overlay at the
bottom-center of the map. Supports discrete (categorical) entries, continuous
gradient bars, and mixed layouts. Designed for pysepal map-based apps where
the current `LegendControl` (ipyleaflet WidgetControl) is too limited.

## Why Not Extend LegendControl

The existing `LegendControl` has structural limitations:
- Only supports `{label: hex_color}` dicts (no gradients, no grouping)
- ipyleaflet `WidgetControl` only allows corner positions — no `bottomcenter`
- Renders via Python-side HTML strings (no Vue reactivity, no CSS transitions)
- Coupled to the ipyleaflet control lifecycle

A new Solara component with a Vue template gives us CSS absolute positioning,
gradient rendering, collapsibility, and full Vuetify/CSS control.

## Data Model

```python
from dataclasses import dataclass, field

@dataclass
class GradientEntry:
    """A continuous color ramp with labeled endpoints."""
    colors: list[str]          # hex colors, left to right
    labels: list[str]          # e.g. ["2001", "2024"] — at least 2 (start/end)
    title: str = ""            # optional label above the gradient

@dataclass
class DiscreteEntry:
    """A single labeled color chip."""
    label: str
    color: str                 # hex color

@dataclass
class LegendData:
    """Complete legend specification. Pass to LegendComponent."""
    gradients: list[GradientEntry] = field(default_factory=list)
    items: list[DiscreteEntry] = field(default_factory=list)
```

### GFC Example

```python
from apps.gfc.params import HEX_PALETTE

legend = LegendData(
    gradients=[
        GradientEntry(
            colors=[HEX_PALETTE[0], HEX_PALETTE[23]],  # yellow -> darkred
            labels=["2001", "2024"],
            title="Forest loss year",
        ),
    ],
    items=[
        DiscreteEntry("Non forest", "#d3d3d3"),
        DiscreteEntry("Forest", "#006400"),
        DiscreteEntry("Gains", "#90ee90"),
        DiscreteEntry("Gain + loss", "#800080"),
    ],
)
```

For multi-stop gradients (FCDM delta-rNBR, NDVI), pass more colors:

```python
GradientEntry(
    colors=["#808080", "#ff0000"],
    labels=["0", "1"],
    title="Delta-rNBR",
)
```

## Component API

```python
@solara.component_vue("vue/Legend.vue")
def LegendComponent(
    legend_data: dict = {},      # serialized LegendData (dataclasses.asdict)
    visible: bool = True,
    collapsed: bool = False,
    on_collapsed: Callable = None,
):
    pass
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `legend_data` | dict | `{}` | Serialized `LegendData`. Empty = nothing rendered. |
| `visible` | bool | `True` | Show/hide the entire legend. |
| `collapsed` | bool | `False` | Collapsed state (icon only). |
| `on_collapsed` | callback | `None` | Fired when user toggles collapse. |

## Reactive State Management

The parent component owns the legend state. The `LegendComponent` is a pure
renderer — it displays whatever props it receives and re-renders when they
change.

```python
# Parent component (e.g., GfcPage) owns legend state as reactive variables
legend_data = solara.use_reactive({})
legend_visible = solara.use_reactive(False)

# --- Show legend when layer is added ---
def _sync_viz():
    if viz_task.finished and viz_task.value is not None:
        state.result_image.value = viz_task.value
        legend_visible.set(True)
        legend_data.set(asdict(gfc_legend))

# --- Hide legend and clear when AOI changes or layer is removed ---
def _on_aoi_change():
    legend_visible.set(False)
    legend_data.set({})

# --- Swap legend content entirely (e.g., different analysis) ---
def _show_ndvi_legend():
    legend_data.set(asdict(ndvi_legend))

# --- Component re-renders automatically on any .set() call ---
LegendComponent(
    legend_data=legend_data.value,
    visible=legend_visible.value,
)
```

### What Can Be Mutated at Runtime

| Action | How |
|--------|-----|
| Show/hide | `legend_visible.set(True/False)` |
| Change content | `legend_data.set(asdict(new_legend))` — different gradient, items, or both |
| Swap legend entirely | Replace `legend_data` with a completely different `LegendData` |
| Collapse/expand | User toggles in the UI, or parent sets `collapsed` prop |
| Clear legend | `legend_data.set({})` — component renders nothing |

### GFC Integration Example

```python
from dataclasses import asdict
from pysepal.solara.components.legend import (
    LegendComponent, LegendData, GradientEntry, DiscreteEntry,
)

GFC_LEGEND = LegendData(
    gradients=[
        GradientEntry(
            colors=[HEX_PALETTE[0], HEX_PALETTE[23]],
            labels=["2001", "2024"],
            title="Forest loss year",
        ),
    ],
    items=[
        DiscreteEntry("Non forest", "#d3d3d3"),
        DiscreteEntry("Forest", "#006400"),
        DiscreteEntry("Gains", "#90ee90"),
        DiscreteEntry("Gain + loss", "#800080"),
    ],
)

@solara.component
def GfcPage():
    legend_data = solara.use_reactive({})
    legend_visible = solara.use_reactive(False)

    # viz_task _sync_viz sets legend on success:
    #   legend_visible.set(True)
    #   legend_data.set(asdict(GFC_LEGEND))

    # _start_viz clears legend before new run:
    #   legend_visible.set(False)
    #   legend_data.set({})

    MapApp.element(
        main_map=[sepal_map, LegendComponent(
            legend_data=legend_data.value,
            visible=legend_visible.value,
        )],
        ...
    )
```

## Vue Template Design

### Layout

```
+--------------------------------------------------------------------+
|                          MAP                                        |
|                                                                     |
|                                                                     |
|                                                                     |
|  +--------------------------------------------------------------+  |
|  |  [gradient bar: yellow -----> darkred]  2001           2024  |  |
|  |  [chip] Non forest  [chip] Forest  [chip] Gains  [chip] G+L  [x]|
|  +--------------------------------------------------------------+  |
+--------------------------------------------------------------------+
```

- **Position:** `absolute`, bottom `12px`, centered with `left: 50%; transform: translateX(-50%)`
- **Width:** auto, max `90%` of the map container
- **Background:** semi-transparent dark card (`rgba(33,33,33,0.85)`) with backdrop blur
- **Text:** white, small (12-13px)
- **Height:** compact — ~50-60px expanded, ~32px collapsed
- **Collapse toggle:** small icon button (top-right corner or inline) toggles to a
  minimal pill showing only a legend icon

### Gradient Bar

- CSS `linear-gradient(to right, color1, color2, ...)` inside a rounded div
- Height: ~12px
- Start/end labels below the gradient, left/right aligned
- Optional title centered above

### Discrete Items

- Horizontal row of color chips (small 14x14 rounded squares) + labels
- Wraps to second line if too many items
- Arranged below the gradient (if any)

### Collapsed State

- A small pill/chip: legend icon (`mdi-map-legend`) only
- Click to expand back

### Responsiveness

- If the map is narrow (< 500px), stack gradient above discrete items vertically
- The component should never exceed 90% of the map width

## File Structure

```
pysepal/solara/components/
  legend.py                    # LegendComponent, LegendData, GradientEntry, DiscreteEntry
  vue/
    Legend.vue                 # Vue template + scoped CSS
```

## Integration with MapApp

The component renders as a child of the map area. In GFC page.py:

```python
MapApp.element(
    app_title="Global Forest Change",
    main_map=[sepal_map, LegendComponent(legend_data=asdict(legend))],
    ...
)
```

Or rendered alongside the map in the page component — exact integration
depends on how MapApp passes `main_map` children to the Vue template.
If `main_map` only accepts a single SepalMap widget, the legend could be
added directly to the SepalMap's ipyleaflet layer stack as a custom Control
with CSS overrides, or rendered as a sibling element in the page.

**Fallback approach:** If CSS absolute positioning within MapApp is tricky,
render the `LegendComponent` in the page component and use a `use_effect`
to append it to the map's DOM container via JavaScript.

## What This Does NOT Cover

- Replacing the existing `LegendControl` in pysepal (it stays for legacy apps)
- Chart legends (ECharts has its own legend system)
- Interactive legend (click to filter layers) — future enhancement
- Legend extraction from EE viz_params (factory/builder) — future enhancement

## Testing

- Unit test: verify `LegendData` serialization with `asdict()`
- Visual test: render component in the pysepal template app with sample data
- Integration test: verify it renders inside GFC's MapApp without errors
