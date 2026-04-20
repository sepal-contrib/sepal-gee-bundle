"""Map visualization helpers for basin rivers."""

from ipyleaflet import GeoJSON

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
