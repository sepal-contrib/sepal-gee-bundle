"""JRC TMF dataset constants and visualization parameters."""

from pysepal.solara.components.legend import DiscreteEntry, GradientEntry, LegendData

from apps._commons.datasets import JRC_TMF_VERSION_YEAR, jrc_tmf_id

# --- JRC TMF dataset version ---
# Sourced from ``apps._commons.datasets`` so all apps stay in lockstep.
TMF_VERSION_YEAR = JRC_TMF_VERSION_YEAR

# The Annual Changes collection covers 1990..TMF_VERSION_YEAR inclusive.
TMF_MIN_YEAR = 1990
TMF_MAX_YEAR = TMF_VERSION_YEAR


def deg_dataset_id() -> str:
    return jrc_tmf_id("DegradationYear")


def def_dataset_id() -> str:
    return jrc_tmf_id("DeforestationYear")


def chg_dataset_id() -> str:
    return jrc_tmf_id("AnnualChanges")


# --- TMF layer types ---
# Degradation, Deforestation share the same "year of event" schema
# Annual Change is a per-year categorical band stack.
TMF_TYPES = [
    {"value": "DEG", "label": "Degradation year", "icon": "mdi-tree"},
    {"value": "DEF", "label": "Deforestation year", "icon": "mdi-tree-outline"},
    {"value": "CHG", "label": "Annual change", "icon": "mdi-calendar-range"},
]

# --- Visualization ---
# Degradation / deforestation year palette: blue -> yellow -> red
TMF_YEAR_PALETTE = ["#0000ff", "#ffff00", "#ff0000"]

# Annual Change classes (per JRC TMF v1 documentation).
# Each year band stores one of these codes.
TMF_CHG_CLASSES = [
    (1, "Undisturbed TMF", "#0d5c00"),
    (2, "Degraded TMF", "#8fbc8f"),
    (3, "Deforested land", "#ff7f50"),
    (4, "Forest regrowth", "#6b8e23"),
    (5, "Permanent/seasonal water", "#1e90ff"),
    (6, "Other land cover", "#d3d3d3"),
]


def year_viz_params(year_start: int, year_end: int) -> dict:
    """Visualization params for DEG/DEF (single year band)."""
    return {
        "min": year_start,
        "max": year_end,
        "palette": TMF_YEAR_PALETTE,
    }


def change_viz_params(year_start: int, year_end: int) -> dict:
    """Visualization params for CHG (year stack, RGB composite).

    Reproduces legacy behaviour: start-start-end band triplet with categorical
    min/max = 1/3.
    """
    return {
        "bands": [f"Dec{year_start}", f"Dec{year_start}", f"Dec{year_end}"],
        "min": 1,
        "max": 3,
        "opacity": 1.0,
        "gamma": 1.0,
    }


def export_vis_params_for(tmf_type: str, year_start: int, year_end: int) -> dict:
    """Return SEPAL-convention ``set_viz_params`` kwargs for an exported TMF image.

    Different shape from the map-side ``viz_params_for`` because pysepal's
    :func:`set_viz_params` accepts ``name`` / ``type`` / ``bands`` / ``min`` /
    ``max`` / ``palette`` / ``values`` / ``labels`` (no ``gamma`` / ``opacity``).
    Attached to ``ResolvedExport.vis_params`` so the exported asset carries
    ``visualization_*`` properties readable by SepalMap and other SEPAL recipes.
    """
    if tmf_type in ("DEG", "DEF"):
        return {
            "name": f"tmf_{tmf_type.lower()}",
            "type": "continuous",
            "min": year_start,
            "max": year_end,
            "palette": TMF_YEAR_PALETTE,
        }
    if tmf_type == "CHG":
        return {
            "name": "tmf_chg",
            "type": "rgb",
            "bands": [f"Dec{year_start}", f"Dec{year_start}", f"Dec{year_end}"],
            "min": 1,
            "max": 3,
        }
    raise ValueError(f"Unknown TMF type: {tmf_type!r}")


# --- Legends ---
def year_legend(tmf_type: str, year_start: int, year_end: int) -> LegendData:
    title = "Degradation year" if tmf_type == "DEG" else "Deforestation year"
    return LegendData(
        gradients=[
            GradientEntry(
                colors=TMF_YEAR_PALETTE,
                labels=[str(year_start), str((year_start + year_end) // 2), str(year_end)],
                title=title,
            ),
        ],
    )


def change_legend() -> LegendData:
    return LegendData(
        items=[DiscreteEntry(label, color) for _, label, color in TMF_CHG_CLASSES],
    )


def asset_basename(aoi_name: str, tmf_type: str, year_start: int, year_end: int) -> str:
    """Default name used for GEE asset / Drive / SEPAL exports."""
    safe = (aoi_name or "aoi").replace(" ", "_")
    return f"tmf_{tmf_type}_{safe}_{year_start}_{year_end}"
