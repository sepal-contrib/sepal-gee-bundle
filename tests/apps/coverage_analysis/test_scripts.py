"""Tests for Coverage Analysis pure helpers (no live GEE)."""

from unittest.mock import MagicMock, patch

from apps.coverage_analysis.params import (
    COUNT_BAND_SR,
    LANDSAT_C02_SR,
    LANDSAT_C02_TOA,
    MEASURE_ITEMS,
    NDVI_BANDS_SR,
    NDVI_BANDS_TOA,
    SENSOR_ITEMS,
    STATS_ITEMS,
    TEMP_ITEMS,
)
from apps.coverage_analysis.scripts.analysis import (
    MEASURE_BAND,
    MEASURE_REDUCER,
    year_windows,
)
from apps.coverage_analysis.scripts.collection_builder import (
    _landsat_id,
    _t2_id,
    build_asset_name,
)


class TestParamsConsistency:
    def test_c02_asset_ids(self):
        for sensor, asset_id in LANDSAT_C02_SR.items():
            assert asset_id.startswith("LANDSAT/")
            assert "/C02/" in asset_id
            assert asset_id.endswith("_L2")
            assert sensor in LANDSAT_C02_TOA

        for asset_id in LANDSAT_C02_TOA.values():
            assert "/C02/" in asset_id
            assert asset_id.endswith("_TOA")

    def test_ndvi_bands_coverage(self):
        assert set(NDVI_BANDS_SR.keys()) == set(NDVI_BANDS_TOA.keys())
        assert "s2" in NDVI_BANDS_SR
        # NDVI bands must be (NIR, RED) tuples
        for bands in NDVI_BANDS_SR.values():
            assert len(bands) == 2
            assert all(isinstance(b, str) for b in bands)

    def test_count_band_sr_covers_sensors(self):
        for sensor in ("l4", "l5", "l7", "l8", "s2"):
            assert sensor in COUNT_BAND_SR

    def test_ui_item_shapes(self):
        for items in (SENSOR_ITEMS, MEASURE_ITEMS, STATS_ITEMS, TEMP_ITEMS):
            for item in items:
                assert "text" in item and "value" in item


class TestCollectionBuilderHelpers:
    def test_landsat_id_sr_vs_toa(self):
        assert _landsat_id("l8", sr=True) == "LANDSAT/LC08/C02/T1_L2"
        assert _landsat_id("l8", sr=False) == "LANDSAT/LC08/C02/T1_TOA"

    def test_t2_id_replaces_tier(self):
        assert _t2_id("LANDSAT/LC08/C02/T1_L2") == "LANDSAT/LC08/C02/T2_L2"
        assert _t2_id("LANDSAT/LE07/C02/T1_TOA") == "LANDSAT/LE07/C02/T2_TOA"

    def test_build_asset_name(self):
        name = build_asset_name(
            aoi_name="my area",
            start="2020-01-01",
            end="2020-12-31",
            sensors=["l8", "s2"],
            sr=True,
        )
        assert "my_area" in name
        assert "2020-01-01" in name
        assert "_L8_" in name
        assert "_S2_" in name
        assert name.endswith("_SR")

    def test_build_asset_name_toa(self):
        name = build_asset_name(
            aoi_name="aoi",
            start="2019-01-01",
            end="2019-12-31",
            sensors=["l4"],
            sr=False,
        )
        assert name.endswith("_TOA")
        assert "_L4_" in name


class TestYearWindows:
    def test_empty_when_invalid_range(self):
        assert year_windows("2020-06-01", "2020-01-01") == []
        assert year_windows("2020-01-01", "2020-01-01") == []

    def test_single_year(self):
        windows = year_windows("2020-01-01", "2020-12-31")
        assert len(windows) == 1
        assert windows[0] == ("2020-01-01", "2020-12-31", 2020)

    def test_crosses_year_boundary(self):
        windows = year_windows("2019-06-01", "2021-03-01")
        # 2019-06-01 -> 2020-01-01 (year=2019)
        # 2020-01-01 -> 2021-01-01 (year=2020)
        # 2021-01-01 -> 2021-03-01 (year=2021)
        assert len(windows) == 3
        assert windows[0] == ("2019-06-01", "2020-01-01", 2019)
        assert windows[1] == ("2020-01-01", "2021-01-01", 2020)
        assert windows[2] == ("2021-01-01", "2021-03-01", 2021)


class TestAnalysisTables:
    def test_measure_band_and_reducer_parity(self):
        assert set(MEASURE_BAND.keys()) == set(MEASURE_REDUCER.keys())
        for measure, band in MEASURE_BAND.items():
            assert band in ("NDVI", "COUNT")


class TestBuildCollection:
    """Smoke-test build_collection by patching ee."""

    @patch("apps.coverage_analysis.scripts.collection_builder.ee")
    def test_returns_none_if_no_sensors(self, mock_ee):
        from apps.coverage_analysis.scripts.collection_builder import build_collection

        assert (
            build_collection(
                aoi=MagicMock(), start="2020-01-01", end="2020-12-31", sensors=[], sr=True
            )
            is None
        )

    @patch("apps.coverage_analysis.scripts.collection_builder.ee")
    def test_single_landsat_pipeline_calls(self, mock_ee):
        from apps.coverage_analysis.scripts.collection_builder import build_collection

        result = build_collection(
            aoi=MagicMock(),
            start="2020-01-01",
            end="2020-12-31",
            sensors=["l8"],
            sr=True,
            include_t2=False,
        )
        # Should have constructed an ImageCollection for Landsat 8 C02 L2.
        mock_ee.ImageCollection.assert_any_call("LANDSAT/LC08/C02/T1_L2")
        assert result is not None
