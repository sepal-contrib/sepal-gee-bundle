"""Pour point selection via map click or manual coordinate entry."""

import logging

import reacton.ipyvuetify as rv
import solara
from ipyleaflet import Marker
from pysepal.solara.notifications import use_notifications

logger = logging.getLogger("sepal_gee_bundle.basin_rivers")


@solara.component
def PointStep(state, sepal_map):
    """Select a pour point by clicking the map or entering coordinates manually."""
    notifications = use_notifications()
    lat_text, set_lat_text = solara.use_state("")
    lon_text, set_lon_text = solara.use_state("")

    def _update_marker(lat, lon):
        """Add or replace the pour point marker on the map."""
        existing = sepal_map.find_layer("Pour Point", none_ok=True)
        if existing:
            sepal_map.remove_layer(existing)
        marker = Marker(location=[lat, lon], draggable=False, name="Pour Point")
        sepal_map.add_layer(marker, key="Pour Point")

    def _register_click():
        def handle(**kwargs):
            if kwargs.get("type") == "click" and not state.manual_coords.value:
                lat, lon = kwargs["coordinates"]
                lat = round(lat, 6)
                lon = round(lon, 6)
                state.lat.set(lat)
                state.lon.set(lon)
                _update_marker(lat, lon)
                notifications.success(f"Pour point set: {lat:.6f}, {lon:.6f}")
                logger.debug("Pour point set via click: %s, %s", lat, lon)

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
        notifications.success(f"Pour point set: {lat:.6f}, {lon:.6f}")
        logger.debug("Pour point set manually: %s, %s", lat, lon)

    with solara.Column():
        rv.Switch(
            v_model=state.manual_coords.value,
            on_v_model=state.manual_coords.set,
            label="Manual coordinates",
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
                "Set Point",
                on_click=_set_manual_point,
                color="primary",
                small=True,
                block=True,
            )
        else:
            solara.Text("Click on the map to select a pour point.")

        if state.lat.value is not None and state.lon.value is not None:
            solara.Text(f"Pour point: {state.lat.value:.6f}, {state.lon.value:.6f}")
