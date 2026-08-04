"""Map visualization helpers for basin rivers."""

from typing import Callable, Iterable

from ipyleaflet import GeoJSON

from apps.basin_rivers.scripts.statistics import basin_color_map

SELECTED_STYLE = {"fillOpacity": 0.1, "weight": 2, "color": "black"}

BASIN_LINE_WIDTH = 2.5
BASIN_LINE_OPACITY = 0.9
BASIN_FILL_OPACITY = 0.08
BASIN_FALLBACK_COLOR = "#CCCCCC"


def create_selection_layer(geojson_data: dict, name: str = "Selected") -> GeoJSON:
    """Create a GeoJSON layer for selected/highlighted basins."""
    return GeoJSON(
        data=geojson_data,
        name=name,
        style=SELECTED_STYLE,
    )


def basin_tile_style(hybas_ids: Iterable) -> Callable[[dict, str], dict]:
    """Style builder outlining each basin the same color as its dashboard bar.

    The fill stays a faint tint of that color rather than fully transparent:
    click-to-inspect (``VectorTileLayer.get_data_from_coords``) skips a fill
    layer whose ``fill-opacity`` is 0, so a see-through basin would stop being
    clickable.

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

    if values:
        color_expr = ["match", ["get", "HYBAS_ID"]]
        for value in values:
            color_expr += [value, colors[str(value)]]
        color_expr.append(BASIN_FALLBACK_COLOR)
    else:
        color_expr = BASIN_FALLBACK_COLOR

    def _build(metadata: dict, pmtiles_url: str) -> dict:
        layers = []
        for vector_layer in metadata.get("vector_layers", []):
            source_layer = vector_layer["id"]
            minzoom = vector_layer.get("minzoom", 0)
            maxzoom = vector_layer.get("maxzoom", 22)
            layers.append(
                {
                    "id": f"{source_layer}-fill",
                    "type": "fill",
                    "source": "pmtiles_source",
                    "source-layer": source_layer,
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "paint": {"fill-color": color_expr, "fill-opacity": BASIN_FILL_OPACITY},
                }
            )
            layers.append(
                {
                    "id": f"{source_layer}-line",
                    "type": "line",
                    "source": "pmtiles_source",
                    "source-layer": source_layer,
                    "minzoom": minzoom,
                    "maxzoom": maxzoom,
                    "paint": {
                        "line-color": color_expr,
                        "line-width": BASIN_LINE_WIDTH,
                        "line-opacity": BASIN_LINE_OPACITY,
                    },
                }
            )
        return {
            "version": 8,
            "sources": {"pmtiles_source": {"type": "vector", "url": f"pmtiles://{pmtiles_url}"}},
            "layers": layers,
        }

    return _build
