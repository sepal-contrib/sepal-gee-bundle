"""Shape and integrity tests for the registry in ``apps._commons.datasets``."""

from __future__ import annotations

from datetime import date

import pytest

from apps._commons import datasets as ds

VALID_PROBES = {"version_pattern", "year_in_collection", "static"}


@pytest.mark.parametrize("descriptor", ds.REGISTRY, ids=lambda d: d.key)
def test_descriptor_has_required_fields(descriptor):
    assert descriptor.key
    assert descriptor.probe in VALID_PROBES
    # last_reviewed parses as ISO date.
    date.fromisoformat(descriptor.last_reviewed)
    assert descriptor.asset_id or descriptor.pattern


@pytest.mark.parametrize("descriptor", ds.REGISTRY, ids=lambda d: d.key)
def test_descriptor_pinned_matches_probe(descriptor):
    if descriptor.probe == "version_pattern":
        assert "year" in descriptor.pinned
        assert descriptor.pattern is not None
    elif descriptor.probe == "year_in_collection":
        assert "years" in descriptor.pinned
        assert descriptor.asset_id is not None
    elif descriptor.probe == "static":
        assert descriptor.asset_id is not None


def test_successor_links_resolve():
    keys = {p.short for p in ds.LANDSAT_PLATFORMS.values()}
    for p in ds.LANDSAT_PLATFORMS.values():
        if p.descriptor.successor:
            assert p.descriptor.successor in keys


def test_landsat_platforms_cover_4_5_7_8_9():
    assert set(ds.LANDSAT_PLATFORMS) == {"l4", "l5", "l7", "l8", "l9"}


def test_landsat_l9_is_present_and_matches_l8_bands():
    l8 = ds.LANDSAT_PLATFORMS["l8"]
    l9 = ds.LANDSAT_PLATFORMS["l9"]
    assert l9.bands == l8.bands
    assert l9.sr == "LANDSAT/LC09/C02/T1_L2"
    assert l9.toa == "LANDSAT/LC09/C02/T1_TOA"


def test_landsat_helpers_match_platforms():
    sr = ds.landsat_c02_sr()
    toa = ds.landsat_c02_toa()
    for short, p in ds.LANDSAT_PLATFORMS.items():
        assert sr[short] == p.sr
        assert toa[short] == p.toa


def test_hansen_resolved_id_matches_pinned():
    assert ds.HANSEN_GFC_ID == "UMD/hansen/global_forest_change_2025_v1_13"
    assert ds.HANSEN_GFC_MAX_LOSS_YEAR == 2025


def test_jrc_tmf_helpers():
    assert ds.JRC_TMF_VERSION_YEAR == 2025
    assert ds.JRC_TMF_DEGRADATION_ID == "projects/JRC/TMF/v1_2025/DegradationYear"
    assert ds.JRC_TMF_DEFORESTATION_ID == "projects/JRC/TMF/v1_2025/DeforestationYear"
    assert ds.JRC_TMF_ANNUAL_CHANGES_ID == "projects/JRC/TMF/v1_2025/AnnualChanges"
    assert ds.jrc_tmf_id("AnnualChanges") == ds.JRC_TMF_ANNUAL_CHANGES_ID


def test_alos_palsar_pinned_years():
    assert 2020 in ds.ALOS_PALSAR_YEARS
    assert ds.ALOS_PALSAR_FNF_LAST_YEAR == 2017


def test_hydrosheds_template_unfilled():
    assert "{level}" in ds.HYDROSHEDS_BASINS_TEMPLATE


def test_registry_keys_unique():
    keys = [d.key for d in ds.REGISTRY]
    assert len(keys) == len(set(keys))
