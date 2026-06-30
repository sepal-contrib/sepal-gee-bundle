"""Map helpers shared across bundle apps."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pysepal.mapping import SepalMap


def add_satellite_basemap(sepal_map: SepalMap, basemap: str = "SATELLITE") -> SepalMap:
    """Add a satellite basemap as a hidden, switchable secondary basemap.

    The map keeps its theme-aware default (CartoDB light/dark) as the active
    basemap; the satellite layer is added hidden so it never becomes the
    default, and the user can switch to it via the map's layers control.
    The same map is returned for convenient chaining inside ``use_memo``.
    """
    sepal_map.add_basemap(basemap)
    sepal_map.layers[-1].visible = False
    return sepal_map
