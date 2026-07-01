"""Pure-Python tests for TMF params and viz-param helpers (no GEE)."""

import pytest

from apps.tmf_sepal.params import (
    TMF_CHG_TRANSITION_CLASSES,
    TMF_CHG_TRANSITION_REMAP,
    TMF_MAX_YEAR,
    TMF_MIN_YEAR,
    TMF_SUBTYPE_TO_MAIN,
    TMF_TRANSITION_MAIN_CLASSES,
    TMF_TYPES,
    TMF_VERSION_YEAR,
    TMF_YEAR_PALETTE,
    asset_basename,
    change_legend,
    change_viz_params,
    chg_dataset_id,
    def_dataset_id,
    deg_dataset_id,
    transition_main_legend,
    transition_main_viz_params,
    year_legend,
    year_viz_params,
)
from apps.tmf_sepal.scripts.tmf_process import VALID_TYPES, viz_params_for


class TestDatasetIds:
    def test_all_ids_embed_version_year(self):
        assert str(TMF_VERSION_YEAR) in deg_dataset_id()
        assert str(TMF_VERSION_YEAR) in def_dataset_id()
        assert str(TMF_VERSION_YEAR) in chg_dataset_id()

    def test_id_prefixes(self):
        for fn in (deg_dataset_id, def_dataset_id, chg_dataset_id):
            assert fn().startswith("projects/JRC/TMF/")


class TestYearBounds:
    def test_min_max_sane(self):
        assert TMF_MIN_YEAR == 1990
        assert TMF_MAX_YEAR == TMF_VERSION_YEAR
        assert TMF_MAX_YEAR >= TMF_MIN_YEAR


class TestTmfTypes:
    def test_types_match_valid(self):
        values = {t["value"] for t in TMF_TYPES}
        assert values == set(VALID_TYPES)

    def test_every_type_has_label_and_icon(self):
        for t in TMF_TYPES:
            assert t["label"]
            assert t["icon"].startswith("mdi-")


class TestVizParams:
    def test_year_palette_is_three_colors(self):
        assert len(TMF_YEAR_PALETTE) == 3

    def test_year_viz_params(self):
        p = year_viz_params(2000, 2020)
        assert p["min"] == 2000
        assert p["max"] == 2020
        assert p["palette"] == TMF_YEAR_PALETTE

    def test_change_viz_params_is_transition(self):
        p = change_viz_params()
        assert p["bands"] == ["transition"]
        assert p["min"] == 1
        assert p["max"] == len(TMF_CHG_TRANSITION_CLASSES)
        assert p["palette"] == [c for _code, _label, c in TMF_CHG_TRANSITION_CLASSES]

    def test_viz_params_for_dispatch(self):
        assert viz_params_for("DEG", 2000, 2020) == year_viz_params(2000, 2020)
        assert viz_params_for("DEF", 2000, 2020) == year_viz_params(2000, 2020)
        assert viz_params_for("CHG", 2000, 2020) == change_viz_params()
        assert viz_params_for("TRANS", 2000, 2020) == transition_main_viz_params()

    def test_viz_params_for_rejects_unknown(self):
        with pytest.raises(ValueError):
            viz_params_for("XXX", 2000, 2020)


class TestTransitionRemap:
    def test_codes_are_valid_1_to_7(self):
        valid = {code for code, _label, _color in TMF_CHG_TRANSITION_CLASSES}
        assert valid == set(range(1, 8))
        assert set(TMF_CHG_TRANSITION_REMAP.values()) <= valid

    def test_sample_transitions(self):
        r = TMF_CHG_TRANSITION_REMAP
        assert r[11] == 1  # undisturbed -> undisturbed: stable forest
        assert r[22] == 1  # stable degraded: stable forest
        assert r[12] == 2  # undisturbed -> degraded: new degradation
        assert r[13] == 3 and r[23] == 3  # forest -> deforested: new deforestation
        assert r[33] == 4  # stable deforested
        assert r[34] == 5  # deforested -> regrowth
        assert r[55] == 6  # water
        assert 16 not in r  # undisturbed -> other falls through to "Other change"


class TestTransitionMap:
    def test_viz_params(self):
        p = transition_main_viz_params()
        assert p["bands"] == ["transition_main"]
        assert p["min"] == 1
        assert p["max"] == len(TMF_TRANSITION_MAIN_CLASSES)
        assert p["palette"] == [c for _code, _label, c in TMF_TRANSITION_MAIN_CLASSES]

    def test_legend_matches_classes(self):
        leg = transition_main_legend()
        assert len(leg.items) == len(TMF_TRANSITION_MAIN_CLASSES)
        for item, (_code, label, color) in zip(leg.items, TMF_TRANSITION_MAIN_CLASSES):
            assert item.label == label
            assert item.color == color

    def test_subtype_remap_targets_are_1_to_9(self):
        valid = {code for code, _label, _color in TMF_TRANSITION_MAIN_CLASSES}
        assert valid == set(range(1, 10))
        assert set(TMF_SUBTYPE_TO_MAIN.values()) == valid

    def test_sample_subtype_recode(self):
        m = TMF_SUBTYPE_TO_MAIN
        assert m[10] == 1 and m[26] == 2 and m[62] == 2  # forest classes
        assert m[81] == 4  # plantations
        assert m[51] == 7 and m[67] == 7  # recent 2022-2025
        assert m[91] == 9  # other land cover
        assert 13 not in m  # gap codes -> masked


class TestLegends:
    def test_year_legend_has_single_gradient(self):
        leg = year_legend("DEG", 2001, 2020)
        assert len(leg.gradients) == 1
        assert leg.gradients[0].colors == TMF_YEAR_PALETTE
        assert leg.items == []

    def test_year_legend_title_per_type(self):
        assert "Degradation" in year_legend("DEG", 2000, 2020).gradients[0].title
        assert "Deforestation" in year_legend("DEF", 2000, 2020).gradients[0].title

    def test_change_legend_items_match_transition_classes(self):
        leg = change_legend()
        assert len(leg.items) == len(TMF_CHG_TRANSITION_CLASSES)
        for item, (_code, label, color) in zip(leg.items, TMF_CHG_TRANSITION_CLASSES):
            assert item.label == label
            assert item.color == color


class TestAssetBasename:
    def test_basic(self):
        assert asset_basename("Uganda", "DEG", 2001, 2020) == "tmf_DEG_Uganda_2001_2020"

    def test_spaces_replaced(self):
        assert asset_basename("West Nile", "DEF", 2000, 2010) == "tmf_DEF_West_Nile_2000_2010"

    def test_none_name_defaults_to_aoi(self):
        assert asset_basename(None, "CHG", 1995, 2005) == "tmf_CHG_aoi_1995_2005"
