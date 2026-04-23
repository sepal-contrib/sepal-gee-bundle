"""Tests for FCDM pure-function scripts."""

from unittest.mock import MagicMock, patch

import pytest


class TestForestMask:
    @patch("apps.fcdm.scripts.forest_mask.ee")
    def test_gfc_path_uses_treecover(self, mock_ee):
        from apps.fcdm.scripts.forest_mask import get_forest_mask

        aoi = MagicMock()
        mask, display = get_forest_mask("gfc", year=2020, treecover=70, aoi=aoi)
        assert mask is not None
        assert display is not None
        mock_ee.Image.assert_called()

    @patch("apps.fcdm.scripts.forest_mask.ee")
    def test_roadless_selects_year_band(self, mock_ee):
        from apps.fcdm.scripts.forest_mask import get_forest_mask

        aoi = MagicMock()
        get_forest_mask("roadless", year=2019, treecover=0, aoi=aoi)
        mock_ee.ImageCollection.assert_called()

    @patch("apps.fcdm.scripts.forest_mask.ee")
    def test_no_map_returns_full_mask(self, mock_ee):
        from apps.fcdm.scripts.forest_mask import get_forest_mask

        aoi = MagicMock()
        mask, display = get_forest_mask("no_map", year=2020, treecover=0, aoi=aoi)
        assert mask is not None
        assert display is not None

    @patch("apps.fcdm.scripts.forest_mask.ee")
    def test_custom_asset_path(self, mock_ee):
        from apps.fcdm.scripts.forest_mask import get_forest_mask

        aoi = MagicMock()
        asset_id = "users/me/custom_forest"
        get_forest_mask(asset_id, year=2020, treecover=0, aoi=aoi)
        # The custom asset path calls ee.Image twice: once for hansen, once for asset.
        assert mock_ee.Image.call_count >= 2


class TestNbrPipeline:
    @patch("apps.fcdm.scripts.nbr_pipeline.ee")
    def test_compute_nbr_returns_image(self, mock_ee):
        from apps.fcdm.scripts.nbr_pipeline import compute_nbr

        image = MagicMock()
        result = compute_nbr(image, sensor="landsat 8")
        assert result is not None

    @patch("apps.fcdm.scripts.nbr_pipeline.ee")
    def test_ddr_filter_returns_image(self, mock_ee):
        from apps.fcdm.scripts.nbr_pipeline import ddr_filter

        nbr_diff = MagicMock()
        result = ddr_filter(nbr_diff, threshold=0.035, radius=80, nb_disturbances=3)
        assert result is not None

    def test_run_fcdm_requires_sensors(self):
        from apps.fcdm.scripts.nbr_pipeline import run_fcdm

        with pytest.raises(ValueError):
            run_fcdm(
                aoi=MagicMock(),
                sensors=[],
                reference_start="2015-01-01",
                reference_end="2015-12-31",
                analysis_start="2020-01-01",
                analysis_end="2020-12-31",
                forest_map="gfc",
                forest_map_year=2020,
                treecover=70,
                cloud_buffer=500,
                kernel_radius=150,
                filter_threshold=0.035,
                filter_radius=80,
                cleaning_offset=3,
            )


class TestCloudMaskers:
    def test_registry_has_all_sensors(self):
        from apps.fcdm.params import SENSORS
        from apps.fcdm.scripts.cloud_masking import CLOUD_MASKERS

        assert set(CLOUD_MASKERS) == set(SENSORS)

    @patch(
        "apps.fcdm.scripts.cloud_masking.SENSORS",
        {
            "landsat 8": {
                "bands": {
                    "blue": "SR_B2",
                    "green": "SR_B3",
                    "red": "SR_B4",
                    "nir": "SR_B5",
                    "swir1": "SR_B6",
                    "swir2": "SR_B7",
                    "pixel_qa": "QA_PIXEL",
                    "cloud": "cloud",
                    "bright_temp1": "ST_B10",
                }
            }
        },
    )
    def test_masking_landsat_returns_image(self):
        from apps.fcdm.scripts.cloud_masking import masking_landsat

        image = MagicMock()
        out = masking_landsat(image, cloud_buffer=500, sensor="landsat 8")
        assert out is not None


class TestCollection:
    @patch("apps.fcdm.scripts.collection.ee")
    def test_build_collection_landsat_joins_toa(self, mock_ee):
        from apps.fcdm.scripts.collection import build_collection

        aoi = MagicMock()
        forest_mask = MagicMock()
        out = build_collection(
            sensor="landsat 8",
            start="2020-01-01",
            end="2020-12-31",
            forest_map="gfc",
            year=2020,
            forest_mask=forest_mask,
            cloud_buffer=500,
            aoi=aoi,
        )
        assert out is not None
        # Joined via ee.Join.inner().apply(...)
        assert mock_ee.Join.inner.called

    @patch("apps.fcdm.scripts.collection.ee")
    def test_build_collection_sentinel_no_join(self, mock_ee):
        from apps.fcdm.scripts.collection import build_collection

        aoi = MagicMock()
        forest_mask = MagicMock()
        out = build_collection(
            sensor="sentinel 2",
            start="2020-01-01",
            end="2020-12-31",
            forest_map="gfc",
            year=2020,
            forest_mask=forest_mask,
            cloud_buffer=500,
            aoi=aoi,
        )
        assert out is not None
        assert not mock_ee.Join.inner.called
