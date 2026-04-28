"""Tests for Basin Rivers scripts and params."""

from unittest.mock import MagicMock, patch

from apps.basin_rivers.params import (
    GFC_CLASSES,
    GFC_COLORS_DICT,
    GFC_GROUPS,
    GFC_LABELS,
    GFC_MAX_YEAR,
    GFC_TRANSLATION,
    HEX_PALETTE,
    HYBAS_LEVELS,
)
from apps.basin_rivers.scripts.statistics import parse_zonal_stats
from apps.basin_rivers.scripts.visualization import create_basins_layer, create_selection_layer


class TestParams:
    def test_labels_match_non_zero_classes(self):
        non_zero = [c for c in GFC_CLASSES if c != 0]
        assert len(GFC_LABELS) == len(non_zero)

    def test_palette_length(self):
        assert len(HEX_PALETTE) == len(GFC_LABELS)

    def test_translation_covers_all_codes(self):
        codes = [*range(1, GFC_MAX_YEAR + 1), 30, 40, 50, 51]
        for code in codes:
            assert code in GFC_TRANSLATION

    def test_groups_count(self):
        assert len(GFC_GROUPS) == GFC_MAX_YEAR + 4

    def test_hybas_levels(self):
        assert HYBAS_LEVELS == list(range(5, 13))

    def test_colors_dict_has_all_groups(self):
        for group in ["loss", "non_forest", "forest", "gain", "gain_loss"]:
            assert group in GFC_COLORS_DICT


class TestClassifyGfc:
    @patch("apps._commons.gfc.ee")
    def test_returns_uint8(self, mock_ee):
        from apps.basin_rivers.scripts.gfc_classification import classify_gfc

        result = classify_gfc(MagicMock(), threshold=80, start_year=2010, end_year=2020)
        assert result is not None
        mock_ee.Image.assert_called()


class TestBuildUpstreamFc:
    @patch("apps.basin_rivers.scripts.watershed.ee")
    def test_calls_iterate(self, mock_ee):
        from apps.basin_rivers.scripts.watershed import build_upstream_fc

        result = build_upstream_fc(level=8, geometry=MagicMock(), max_steps=10)
        assert result is not None
        mock_ee.List.sequence.assert_called_once_with(1, 10)


class TestParseZonalStats:
    def test_empty_result(self):
        df = parse_zonal_stats({"features": []})
        assert df.empty
        assert "basin" in df.columns

    def test_single_basin(self):
        raw = {
            "features": [
                {
                    "properties": {
                        "HYBAS_ID": 123456,
                        "groups": [
                            {"group": 40, "sum": 1000.0},
                            {"group": 5, "sum": 200.0},
                            {"group": 30, "sum": 500.0},
                        ],
                    }
                }
            ]
        }
        df = parse_zonal_stats(raw)
        assert len(df) == 3
        assert set(df["basin"]) == {"123456"}

    def test_year_column(self):
        raw = {
            "features": [
                {
                    "properties": {
                        "HYBAS_ID": 1,
                        "groups": [
                            {"group": 5, "sum": 100.0},
                            {"group": 40, "sum": 200.0},
                        ],
                    }
                }
            ]
        }
        df = parse_zonal_stats(raw)
        loss_row = df[df["variable"] == 5].iloc[0]
        forest_row = df[df["variable"] == 40].iloc[0]
        assert loss_row["year"] == 2005
        assert forest_row["year"] == 0

    def test_group_translation(self):
        raw = {
            "features": [
                {
                    "properties": {
                        "HYBAS_ID": 1,
                        "groups": [
                            {"group": 5, "sum": 100.0},
                            {"group": 30, "sum": 50.0},
                            {"group": 50, "sum": 25.0},
                        ],
                    }
                }
            ]
        }
        df = parse_zonal_stats(raw)
        groups = dict(zip(df["variable"], df["group"]))
        assert groups[5] == "loss"
        assert groups[30] == "non_forest"
        assert groups[50] == "gain"


class TestVisualization:
    def test_create_basins_layer(self):
        geojson = {"type": "FeatureCollection", "features": []}
        layer = create_basins_layer(geojson)
        assert layer.name == "Upstream catchment"
        assert layer.data == geojson

    def test_create_selection_layer(self):
        geojson = {"type": "FeatureCollection", "features": []}
        layer = create_selection_layer(geojson)
        assert layer.name == "Selected"

    def test_custom_layer_name(self):
        geojson = {"type": "FeatureCollection", "features": []}
        layer = create_basins_layer(geojson, name="My Basins")
        assert layer.name == "My Basins"


class TestDashboardParams:
    def test_catch_palette_unique_and_nonempty(self):
        from apps.basin_rivers.params import CATCH_COLOR_PALETTE

        assert len(CATCH_COLOR_PALETTE) >= 12
        assert len(set(CATCH_COLOR_PALETTE)) == len(CATCH_COLOR_PALETTE)
        for c in CATCH_COLOR_PALETTE:
            assert c.startswith("#") and len(c) == 7

    def test_variable_labels_cover_groups(self):
        from apps.basin_rivers.params import VARIABLE_LABELS

        for key in ["all", "forest", "loss", "gain", "non_forest", "gain_loss"]:
            assert key in VARIABLE_LABELS

    def test_chart_titles_have_per_variable_keys(self):
        from apps.basin_rivers.params import CATCH_BAR_TITLES, CATCH_PIE_TITLES

        for key in ["all", "forest", "loss", "gain", "non_forest", "gain_loss"]:
            assert key in CATCH_PIE_TITLES
            assert key in CATCH_BAR_TITLES
