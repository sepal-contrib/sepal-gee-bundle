"""Map visualization helpers for basin rivers."""

from typing import Callable, Iterable

from ipyleaflet import GeoJSON
from vectortileserver import categorized_style

from apps.basin_rivers.scripts.statistics import basin_color_map

BASIN_STYLE = {"fillOpacity": 0.1, "weight": 2}
BASIN_HOVER_STYLE = {"color": "white", "dashArray": "0", "fillOpacity": 0, "weight": 3}
SELECTED_STYLE = {"fillOpacity": 0.1, "weight": 2, "color": "black"}


def create_basins_layer(geojson_data: dict, name: str = "Upstream catchment") -> GeoJSON:
    """Create an ipyleaflet GeoJSON layer from upstream basin data.

    Args:
        geojson_data: GeoJSON dict from ee.FeatureCollection.getInfo().
        name: Layer name on the map.

    Returns:
        ipyleaflet.GeoJSON layer with styling and hover interaction.
    """
    return GeoJSON(
        data=geojson_data,
        name=name,
        style=BASIN_STYLE,
        hover_style=BASIN_HOVER_STYLE,
    )


def create_selection_layer(geojson_data: dict, name: str = "Selected") -> GeoJSON:
    """Create a GeoJSON layer for selected/highlighted basins."""
    return GeoJSON(
        data=geojson_data,
        name=name,
        style=SELECTED_STYLE,
    )


def basin_tile_style(hybas_ids: Iterable) -> Callable[[dict, str], dict]:
    """Style builder coloring each basin the same color as its dashboard bar.

    Args:
        hybas_ids: the basin ids present in the archive.

    Returns:
        a builder for ``TileWorkspace.open_async(style=...)``.
    """
    # The tiles carry HYBAS_ID as a number, so the match values must be numeric
    # even though the shared color map is keyed by string. Deriving values first
    # and building the color map from them keeps this to one normalization and
    # one pass over hybas_ids, so a one-shot iterator works too.
    values = sorted({int(b) for b in hybas_ids})
    colors = basin_color_map(values)

    return categorized_style(
        "HYBAS_ID",
        values,
        colors=[colors[str(v)] for v in values] or None,
    )
