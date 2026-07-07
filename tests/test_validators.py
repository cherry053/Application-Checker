from decimal import Decimal

from core.models import ApplicationData, DamageItem
from core.validators import (
    _expected_evidence_name,
    _is_australian_phone,
    _is_valid_email,
    cross_checks,
    damage_item_checks,
    run_checks,
)


def _complete_item(**overrides) -> DamageItem:
    values = dict(
        asset_category="Public Infrastructure",
        damage_item_id="D001",
        asset_id="MCC-RD-001",
        asset_name="Bucketts Way",
        date_accessible="15/04/2026",
        location_start="Bucketts Way, Tinonee, NSW, 2430, Australia",
        location_end="Bucketts Way, Tinonee, NSW, 2430, Australia",
        chainage_focal=1.2,
        chainage_from=0.6,
        chainage_to=1.8,
        longitude_from=152.405,
        latitude_from=-31.903,
        longitude_to=152.416,
        latitude_to=-31.909,
        sub_category="Local Roads",
        classification_type="Other",
        capacity="Two traffic lanes",
        layout="Sealed road with drainage",
        dimensions="W8m × L1200m × D60mm",
        pre_disaster_evidence_file="D001_PredisasterEvidence.png",
        pre_disaster_evidence_bytes=2_400_000,
        damage_evidence_file="D001_DamageEvidence.png",
        damage_evidence_bytes=3_000_000,
        damage_description="Extensive pavement failure.",
        estimation_method="Cost Estimation - Standard Tool",
        cost_construction=Decimal("3600000.00"),
        cost_pm_design=Decimal("360000.00"),
        cost_contingency=Decimal("360000.00"),
        cost_escalation=Decimal("180000.00"),
        cost_total=Decimal("4500000.00"),
        cost_evidence_file="Cost Estimation Evidence.xlsx",
        cost_evidence_bytes=327_700,
        methodology="Cost estimation Tool",
    )
    values.update(overrides)
    return DamageItem(**values)


def _by_name(checks, fragment):
    return next(check for check in checks if fragment in check.name)


def test_complete_item_passes_all_checks():
    checks = damage_item_checks(_complete_item(), 1)
    assert all(check.passed for check in checks), [c.name for c in checks if not c.passed]


def test_email_and_phone_helpers():
    assert _is_valid_email("someone@council.nsw.gov.au")
    assert not _is_valid_email("someone@council..nsw..")
    assert not _is_valid_email("no-at-sign.example")
    assert _is_australian_phone("0451 403 825")
    assert _is_australian_phone("+61 451 403 825")
    assert not _is_australian_phone("123")


def test_evidence_naming_convention():
    assert _expected_evidence_name("D001", "D001_PredisasterEvidence.png", "predisasterevidence") is None
    assert _expected_evidence_name("D007", "D007_PreDisasterEvidence.jpg", "predisasterevidence") is None
    assert _expected_evidence_name("D005", "D005_PreDisasterEvidence .png", "predisasterevidence") is not None
    assert _expected_evidence_name("D006", "D006_DamageEvidence copy.png", "damageevidence") is not None
    assert _expected_evidence_name("D002", "WrongId_DamageEvidence.png", "damageevidence") is not None


def test_missing_locations_fail_nsw_check():
    checks = damage_item_checks(_complete_item(location_start=None, location_end=None), 1)
    assert not _by_name(checks, "Damage Locations Within NSW").passed


def test_qld_location_fails_nsw_check():
    checks = damage_item_checks(
        _complete_item(location_start="1-9 Ingham Rd, West End, QLD, 4810, Australia"), 1
    )
    assert not _by_name(checks, "Damage Locations Within NSW").passed


def test_out_of_bounds_coordinate_fails():
    checks = damage_item_checks(_complete_item(latitude_from=-19.26866, longitude_from=146.80602), 1)
    assert not _by_name(checks, "Coordinates Within NSW Bounds").passed


def test_cost_mismatch_fails():
    checks = damage_item_checks(_complete_item(cost_total=Decimal("9999999.00")), 1)
    assert not _by_name(checks, "Cost Components Sum To Total").passed


def test_chainage_order_enforced():
    checks = damage_item_checks(_complete_item(chainage_from=2.0, chainage_to=1.0), 1)
    assert not _by_name(checks, "Chainage Range Valid").passed


def test_oversized_upload_flagged():
    checks = damage_item_checks(_complete_item(damage_evidence_bytes=150_000_000), 1)
    assert not _by_name(checks, "Upload Sizes Within 100MB").passed


def test_cross_checks_reconcile():
    data = ApplicationData(declared_item_count=2, total_amount_requested=Decimal("9000000.00"))
    items = [
        _complete_item(),
        _complete_item(damage_item_id="D002", cost_total=Decimal("4500000.00")),
    ]
    checks = cross_checks(data, items, [])
    assert _by_name(checks, "Damage Item Count Reconciles").passed
    assert _by_name(checks, "Total Amount Requested Reconciles").passed
    assert _by_name(checks, "Damage Item Limit").passed
    assert _by_name(checks, "Independent Technical Review Threshold").passed


def test_cross_checks_detect_mismatches():
    data = ApplicationData(declared_item_count=5, total_amount_requested=Decimal("26000000.00"))
    items = [_complete_item()]
    checks = cross_checks(data, items, ["something odd"])
    assert not _by_name(checks, "Damage Item Count Reconciles").passed
    assert not _by_name(checks, "Total Amount Requested Reconciles").passed
    assert not _by_name(checks, "Independent Technical Review Threshold").passed
    assert not _by_name(checks, "Damage Table Parsed Cleanly").passed


def test_unticked_declaration_and_unanswered_questions_fail():
    data = ApplicationData(declaration_agreed=False, insurance_compensation_answer=None)
    result = run_checks(data)
    failures = {check.name for check in result.criteria if not check.passed}
    assert "Declaration Agreed" in failures
    assert "Insurance Compensation Question Answered" in failures
    assert "Authoriser Name Provided" in failures
