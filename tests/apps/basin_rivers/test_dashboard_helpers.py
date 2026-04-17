"""Tests for Basin Rivers dashboard dataframe helpers."""

import pandas as pd
import pytest

from apps.basin_rivers.scripts.statistics import add_catchment_colors


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
