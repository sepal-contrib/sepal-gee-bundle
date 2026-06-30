"""Pure-Python tests for parse_area_stats (no GEE)."""

from apps.tmf_sepal.params import TMF_CHG_TRANSITION_CLASSES
from apps.tmf_sepal.scripts.statistics import parse_area_stats


def _raw(groups):
    return {"groups": groups}


class TestParseAreaStatsChg:
    def test_known_codes_get_labels_and_colors(self):
        raw = _raw(
            [
                {"group": 1, "sum": 123.456},
                {"group": 3, "sum": 10.0},
            ]
        )
        rows = parse_area_stats(raw, "CHG")
        assert len(rows) == 2

        by_code = {r["code"]: r for r in rows}
        expected = {c: (lbl, col) for c, lbl, col in TMF_CHG_TRANSITION_CLASSES}
        assert by_code[1]["label"] == expected[1][0]
        assert by_code[1]["color"] == expected[1][1]
        assert by_code[1]["area_ha"] == 123.46
        assert by_code[3]["label"] == expected[3][0]

    def test_unknown_chg_code_passes_through(self):
        rows = parse_area_stats(_raw([{"group": 99, "sum": 42.0}]), "CHG")
        assert rows == [{"code": 99, "label": "unknown (99)", "color": None, "area_ha": 42.0}]

    def test_drops_zero_and_negative_area(self):
        raw = _raw(
            [
                {"group": 1, "sum": 0.0},
                {"group": 2, "sum": -1.0},
                {"group": 3, "sum": 5.0},
            ]
        )
        rows = parse_area_stats(raw, "CHG")
        assert [r["code"] for r in rows] == [3]

    def test_sorted_by_code(self):
        raw = _raw(
            [
                {"group": 3, "sum": 10.0},
                {"group": 1, "sum": 20.0},
                {"group": 2, "sum": 30.0},
            ]
        )
        rows = parse_area_stats(raw, "CHG")
        assert [r["code"] for r in rows] == [1, 2, 3]


class TestParseAreaStatsYear:
    def test_year_codes_become_labels(self):
        raw = _raw(
            [
                {"group": 2005, "sum": 100.0},
                {"group": 2010, "sum": 200.0},
            ]
        )
        rows = parse_area_stats(raw, "DEG")
        assert rows[0] == {
            "code": 2005,
            "label": "2005",
            "color": None,
            "area_ha": 100.0,
        }
        assert rows[1]["label"] == "2010"

    def test_def_and_deg_have_same_shape(self):
        raw = _raw([{"group": 2001, "sum": 1.5}])
        assert parse_area_stats(raw, "DEF") == parse_area_stats(raw, "DEG")


class TestParseAreaStatsEdges:
    def test_empty_groups(self):
        assert parse_area_stats({}, "CHG") == []
        assert parse_area_stats({"groups": []}, "DEG") == []
        assert parse_area_stats({"groups": None}, "CHG") == []

    def test_skips_bad_group_values(self):
        raw = _raw(
            [
                {"group": None, "sum": 1.0},
                {"group": "bad", "sum": 1.0},
                {"group": 1, "sum": 2.0},
            ]
        )
        rows = parse_area_stats(raw, "CHG")
        assert [r["code"] for r in rows] == [1]
