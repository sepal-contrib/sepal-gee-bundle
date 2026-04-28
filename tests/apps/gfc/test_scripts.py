"""Tests for GFC scripts and params."""

from unittest.mock import MagicMock, patch

from apps.gfc.params import GFC_CLASSES, GFC_LABELS, GFC_MAX_YEAR, HEX_PALETTE, LEGEND_DICT
from apps.gfc.scripts.statistics import parse_area_stats


class TestGfcParams:
    """Verify params consistency."""

    def test_labels_match_non_zero_classes(self):
        """Labels should match classes excluding code 0 (no data)."""
        non_zero_classes = [c for c in GFC_CLASSES if c != 0]
        assert len(GFC_LABELS) == len(non_zero_classes)

    def test_palette_matches_labels(self):
        assert len(HEX_PALETTE) == len(GFC_LABELS)

    def test_legend_dict_matches_labels(self):
        assert set(LEGEND_DICT.keys()) == set(GFC_LABELS)

    def test_max_year_consistent(self):
        loss_classes = [c for c in GFC_CLASSES if 1 <= c <= GFC_MAX_YEAR]
        assert len(loss_classes) == GFC_MAX_YEAR


class TestClassifyGfc:
    """Test GFC classification function."""

    @patch("apps._commons.gfc.ee")
    def test_returns_uint8_image(self, mock_ee):
        """classify_gfc should return a .uint8() image."""
        from apps.gfc.scripts.gfc_classification import classify_gfc

        mock_aoi = MagicMock()
        result = classify_gfc(mock_aoi, threshold=30, start_year=2001, end_year=2020)

        # The chain ends with .uint8()
        assert result is not None
        # Verify ee.Image was called with the dataset
        mock_ee.Image.assert_called()


class TestParseAreaStats:
    """Test statistics parsing."""

    def test_parse_empty_result(self):
        result = parse_area_stats({"groups": []})
        assert result == []

    def test_parse_grouped_result(self):
        raw = {
            "groups": [
                {"group": 40, "sum": 1000.5},
                {"group": 5, "sum": 200.3},
                {"group": 30, "sum": 500.0},
            ]
        }
        rows = parse_area_stats(raw)
        assert len(rows) == 3
        # Should be sorted by code
        assert rows[0]["code"] == 5
        assert rows[0]["label"] == "loss 2005"
        assert rows[1]["code"] == 30
        assert rows[1]["label"] == "non forest"
        assert rows[2]["code"] == 40
        assert rows[2]["label"] == "forest"

    def test_parse_unknown_code(self):
        raw = {"groups": [{"group": 99, "sum": 10.0}]}
        rows = parse_area_stats(raw)
        assert rows[0]["label"] == "unknown (99)"
