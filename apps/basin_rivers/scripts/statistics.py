"""Zonal statistics per catchment using reduceRegions."""

import ee
import pandas as pd

from apps.basin_rivers.params import GFC_COLORS_DICT, GFC_DATASET, GFC_MAX_YEAR, GFC_TRANSLATION


def compute_zonal_stats(
    gfc_image: ee.Image,
    feature_collection: ee.FeatureCollection,
) -> ee.FeatureCollection:
    """Server-side reduceRegions with group reducer.

    Returns ee.FeatureCollection where each feature has a 'groups' property.
    """
    return (
        ee.Image.pixelArea()
        .divide(10000)
        .addBands(gfc_image)
        .reduceRegions(
            collection=feature_collection,
            reducer=ee.Reducer.sum().group(1),
            scale=ee.Image(GFC_DATASET).projection().nominalScale(),
        )
    )


def parse_zonal_stats(raw_result: dict) -> pd.DataFrame:
    """Parse reduceRegions getInfo() result into a tidy DataFrame.

    Returns DataFrame with columns: basin, variable, area, group, year, color.
    """
    hybas_stats = {}
    for feature in raw_result.get("features", []):
        hybas_id = feature["properties"]["HYBAS_ID"]
        groups = feature["properties"].get("groups", [])
        hybas_stats[hybas_id] = {int(g["group"]): g["sum"] for g in groups}

    if not hybas_stats:
        return pd.DataFrame(columns=["basin", "variable", "area", "group", "year", "color"])

    df = (
        pd.DataFrame.from_dict(hybas_stats, orient="index")
        .reset_index()
        .melt(id_vars=["index"], var_name="variable", value_name="area")
        .rename(columns={"index": "basin"})
    )

    df["basin"] = df["basin"].astype(str)
    df["variable"] = df["variable"].astype(int)
    df["area"] = df["area"].fillna(0.0)
    df["group"] = df["variable"].map(GFC_TRANSLATION).fillna("unknown")
    df["year"] = df["variable"].apply(lambda x: x + 2000 if 1 <= x <= GFC_MAX_YEAR else 0)
    df["color"] = df["group"].map(GFC_COLORS_DICT).fillna("#888888")

    return df


from apps.basin_rivers.params import CATCH_COLOR_PALETTE


def add_catchment_colors(df: pd.DataFrame) -> pd.DataFrame:
    """Add a deterministic `catch_color` column keyed on sorted basin id.

    Same basin always gets the same color. If there are more basins than palette
    entries, the palette cycles.
    """
    if df.empty or "basin" not in df.columns:
        return df.assign(catch_color=pd.Series(dtype=str))

    basins_sorted = sorted(df["basin"].astype(str).unique())
    palette = CATCH_COLOR_PALETTE
    mapping = {b: palette[i % len(palette)] for i, b in enumerate(basins_sorted)}
    out = df.copy()
    out["catch_color"] = out["basin"].astype(str).map(mapping)
    return out


def get_overall_pie_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate area per group (change class) for the overall donut."""
    if df.empty:
        return pd.DataFrame(columns=["group", "area", "color"])

    grouped = df.groupby("group", as_index=False)["area"].sum()
    grouped["color"] = grouped["group"].map(GFC_COLORS_DICT).fillna("#888888")
    return grouped.sort_values("area", ascending=False).reset_index(drop=True)


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
