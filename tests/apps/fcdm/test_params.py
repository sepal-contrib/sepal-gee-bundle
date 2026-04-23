"""Tests for FCDM params and helpers."""

from apps.fcdm.params import (
    DELTA_NBR_VIS,
    FOREST_MAP_ITEMS,
    HANSEN_GFC,
    JRC_ROADLESS,
    SENSOR_ITEMS,
    SENSORS,
    viz_forest_mask,
)


class TestSensors:
    def test_all_sensors_have_required_bands(self):
        required = {"blue", "green", "red", "nir", "swir1", "swir2"}
        for name, cfg in SENSORS.items():
            missing = required - set(cfg["bands"])
            assert not missing, f"{name} missing bands: {missing}"

    def test_landsat_uses_c02(self):
        for name, cfg in SENSORS.items():
            if "landsat" not in name:
                continue
            assert "C02" in cfg["dataset"]["sr"], f"{name} SR must be C02"
            assert "C02" in cfg["dataset"]["toa"], f"{name} TOA must be C02"

    def test_sentinel2_uses_harmonized(self):
        ds = SENSORS["sentinel 2"]["dataset"]
        assert "HARMONIZED" in ds["sr"]
        assert "HARMONIZED" in ds["toa"]

    def test_sensor_items_match_sensors(self):
        assert {item["value"] for item in SENSOR_ITEMS} == set(SENSORS)


class TestForestMask:
    def test_forest_map_items_values(self):
        values = {item["value"] for item in FOREST_MAP_ITEMS}
        assert values == {"gfc", "roadless", "no_map", "custom"}

    def test_viz_forest_mask_known_keys(self):
        for key in ("gfc", "roadless", "no_map"):
            viz = viz_forest_mask(key)
            assert "palette" in viz

    def test_viz_forest_mask_fallback(self):
        assert viz_forest_mask("totally_unknown") == viz_forest_mask("gfc")


class TestDatasets:
    def test_hansen_dataset_is_set(self):
        assert HANSEN_GFC.startswith("UMD/hansen/")

    def test_jrc_dataset_is_set(self):
        assert JRC_ROADLESS.startswith("projects/JRC/TMF/")


class TestDeltaNbrVis:
    def test_delta_nbr_vis_shape(self):
        assert DELTA_NBR_VIS["min"] == 0
        assert DELTA_NBR_VIS["max"] == 0.3
        assert len(DELTA_NBR_VIS["palette"]) == 2
