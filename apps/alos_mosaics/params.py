"""ALOS PALSAR / PALSAR-2 yearly mosaic constants and visualization parameters.

Ported from the legacy ``alos_mosaics/component/parameter/`` tree. Only the
GEE datasets, year list, visualization params, speckle-filter options and
export-naming logic are preserved; all sepal_ui / ipyvuetify / traitlets
wrappers have been dropped.
"""

from __future__ import annotations

from pysepal.solara.components.legend import DiscreteEntry, GradientEntry, LegendData

from apps._commons.datasets import (
    ALOS_PALSAR_FNF_ID,
    ALOS_PALSAR_FNF_LAST_YEAR,
    ALOS_PALSAR_SAR_ID,
    ALOS_PALSAR_YEARS,
)

# --- GEE dataset IDs ---------------------------------------------------------
ALOS_SAR_COLLECTION = ALOS_PALSAR_SAR_ID
ALOS_FNF_COLLECTION = ALOS_PALSAR_FNF_ID

# --- Years -------------------------------------------------------------------
ALOS_YEARS = list(ALOS_PALSAR_YEARS)
LAST_FNF_YEAR = ALOS_PALSAR_FNF_LAST_YEAR

# --- Speckle filters ---------------------------------------------------------
SPECKLE_NONE = "NONE"
SPECKLE_REFINED_LEE = "REFINED_LEE"
SPECKLE_QUEGAN = "QUEGAN"

SPECKLE_FILTERS = [
    {"text": "No speckle filter", "value": SPECKLE_NONE},
    {"text": "Refined Lee (zoom dependent)", "value": SPECKLE_REFINED_LEE},
    {"text": "Quegan filter", "value": SPECKLE_QUEGAN},
]

DEFAULT_SPECKLE_DICT = {"radius": 30, "units": "meters"}

# --- Visualization layers (RadioGroup values) -------------------------------
VIZ_RGB = "RGB"
VIZ_RFDI = "RFDI"
VIZ_FNF = "FNF"

VIZ_LAYERS = [
    {"label": "Backscatter RGB (HH, HV, HH/HV power ratio)", "value": VIZ_RGB},
    {
        "label": "Radar Forest Degradation Index (RFDI, Mitchard et al. 2012)",
        "value": VIZ_RFDI,
    },
    {
        "label": "Forest / Non-Forest (available only until 2017)",
        "value": VIZ_FNF,
    },
]

# --- Visualization params (ported verbatim from legacy parameter/viz.py) -----
VIS_PARAM_DB = {
    "bands": ["HH", "HV", "HHHV_ratio"],
    "min": [-20, -25, 1],
    "max": [0, -5, 15],
    "gamma": 1.1,
}

VIS_PARAM_POW = {
    "bands": ["HH", "HV", "HHHV_ratio"],
    "min": [0, 0, 1],
    "max": [0.5, 0.15, 15],
    "gamma": 1.1,
}

VIS_PARAM_RFDI = {
    "min": 0.25,
    "max": 1,
    "palette": ["#105e1e", "#fffa6c"],
}

# FNF classes: 1=Forest, 2=Non-forest, 3=Water
VIS_PARAM_FNF = {
    "min": 1,
    "max": 3,
    "palette": ["#006400", "#FEFF99", "#0000FF"],
}

FNF_CLASSES = [
    (1, "Forest", "#006400"),
    (2, "Non-forest", "#FEFF99"),
    (3, "Water", "#0000FF"),
]


# --- Legends -----------------------------------------------------------------
def fnf_legend() -> LegendData:
    return LegendData(
        items=[DiscreteEntry(label, color) for _, label, color in FNF_CLASSES],
    )


def rfdi_legend() -> LegendData:
    return LegendData(
        gradients=[
            GradientEntry(
                title="Radar Forest Degradation Index",
                colors=list(VIS_PARAM_RFDI["palette"]),
                labels=[str(VIS_PARAM_RFDI["min"]), str(VIS_PARAM_RFDI["max"])],
            )
        ],
    )


def rgb_legend(db: bool) -> LegendData:
    """Channel-to-band mapping for the SAR RGB composite.

    A multi-band RGB has no single colorbar, and chips that name specific
    land covers ("forest = #a3b300") imply a precision SAR doesn't have.
    So the legend stays honest: each chip is the literal color used to
    encode one SAR band. Interpretation guidance (what colors *tend to*
    mean for forest / water / urban) lives in the "How to read this
    image" dialog, where the variability can be qualified properly.
    """
    del db  # channel mapping is identical in dB and power modes
    return LegendData(
        items=[
            DiscreteEntry("HH (co-pol)", "#ff0000"),
            DiscreteEntry("HV (cross-pol)", "#00ff00"),
            DiscreteEntry("HH/HV ratio", "#0000ff"),
        ],
    )


# --- Export visualization ----------------------------------------------------
def export_vis_rgb(db: bool) -> dict:
    """SEPAL ``set_viz_params`` kwargs for the HH/HV/HH-HV-ratio composite.

    Attached to the exported ALOS mosaic when the backscatter triplet is
    included, so the GEE asset carries ``visualization_*`` properties readable
    by SepalMap and other SEPAL recipes.
    """
    vis = VIS_PARAM_DB if db else VIS_PARAM_POW
    return {
        "name": "alos_rgb",
        "type": "rgb",
        "bands": list(vis["bands"]),
        "min": list(vis["min"]),
        "max": list(vis["max"]),
    }


def export_vis_fnf(year: int) -> dict:
    """SEPAL ``set_viz_params`` kwargs for the FNF band of ``year``."""
    return {
        "name": "alos_fnf",
        "type": "categorical",
        "bands": [f"fnf_{year}"],
        "values": [code for code, _, _ in FNF_CLASSES],
        "labels": [label for _, label, _ in FNF_CLASSES],
        "palette": list(VIS_PARAM_FNF["palette"]),
    }


# --- Export naming -----------------------------------------------------------
def asset_name(
    aoi_name: str,
    year: int,
    speckle_filter: str = SPECKLE_NONE,
    rfdi: bool = False,
    ls_mask: bool = False,
    db: bool = False,
    texture: bool = False,
    aux: bool = False,
    fnf: bool = False,
) -> str:
    """Return the default asset / file name for an ALOS mosaic export.

    Mirrors legacy ``parameter.values.asset_name`` behaviour.
    """
    prefix = "kc_fnf" if fnf else "alos_mosaic"
    safe = (aoi_name or "aoi").replace(" ", "_")
    name = f"{prefix}_{safe}_{year}"

    if speckle_filter and speckle_filter != SPECKLE_NONE:
        name += f"_{speckle_filter.lower()}"
    if rfdi:
        name += "_rfdi"
    if ls_mask:
        name += "_masked"
    if db:
        name += "_dB"
    if texture:
        name += "_texture"
    if aux:
        name += "_aux"
    return name


def fnf_available(year: int) -> bool:
    """Return True when a FNF band is available for the given year."""
    return year <= LAST_FNF_YEAR
