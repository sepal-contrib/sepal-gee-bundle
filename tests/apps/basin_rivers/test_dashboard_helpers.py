"""Tests for Basin Rivers dashboard dataframe helpers."""

import pandas as pd
import pytest

from apps.basin_rivers.scripts.statistics import (
    add_catchment_colors,
    get_catchment_pie_df,
    get_overall_pie_df,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "basin": ["1", "1", "2", "2", "3"],
            "variable": [1, 40, 1, 30, 40],
            "area": [10.0, 20.0, 15.0, 25.0, 5.0],
            "group": ["loss", "forest", "loss", "non_forest", "forest"],
            "year": [2001, 0, 2001, 0, 0],
            "color": ["#a", "#b", "#a", "#c", "#b"],
        }
    )


class TestAddCatchmentColors:
    def test_adds_catch_color_column(self, sample_df):
        out = add_catchment_colors(sample_df)
        assert "catch_color" in out.columns

    def test_same_basin_same_color(self, sample_df):
        out = add_catchment_colors(sample_df)
        colors_by_basin = out.groupby("basin")["catch_color"].nunique()
        assert (colors_by_basin == 1).all()

    def test_different_basins_different_colors(self, sample_df):
        out = add_catchment_colors(sample_df)
        unique_colors = out.drop_duplicates("basin")["catch_color"].nunique()
        assert unique_colors == 3

    def test_deterministic(self, sample_df):
        a = add_catchment_colors(sample_df)["catch_color"].tolist()
        b = add_catchment_colors(sample_df)["catch_color"].tolist()
        assert a == b

    def test_more_basins_than_palette_cycles(self):
        many = pd.DataFrame({"basin": [str(i) for i in range(30)], "area": [1.0] * 30})
        out = add_catchment_colors(many)
        assert out["catch_color"].notna().all()


class TestGetOverallPieDf:
    def test_groups_sum_area(self, sample_df):
        out = get_overall_pie_df(sample_df)
        expected_total = sample_df["area"].sum()
        assert out["area"].sum() == pytest.approx(expected_total)

    def test_one_row_per_group(self, sample_df):
        out = get_overall_pie_df(sample_df)
        assert out["group"].nunique() == len(out)

    def test_color_column_present(self, sample_df):
        out = get_overall_pie_df(sample_df)
        assert "color" in out.columns
        assert out["color"].notna().all()

    def test_empty_df_returns_empty(self):
        out = get_overall_pie_df(pd.DataFrame(columns=["basin", "group", "area"]))
        assert out.empty


class TestGetCatchmentPieDf:
    @pytest.fixture
    def colored_df(self, sample_df):
        return add_catchment_colors(sample_df)

    def test_all_sums_all_groups(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="all")
        assert set(out["basin"]) == {"1", "2", "3"}
        assert out.loc[out.basin == "1", "area"].iloc[0] == 30.0

    def test_specific_class_filters(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="forest")
        assert set(out["basin"]) == {"1", "3"}
        assert out.loc[out.basin == "1", "area"].iloc[0] == 20.0

    def test_carries_catch_color(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="all")
        assert "catch_color" in out.columns
        assert out["catch_color"].notna().all()

    def test_unknown_var_returns_empty(self, colored_df):
        out = get_catchment_pie_df(colored_df, selected_var="nope")
        assert out.empty
