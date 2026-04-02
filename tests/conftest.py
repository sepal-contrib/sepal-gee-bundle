"""Shared test fixtures for sepal-gee-bundle."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_gee_interface():
    """Mock GEEInterface with common methods stubbed."""
    gee = MagicMock()
    gee.get_info = MagicMock(return_value={})
    gee.get_info_async = MagicMock()
    gee.get_map_id_async = MagicMock()
    gee.export_image_to_asset_async = MagicMock()
    gee.export_image_to_drive_async = MagicMock()
    gee.is_running_async = MagicMock(return_value=False)
    return gee


@pytest.fixture
def mock_aoi_fc():
    """Mock ee.FeatureCollection for AOI."""
    fc = MagicMock()
    fc.geometry.return_value = MagicMock()
    return fc
