"""Pure-Python tests for alos_mosaics params and naming helpers (no GEE)."""

from apps.alos_mosaics.params import (
    ALOS_FNF_COLLECTION,
    ALOS_SAR_COLLECTION,
    ALOS_YEARS,
    FNF_CLASSES,
    LAST_FNF_YEAR,
    SPECKLE_FILTERS,
    SPECKLE_NONE,
    SPECKLE_QUEGAN,
    SPECKLE_REFINED_LEE,
    VIS_PARAM_DB,
    VIS_PARAM_FNF,
    VIS_PARAM_POW,
    VIS_PARAM_RFDI,
    VIZ_FNF,
    VIZ_LAYERS,
    VIZ_RFDI,
    VIZ_RGB,
    asset_name,
    fnf_available,
    fnf_legend,
    rfdi_legend,
    rgb_legend,
)


class TestDatasetIds:
    def test_sar_collection(self):
        assert ALOS_SAR_COLLECTION == "JAXA/ALOS/PALSAR/YEARLY/SAR"

    def test_fnf_collection(self):
        assert ALOS_FNF_COLLECTION == "JAXA/ALOS/PALSAR/YEARLY/FNF"


class TestYears:
    def test_years_are_unique_sorted(self):
        assert len(ALOS_YEARS) == len(set(ALOS_YEARS))
        assert ALOS_YEARS == sorted(ALOS_YEARS)

    def test_last_fnf_year(self):
        assert LAST_FNF_YEAR == 2017

    def test_fnf_available(self):
        assert fnf_available(2007) is True
        assert fnf_available(2017) is True
        assert fnf_available(2018) is False
        assert fnf_available(2020) is False


class TestSpeckleFilters:
    def test_enum_values(self):
        assert SPECKLE_NONE == "NONE"
        assert SPECKLE_QUEGAN == "QUEGAN"
        assert SPECKLE_REFINED_LEE == "REFINED_LEE"

    def test_filter_items_match_enum(self):
        values = {f["value"] for f in SPECKLE_FILTERS}
        assert values == {SPECKLE_NONE, SPECKLE_QUEGAN, SPECKLE_REFINED_LEE}
        for f in SPECKLE_FILTERS:
            assert f["text"]


class TestVizLayers:
    def test_values(self):
        values = {v["value"] for v in VIZ_LAYERS}
        assert values == {VIZ_RGB, VIZ_RFDI, VIZ_FNF}

    def test_rgb_bands(self):
        assert VIS_PARAM_DB["bands"] == ["HH", "HV", "HHHV_ratio"]
        assert VIS_PARAM_POW["bands"] == ["HH", "HV", "HHHV_ratio"]

    def test_rfdi_palette(self):
        assert VIS_PARAM_RFDI["palette"] == ["#105e1e", "#fffa6c"]
        assert VIS_PARAM_RFDI["min"] == 0.25
        assert VIS_PARAM_RFDI["max"] == 1

    def test_fnf_palette(self):
        assert VIS_PARAM_FNF["min"] == 1
        assert VIS_PARAM_FNF["max"] == 3
        assert len(VIS_PARAM_FNF["palette"]) == 3


class TestLegends:
    def test_fnf_legend_has_three_entries(self):
        leg = fnf_legend()
        assert len(leg.items) == len(FNF_CLASSES) == 3

    def test_rfdi_legend_items(self):
        leg = rfdi_legend()
        assert len(leg.gradients) == 1
        assert len(leg.gradients[0].colors) == 2

    def test_rgb_legend_db_vs_power(self):
        assert "dB" in rgb_legend(db=True).gradients[0].title
        assert "power" in rgb_legend(db=False).gradients[0].title


class TestAssetName:
    def test_basic(self):
        assert asset_name("myAoi", 2020) == "alos_mosaic_myAoi_2020"

    def test_fnf(self):
        assert asset_name("myAoi", 2017, fnf=True) == "kc_fnf_myAoi_2017"

    def test_spaces_replaced(self):
        assert asset_name("my aoi", 2020) == "alos_mosaic_my_aoi_2020"

    def test_all_toggles(self):
        name = asset_name(
            "AOI",
            2020,
            speckle_filter=SPECKLE_REFINED_LEE,
            rfdi=True,
            ls_mask=True,
            db=True,
            texture=True,
            aux=True,
        )
        assert name == "alos_mosaic_AOI_2020_refined_lee_rfdi_masked_dB_texture_aux"

    def test_speckle_none_omits_suffix(self):
        assert "none" not in asset_name("A", 2020).lower()

    def test_none_aoi_name_defaults(self):
        assert asset_name(None, 2020).startswith("alos_mosaic_aoi_")
