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

    Emits one pair of layers per palette color, each selecting its basins with
    a filter, rather than one pair carrying a ``match`` on the color. The
    renderer behind ``PMTilesLayer`` is protomaps-leaflet, which evaluates
    filters (``==``, ``in``, ``!in``, comparisons) but not data-driven paint
    expressions -- its only paint function is zoom interpolation, so a
    ``["match", ["get", "HYBAS_ID"], ...]`` silently renders as one flat
    default color. Layer count is bounded by the palette, not the basin count.

    The fill stays a faint tint of that color rather than fully transparent:
    click-to-inspect (``VectorTileLayer.get_data_from_coords``) skips a fill
    layer whose ``fill-opacity`` is 0, so a see-through basin would stop being
    clickable.

    Args:
        hybas_ids: the basin ids present in the archive.

    Returns:
        a builder for ``TileWorkspace.open_async(style=...)``.
    """
    # The tiles carry HYBAS_ID as a number, and the filter compares it to the
    # listed values with `includes`, so the ids must be numeric even though the
    # shared color map is keyed by string. Deriving values first and building
    # the color map from them keeps this to one normalization and one pass over
    # hybas_ids, so a one-shot iterator works too.
    values = sorted({int(b) for b in hybas_ids})
    colors = basin_color_map(values)

    # One group per distinct color, each keeping the palette's first-use order
    # so the emitted layers are stable between runs.
    groups: dict[str, list[int]] = {}
    for value in values:
        groups.setdefault(colors[str(value)], []).append(value)

    def _paint_pair(source_layer, minzoom, maxzoom, color, ids):
        common = {
            "source": "pmtiles_source",
            "source-layer": source_layer,
            "minzoom": minzoom,
            "maxzoom": maxzoom,
        }
        # An unfiltered pair when there is nothing to select on: an archive with
        # no ids still has to draw as something.
        selector = ["in", "HYBAS_ID", *ids] if ids else None
        suffix = color.lstrip("#") if ids else "all"

        fill = {
            "id": f"{source_layer}-{suffix}-fill",
            "type": "fill",
            **common,
            "paint": {"fill-color": color, "fill-opacity": BASIN_FILL_OPACITY},
        }
        line = {
            "id": f"{source_layer}-{suffix}-line",
            "type": "line",
            **common,
            "paint": {
                "line-color": color,
                "line-width": BASIN_LINE_WIDTH,
                "line-opacity": BASIN_LINE_OPACITY,
            },
        }
        if selector is not None:
            fill["filter"] = selector
            line["filter"] = selector

        return [fill, line]

    def _build(metadata: dict, pmtiles_url: str) -> dict:
        layers = []
        for vector_layer in metadata.get("vector_layers", []):
            source_layer = vector_layer["id"]
            minzoom = vector_layer.get("minzoom", 0)
            maxzoom = vector_layer.get("maxzoom", 22)

            if groups:
                for color, ids in groups.items():
                    layers += _paint_pair(source_layer, minzoom, maxzoom, color, ids)
            else:
                layers += _paint_pair(
                    source_layer, minzoom, maxzoom, BASIN_FALLBACK_COLOR, []
                )

        return {
            "version": 8,
            "sources": {"pmtiles_source": {"type": "vector", "url": f"pmtiles://{pmtiles_url}"}},
            "layers": layers,
        }

    return _build
