"""Tests for Basin Rivers scripts and params."""

from typing import ClassVar
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
from apps.basin_rivers.scripts.visualization import create_selection_layer


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
    def test_create_selection_layer(self):
        geojson = {"type": "FeatureCollection", "features": []}
        layer = create_selection_layer(geojson)
        assert layer.name == "Selected"


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


class TestBasinColorMap:
    def test_is_deterministic_regardless_of_input_order(self):
        from apps.basin_rivers.scripts.statistics import basin_color_map

        assert basin_color_map([3, 1, 2]) == basin_color_map([2, 3, 1])

    def test_keys_are_strings(self):
        from apps.basin_rivers.scripts.statistics import basin_color_map

        assert set(basin_color_map([10, 20])) == {"10", "20"}

    def test_cycles_the_palette_when_there_are_more_basins_than_colors(self):
        from apps.basin_rivers.params import CATCH_COLOR_PALETTE
        from apps.basin_rivers.scripts.statistics import basin_color_map

        ids = list(range(len(CATCH_COLOR_PALETTE) + 2))
        mapping = basin_color_map(ids)

        assert len(mapping) == len(ids)
        assert set(mapping.values()) <= set(CATCH_COLOR_PALETTE)

    def test_add_catchment_colors_uses_the_same_mapping(self):
        import pandas as pd

        from apps.basin_rivers.scripts.statistics import add_catchment_colors, basin_color_map

        df = pd.DataFrame({"basin": ["7", "8"], "area": [1.0, 2.0]})
        colored = add_catchment_colors(df)
        mapping = basin_color_map(["7", "8"])

        assert colored["catch_color"].tolist() == [mapping["7"], mapping["8"]]

    def test_add_catchment_colors_gives_a_nan_basin_row_a_nan_color(self):
        import pandas as pd

        from apps.basin_rivers.scripts.statistics import add_catchment_colors, basin_color_map

        # Pins current behavior for a basin column that still contains NaN (i.e. a
        # caller bypassing parse_zonal_stats, which always casts basin to str first).
        # basin_color_map keys its map with plain str(b), so str(float("nan")) == "nan"
        # becomes a real key. But add_catchment_colors looks values up through
        # df["basin"].astype(str), and pandas' astype(str) leaves NaN as float NaN
        # rather than the string "nan" -- so the lookup misses and that row silently
        # gets a NaN catch_color instead of matching the "nan" entry. Pre-refactor code
        # raised TypeError here instead (sorted() compared str to float); this is a
        # deliberate, recorded behavior change rather than a regression to guard.
        df = pd.DataFrame({"basin": [7, 8, float("nan")], "area": [1.0, 2.0, 3.0]})
        colored = add_catchment_colors(df)
        mapping = basin_color_map(df["basin"])

        assert colored["catch_color"].iloc[0] == mapping["7.0"]
        assert colored["catch_color"].iloc[1] == mapping["8.0"]
        assert pd.isna(colored["catch_color"].iloc[2])


class TestBasinTileStyle:
    META: ClassVar[dict] = {"vector_layers": [{"id": "basins", "minzoom": 0, "maxzoom": 14}]}
    URL = "/vectortiles/pmtiles?filePath=/tmp/basins.pmtiles"

    def _layers(self, ids):
        from apps.basin_rivers.scripts.visualization import basin_tile_style

        return basin_tile_style(ids)(self.META, self.URL)["layers"]

    def _color_by_id(self, ids):
        """Map each basin id to the color the emitted layers paint it.

        Reads the filters rather than a paint expression: protomaps-leaflet
        evaluates filters but not data-driven paint, so the selection has to
        live where the renderer will actually look.
        """
        found = {}
        for layer in self._layers(ids):
            if layer["type"] != "fill":
                continue
            selector = layer.get("filter")
            assert selector is None or selector[:2] == ["in", "HYBAS_ID"]
            for value in [] if selector is None else selector[2:]:
                found[value] = layer["paint"]["fill-color"]

        return found

    def test_selects_on_numeric_hybas_id(self):
        """The tiles carry HYBAS_ID as a Number; "123" would never match."""
        selected = self._color_by_id([1234502, 1234501])

        assert set(selected) == {1234501, 1234502}
        assert all(isinstance(value, int) for value in selected)

    def test_uses_no_paint_expression(self):
        """A ["match", ...] paint renders as one flat default color."""
        for layer in self._layers([1234501, 1234502]):
            for value in layer["paint"].values():
                assert not isinstance(value, list), f"expression in paint: {value}"

    def test_colors_agree_with_the_dashboard(self):
        from apps.basin_rivers.scripts.statistics import basin_color_map

        ids = [1234501, 1234502, 1234503]
        mapping = basin_color_map(ids)

        assert self._color_by_id(ids) == {i: mapping[str(i)] for i in ids}

    def test_colors_agree_with_the_dashboard_across_digit_lengths(self):
        # 9 and 100 sort differently as strings (basin_color_map's order) than
        # as ints, unlike same-digit-count ids above. This catches a positional
        # zip of basin_color_map(...).values() against numeric-sorted ids.
        from apps.basin_rivers.scripts.statistics import basin_color_map

        ids = [9, 100]
        mapping = basin_color_map(ids)

        assert self._color_by_id(ids) == {i: mapping[str(i)] for i in ids}

    def test_groups_basins_sharing_a_color_into_one_layer(self):
        """Layer count follows the palette, not the basin count."""
        from apps.basin_rivers.scripts.statistics import basin_color_map

        ids = list(range(1, 60))
        distinct = len(set(basin_color_map(ids).values()))

        assert len(self._layers(ids)) == 2 * distinct
        assert self._color_by_id(ids) == {i: basin_color_map(ids)[str(i)] for i in ids}

    def test_handles_an_empty_id_list(self):
        from apps.basin_rivers.scripts.visualization import BASIN_FALLBACK_COLOR

        layers = self._layers([])

        assert [layer["paint"]["fill-color"] for layer in layers if layer["type"] == "fill"] == [
            BASIN_FALLBACK_COLOR
        ]
        assert all("filter" not in layer for layer in layers)

    def test_normalizes_float_hybas_ids(self):
        # HYBAS_ID can arrive as a JSON double from Earth Engine. Both the
        # selector values and the color lookup must normalize the same way, or
        # str(float) vs str(int) keys mismatch and the lookup raises KeyError.
        from apps.basin_rivers.scripts.statistics import basin_color_map

        ids = [6120000010.0, 6120000020.0]
        mapping = basin_color_map([int(b) for b in ids])

        assert self._color_by_id(ids) == {int(b): mapping[str(int(b))] for b in ids}

    def test_consumes_a_one_shot_iterator_exactly_once(self):
        # Consuming hybas_ids twice leaves the second pass empty, which silently
        # produces the all-grey fallback instead of raising.
        from apps.basin_rivers.scripts.visualization import BASIN_FALLBACK_COLOR

        ids = [1234501, 1234502]
        selected = self._color_by_id(iter(ids))

        assert set(selected) == set(ids)
        assert BASIN_FALLBACK_COLOR not in selected.values()

    def test_line_shares_the_fill_color_and_selector(self):
        layers = self._layers([1234501, 1234502])
        fills = [layer for layer in layers if layer["type"] == "fill"]
        lines = [layer for layer in layers if layer["type"] == "line"]

        assert len(fills) == len(lines)
        for fill, line in zip(fills, lines):
            assert line["paint"]["line-color"] == fill["paint"]["fill-color"]
            assert line["filter"] == fill["filter"]

    def test_line_and_fill_paint_use_the_shared_constants(self):
        from apps.basin_rivers.scripts.visualization import (
            BASIN_FILL_OPACITY,
            BASIN_LINE_OPACITY,
            BASIN_LINE_WIDTH,
        )

        layers = self._layers([1234501])
        fill = next(layer for layer in layers if layer["type"] == "fill")
        line = next(layer for layer in layers if layer["type"] == "line")

        assert fill["paint"]["fill-opacity"] == BASIN_FILL_OPACITY
        assert line["paint"]["line-width"] == BASIN_LINE_WIDTH
        assert line["paint"]["line-opacity"] == BASIN_LINE_OPACITY

    def test_emits_no_circle_layer(self):
        assert all(layer["type"] != "circle" for layer in self._layers([1234501]))
