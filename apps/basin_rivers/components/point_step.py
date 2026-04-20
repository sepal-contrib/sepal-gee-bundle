"""Outlet point selection via map click or manual coordinate entry."""

import logging

import reacton.ipyvuetify as rv
import solara
from ipyleaflet import Marker
from pysepal.solara.notifications import use_notifications

logger = logging.getLogger("sepal_gee_bundle.basin_rivers")

_OUTLET_LAYER = "Outlet"


@solara.component
def PointStep(state, sepal_map):
    """Pick a watershed outlet by clicking the map or entering coordinates."""
    notifications = use_notifications()
    lat_text, set_lat_text = solara.use_state("")
    lon_text, set_lon_text = solara.use_state("")

    def _update_marker(lat, lon):
        existing = sepal_map.find_layer(_OUTLET_LAYER, none_ok=True)
        if existing:
            sepal_map.remove_layer(existing)
        marker = Marker(location=[lat, lon], draggable=False, name=_OUTLET_LAYER)
        sepal_map.add_layer(marker, key=_OUTLET_LAYER)

    def _register_click():
        def handle(**kwargs):
            if kwargs.get("type") == "click" and not state.manual_coords.value:
                lat, lon = kwargs["coordinates"]
                lat = round(lat, 6)
                lon = round(lon, 6)
                state.lat.set(lat)
                state.lon.set(lon)
                _update_marker(lat, lon)
                notifications.success(f"Outlet set: {lat:.6f}, {lon:.6f}")
                logger.debug("Outlet set via click: %s, %s", lat, lon)

        sepal_map.on_interaction(handle)

    solara.use_effect(_register_click, [])

    def _set_manual_point(*_args):
        try:
            lat = float(lat_text)
            lon = float(lon_text)
        except ValueError:
            notifications.error("Invalid coordinates — enter numeric latitude and longitude.")
            return
        state.lat.set(lat)
        state.lon.set(lon)
        _update_marker(lat, lon)
        notifications.success(f"Outlet set: {lat:.6f}, {lon:.6f}")
        logger.debug("Outlet set manually: %s, %s", lat, lon)

    with solara.Column():
        rv.Switch(
            v_model=state.manual_coords.value,
            on_v_model=state.manual_coords.set,
            label="Manual coordinates",
            dense=True,
        )

        if state.manual_coords.value:
            rv.TextField(
                v_model=lat_text,
                on_v_model=set_lat_text,
                label="Latitude",
                type="number",
                dense=True,
                outlined=True,
            )
            rv.TextField(
                v_model=lon_text,
                on_v_model=set_lon_text,
                label="Longitude",
                type="number",
                dense=True,
                outlined=True,
            )
            solara.Button(
                "Set outlet",
                on_click=_set_manual_point,
                color="primary",
                small=True,
                block=True,
            )
        else:
            rv.Alert(
                type="info",
                text=True,
                dense=True,
                border="left",
                icon="mdi-gesture-tap",
                children=["Click on the map to pick a watershed outlet."],
                class_="mt-2 mb-0",
            )

        if state.lat.value is not None and state.lon.value is not None:
            rv.Chip(
                color="primary",
                text_color="white",
                small=True,
                class_="mt-3",
                children=[
                    rv.Icon(left=True, small=True, children=["mdi-crosshairs-gps"]),
                    f"{state.lat.value:.5f}, {state.lon.value:.5f}",
                ],
            )
