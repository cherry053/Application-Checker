from decimal import Decimal
from pathlib import Path

import pytest

from core.damage_table_parser import parse_damage_table

FIXTURE = Path(__file__).parent / "fixtures" / "damage_table.txt"


@pytest.fixture(scope="module")
def parsed():
    return parse_damage_table(FIXTURE.read_text())


@pytest.fixture(scope="module")
def items(parsed):
    return parsed[0]


def test_finds_all_seven_items(items):
    assert [item.damage_item_id for item in items] == ["D001", "D002", "D003", "D004", "D005", "D006", "D007"]


def test_d001_identity_and_date(items):
    d001 = items[0]
    assert d001.asset_category == "Public Infrastructure"
    assert d001.asset_id == "MCC-RD-001"
    assert d001.asset_name == "Bucketts Way"
    assert d001.date_accessible == "15/04/2026"


def test_d001_locations_and_coordinates(items):
    d001 = items[0]
    assert d001.location_start == "Bucketts Way, Tinonee, NSW, 2430, Australia"
    assert d001.location_end == "Bucketts Way, Tinonee, NSW, 2430, Australia"
    assert d001.chainage_focal == 1.20
    assert d001.chainage_from == 0.6
    assert d001.chainage_to == 1.8
    assert d001.longitude_from == 152.4050
    assert d001.latitude_from == -31.9030
    assert d001.longitude_to == 152.4160
    assert d001.latitude_to == -31.9090


def test_d001_asset_attributes(items):
    d001 = items[0]
    assert d001.sub_category.startswith("Local Roads:")
    assert d001.classification_type == "Other"
    assert d001.capacity == "Two traffic lanes"
    assert d001.layout == "Sealed road with drainage"
    assert d001.dimensions == "W8m × L1200m × D60mm"


def test_d001_evidence_and_costs(items):
    d001 = items[0]
    assert d001.pre_disaster_evidence_file == "D001_PredisasterEvidence.png"
    assert d001.pre_disaster_evidence_bytes == 2_400_000
    assert d001.damage_evidence_file == "D001_DamageEvidence.png"
    assert d001.damage_evidence_bytes == 3_000_000
    assert d001.damage_description == (
        "Extensive pavement failure, shoulder erosion and drainage damage caused by prolonged flooding."
    )
    assert d001.estimation_method == "Cost Estimation - Standard Tool"
    assert d001.cost_construction == Decimal("3600000.00")
    assert d001.cost_pm_design == Decimal("360000.00")
    assert d001.cost_contingency == Decimal("360000.00")
    assert d001.cost_escalation == Decimal("180000.00")
    assert d001.cost_total == Decimal("4500000.00")
    assert d001.cost_evidence_file == "Cost Estimation Evidence.xlsx"
    assert d001.cost_evidence_bytes == 327_700
    assert d001.methodology == "Cost estimation Tool"


def test_d002_missing_locations_and_description(items):
    d002 = items[1]
    assert d002.location_start is None
    assert d002.location_end is None
    assert d002.damage_description is None
    assert d002.chainage_focal == 0.15
    assert d002.chainage_from == 0
    assert d002.chainage_to == 0.3
    assert d002.cost_total == Decimal("3940000.00")


def test_d003_addresses_outside_nsw(items):
    d003 = items[2]
    assert "QLD" in d003.location_start
    assert "QLD" in d003.location_end


def test_d004_asset_attributes(items):
    d004 = items[3]
    assert d004.capacity == "1500mm stormwater pipe network"
    assert d004.layout == "Underground pipe network and drainage pits"
    assert d004.dimensions == "L800m × Ø1500mm"


def test_d005_and_d006_filenames_survive_verbatim(items):
    assert items[4].pre_disaster_evidence_file == "D005_PreDisasterEvidence .png"
    assert items[5].pre_disaster_evidence_file == "D006_PreDisasterEvidence copy.png"
    assert items[5].damage_evidence_file == "D006_DamageEvidence copy.png"


def test_d007_jpg_evidence(items):
    d007 = items[6]
    assert d007.pre_disaster_evidence_file == "D007_PreDisasterEvidence.jpg"
    assert d007.pre_disaster_evidence_bytes == 236_000


def test_item_totals_sum_to_package_total(items):
    total = sum(item.cost_total for item in items)
    assert total == Decimal("20890000.00")


def test_material_and_function_flagged_as_undeterminable(items):
    for item in items:
        assert item.material is None
        assert item.same_pre_disaster_function is None
        assert any("Asset Material" in warning for warning in item.parse_warnings)
        assert any("pre-disaster function" in warning for warning in item.parse_warnings)


def test_empty_text_returns_warning():
    items, warnings = parse_damage_table("")
    assert items == []
    assert warnings
