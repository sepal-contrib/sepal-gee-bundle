"""Single source of truth for GEE datasets shared by ≥2 apps in the bundle.

Each entry is a :class:`DatasetDescriptor` carrying the asset id (or pattern),
the probe strategy used by ``apps._commons.dataset_check``, the currently
pinned version, and a ``last_reviewed`` ISO date.

Apps import constants from this module instead of duplicating asset ids.
Per-app palettes, class codes, SLDs, and app-specific defaults stay in each
app's ``params.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Descriptor types
# ---------------------------------------------------------------------------

ProbeStrategy = str  # "version_pattern" | "year_in_collection" | "static"


@dataclass(frozen=True)
class DatasetDescriptor:
    """Declarative metadata for a single dataset / collection.

    ``asset_id`` is set for static collections.  ``pattern`` is set for
    versioned snapshots (Hansen, JRC TMF) and contains ``{name}`` placeholders
    that ``pinned`` fills in.
    """

    key: str
    probe: ProbeStrategy
    last_reviewed: str  # ISO date
    asset_id: str | None = None
    pattern: str | None = None
    pinned: dict[str, Any] = field(default_factory=dict)
    successor: str | None = None
    notes: str = ""

    def resolved_id(self, **overrides: Any) -> str:
        """Return the concrete asset id for the pinned (or overridden) values."""
        values = {**self.pinned, **overrides}
        if self.pattern is not None:
            return self.pattern.format(**values)
        if self.asset_id is None:
            raise ValueError(f"{self.key}: descriptor has neither asset_id nor pattern")
        return self.asset_id


# ---------------------------------------------------------------------------
# Hansen Global Forest Change
# ---------------------------------------------------------------------------

HANSEN_GFC = DatasetDescriptor(
    key="HANSEN_GFC",
    probe="version_pattern",
    last_reviewed="2026-05-14",
    pattern="UMD/hansen/global_forest_change_{year}_v1_{minor}",
    pinned={"year": 2025, "minor": 13},
    notes="Yearly snapshot. `lossyear` band stores year - 2000.",
)

HANSEN_GFC_ID: str = HANSEN_GFC.resolved_id()
HANSEN_GFC_LOSS_YEAR_BASE = 2000
HANSEN_GFC_MAX_LOSS_YEAR = HANSEN_GFC.pinned["year"]
HANSEN_GFC_MIN_LOSS_YEAR = HANSEN_GFC_LOSS_YEAR_BASE + 1
HANSEN_GFC_MAX_LOSS_OFFSET = HANSEN_GFC_MAX_LOSS_YEAR - HANSEN_GFC_LOSS_YEAR_BASE


# ---------------------------------------------------------------------------
# JRC Tropical Moist Forests
# ---------------------------------------------------------------------------

JRC_TMF = DatasetDescriptor(
    key="JRC_TMF",
    probe="version_pattern",
    last_reviewed="2026-04-27",
    pattern="projects/JRC/TMF/v1_{year}/{product}",
    pinned={"year": 2025},
    notes="`product` is one of DegradationYear / DeforestationYear / AnnualChanges.",
)


def jrc_tmf_id(product: str) -> str:
    """Return the concrete TMF asset id for the given product, using the pinned year."""
    return JRC_TMF.resolved_id(product=product)


JRC_TMF_VERSION_YEAR: int = JRC_TMF.pinned["year"]
JRC_TMF_DEGRADATION_ID = jrc_tmf_id("DegradationYear")
JRC_TMF_DEFORESTATION_ID = jrc_tmf_id("DeforestationYear")
JRC_TMF_ANNUAL_CHANGES_ID = jrc_tmf_id("AnnualChanges")


# ---------------------------------------------------------------------------
# Landsat Collection 2
# ---------------------------------------------------------------------------
# Each platform is a separate descriptor so the checker can flag them
# individually if Google retires one (it has happened before).  The shared
# C02 path template encodes the convention.
#
# Landsat 9 was added 2026-04-27 — operational since 2022, in C02 since
# 2022-01.  Bands match Landsat 8 (OLI/TIRS-2).

_C02_TOA_TEMPLATE = "LANDSAT/{code}/C02/T1_TOA"
_C02_SR_TEMPLATE = "LANDSAT/{code}/C02/T1_L2"

_LANDSAT_BANDS_OLD = {
    # L4 / L5 (TM), L7 (ETM+) share the same band ordering for our purposes.
    "blue": "SR_B1",
    "green": "SR_B2",
    "red": "SR_B3",
    "nir": "SR_B4",
    "swir1": "SR_B5",
    "swir2": "SR_B7",
    "pixel_qa": "QA_PIXEL",
    "thermal": "ST_B6",
}

_LANDSAT_BANDS_NEW = {
    # L8 / L9 (OLI / OLI-2 + TIRS / TIRS-2).
    "blue": "SR_B2",
    "green": "SR_B3",
    "red": "SR_B4",
    "nir": "SR_B5",
    "swir1": "SR_B6",
    "swir2": "SR_B7",
    "pixel_qa": "QA_PIXEL",
    "thermal": "ST_B10",
}


@dataclass(frozen=True)
class LandsatPlatform:
    """Metadata for a single Landsat platform within Collection 2."""

    code: str  # e.g. "LT04", "LC09"
    name: str  # e.g. "landsat 4"
    short: str  # e.g. "l4"
    start_year: int
    end_year: int | None  # None = still operational
    bands: dict[str, str]
    descriptor: DatasetDescriptor

    @property
    def toa(self) -> str:
        return _C02_TOA_TEMPLATE.format(code=self.code)

    @property
    def sr(self) -> str:
        return _C02_SR_TEMPLATE.format(code=self.code)


def _landsat_platform(
    code: str,
    name: str,
    short: str,
    start: int,
    end: int | None,
    bands: dict[str, str],
    *,
    successor: str | None = None,
) -> LandsatPlatform:
    descriptor = DatasetDescriptor(
        key=f"LANDSAT_{short.upper()}",
        probe="static",
        last_reviewed="2026-04-27",
        asset_id=_C02_SR_TEMPLATE.format(code=code),
        successor=successor,
        notes=f"Landsat {short[1:]} Collection 2 surface reflectance.",
    )
    return LandsatPlatform(
        code=code,
        name=name,
        short=short,
        start_year=start,
        end_year=end,
        bands=bands,
        descriptor=descriptor,
    )


LANDSAT_PLATFORMS: dict[str, LandsatPlatform] = {
    "l4": _landsat_platform("LT04", "landsat 4", "l4", 1982, 1993, _LANDSAT_BANDS_OLD),
    "l5": _landsat_platform("LT05", "landsat 5", "l5", 1984, 2013, _LANDSAT_BANDS_OLD),
    "l7": _landsat_platform("LE07", "landsat 7", "l7", 1999, None, _LANDSAT_BANDS_OLD),
    "l8": _landsat_platform(
        "LC08", "landsat 8", "l8", 2013, None, _LANDSAT_BANDS_NEW, successor="l9"
    ),
    "l9": _landsat_platform("LC09", "landsat 9", "l9", 2021, None, _LANDSAT_BANDS_NEW),
}


def landsat_c02_sr() -> dict[str, str]:
    """Return ``{short: SR asset id}`` for every Landsat platform."""
    return {short: p.sr for short, p in LANDSAT_PLATFORMS.items()}


def landsat_c02_toa() -> dict[str, str]:
    """Return ``{short: TOA asset id}`` for every Landsat platform."""
    return {short: p.toa for short, p in LANDSAT_PLATFORMS.items()}


# ---------------------------------------------------------------------------
# Sentinel-2
# ---------------------------------------------------------------------------

SENTINEL_2_TOA = DatasetDescriptor(
    key="SENTINEL_2_TOA",
    probe="static",
    last_reviewed="2026-04-27",
    asset_id="COPERNICUS/S2_HARMONIZED",
)

SENTINEL_2_SR = DatasetDescriptor(
    key="SENTINEL_2_SR",
    probe="static",
    last_reviewed="2026-04-27",
    asset_id="COPERNICUS/S2_SR_HARMONIZED",
)

SENTINEL_2_CLOUD_PROBABILITY = DatasetDescriptor(
    key="SENTINEL_2_CLOUD_PROBABILITY",
    probe="static",
    last_reviewed="2026-04-27",
    asset_id="COPERNICUS/S2_CLOUD_PROBABILITY",
)

SENTINEL_2_TOA_ID = SENTINEL_2_TOA.asset_id
SENTINEL_2_SR_ID = SENTINEL_2_SR.asset_id
SENTINEL_2_CLOUD_PROBABILITY_ID = SENTINEL_2_CLOUD_PROBABILITY.asset_id


# ---------------------------------------------------------------------------
# JAXA ALOS PALSAR yearly mosaics
# ---------------------------------------------------------------------------
# `pinned.years` is the year set as of `last_reviewed`.  The checker probes
# the live collection for new years and flags drift; refresh this list when
# the report says NEWER_AVAILABLE.

ALOS_PALSAR_SAR = DatasetDescriptor(
    key="ALOS_PALSAR_SAR",
    probe="year_in_collection",
    last_reviewed="2026-04-27",
    asset_id="JAXA/ALOS/PALSAR/YEARLY/SAR",
    pinned={"years": [2007, 2008, 2009, 2010, 2015, 2016, 2017, 2018, 2019, 2020]},
)

ALOS_PALSAR_FNF = DatasetDescriptor(
    key="ALOS_PALSAR_FNF",
    probe="year_in_collection",
    last_reviewed="2026-04-27",
    asset_id="JAXA/ALOS/PALSAR/YEARLY/FNF",
    pinned={"years": [2007, 2008, 2009, 2010, 2015, 2016, 2017]},
    notes="Discontinued after 2017.",
)

ALOS_PALSAR_SAR_ID = ALOS_PALSAR_SAR.asset_id
ALOS_PALSAR_FNF_ID = ALOS_PALSAR_FNF.asset_id
ALOS_PALSAR_YEARS = list(ALOS_PALSAR_SAR.pinned["years"])
ALOS_PALSAR_FNF_LAST_YEAR = max(ALOS_PALSAR_FNF.pinned["years"])


# ---------------------------------------------------------------------------
# WWF HydroSHEDS basins
# ---------------------------------------------------------------------------

HYDROSHEDS_BASINS = DatasetDescriptor(
    key="HYDROSHEDS_BASINS",
    probe="static",
    last_reviewed="2026-04-27",
    asset_id="WWF/HydroSHEDS/v1/Basins/hybas_{level}",
    notes="`{level}` is filled at call time, levels 5..12 published.",
)

HYDROSHEDS_BASINS_TEMPLATE = HYDROSHEDS_BASINS.asset_id


# ---------------------------------------------------------------------------
# Registry index
# ---------------------------------------------------------------------------

REGISTRY: tuple[DatasetDescriptor, ...] = (
    HANSEN_GFC,
    JRC_TMF,
    *(p.descriptor for p in LANDSAT_PLATFORMS.values()),
    SENTINEL_2_TOA,
    SENTINEL_2_SR,
    SENTINEL_2_CLOUD_PROBABILITY,
    ALOS_PALSAR_SAR,
    ALOS_PALSAR_FNF,
    HYDROSHEDS_BASINS,
)


__all__ = [
    "ALOS_PALSAR_FNF",
    "ALOS_PALSAR_FNF_ID",
    "ALOS_PALSAR_FNF_LAST_YEAR",
    "ALOS_PALSAR_SAR",
    "ALOS_PALSAR_SAR_ID",
    "ALOS_PALSAR_YEARS",
    "HANSEN_GFC",
    "HANSEN_GFC_ID",
    "HANSEN_GFC_LOSS_YEAR_BASE",
    "HANSEN_GFC_MAX_LOSS_OFFSET",
    "HANSEN_GFC_MAX_LOSS_YEAR",
    "HANSEN_GFC_MIN_LOSS_YEAR",
    "HYDROSHEDS_BASINS",
    "HYDROSHEDS_BASINS_TEMPLATE",
    "JRC_TMF",
    "JRC_TMF_ANNUAL_CHANGES_ID",
    "JRC_TMF_DEFORESTATION_ID",
    "JRC_TMF_DEGRADATION_ID",
    "JRC_TMF_VERSION_YEAR",
    "LANDSAT_PLATFORMS",
    "REGISTRY",
    "SENTINEL_2_CLOUD_PROBABILITY",
    "SENTINEL_2_CLOUD_PROBABILITY_ID",
    "SENTINEL_2_SR",
    "SENTINEL_2_SR_ID",
    "SENTINEL_2_TOA",
    "SENTINEL_2_TOA_ID",
    "DatasetDescriptor",
    "LandsatPlatform",
    "jrc_tmf_id",
    "landsat_c02_sr",
    "landsat_c02_toa",
]
