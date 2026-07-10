from decimal import Decimal
from pathlib import Path

import pytest

from core.completeness import EXPECTED_COLUMNS, assess_completeness
from core.damage_table_parser import count_table_records, parse_damage_table
from core.models import DamageItem

FIXTURE = Path(__file__).parent / "fixtures" / "damage_table.txt"


def full_item(item_id: str = "D001") -> DamageItem:
    """A damage item with every tracked column populated."""
    return DamageItem(
        asset_category="Public Infrastructure",
        damage_item_id=item_id,
        asset_id=f"MCC-RD-{item_id}",
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
        pre_disaster_evidence_file=f"{item_id}_PredisasterEvidence.png",
        damage_evidence_file=f"{item_id}_DamageEvidence.png",
        damage_description="Extensive pavement failure.",
        estimation_method="Cost Estimation - Standard Tool",
        cost_construction=Decimal("100"),
        cost_pm_design=Decimal("10"),
        cost_contingency=Decimal("10"),
        cost_escalation=Decimal("5"),
        cost_total=Decimal("125"),
        cost_evidence_file="Cost Estimation Evidence.xlsx",
        methodology="Cost estimation Tool",
    )


def table_text(records: int) -> str:
    """A minimal pasted-table text containing `records` recognisable records."""
    lines: list[str] = []
    for n in range(1, records + 1):
        lines.append("Public Infrastructure")
        lines.append(f"D{n:03d}")
    return "\n".join(lines)


def test_count_table_records_on_fixture():
    assert count_table_records(FIXTURE.read_text()) == 7


def test_fully_extracted_table_is_complete():
    items = [full_item("D001"), full_item("D002")]
    report = assess_completeness(table_text(2), items, declared_count=2, table_warnings=[])
    assert report.status == "complete"
    assert report.score >= 98
    assert report.rows_detected == 2
    assert report.rows_extracted == 2
    assert report.rows_missing == 0
    assert report.empty_fields == 0
    assert report.columns_extracted == len(EXPECTED_COLUMNS)
    assert report.confidence >= 80
    assert not report.manual_review_recommended


def test_missing_row_is_never_complete():
    report = assess_completeness(table_text(3), [full_item("D001"), full_item("D002")], 3, [])
    assert report.rows_missing == 1
    assert report.status != "complete"
    assert any("3" in issue.message for issue in report.issues)


def test_declared_count_mismatch_flags_review():
    items = [full_item("D001"), full_item("D002")]
    report = assess_completeness(table_text(2), items, declared_count=4, table_warnings=[])
    assert report.status != "complete"
    assert report.rows_missing == 2
    assert any("declares 4" in issue.message for issue in report.issues)


def test_blank_fields_are_counted():
    item = full_item("D001")
    item.damage_description = None
    item.methodology = ""
    report = assess_completeness(table_text(1), [item], 1, [])
    assert report.empty_fields == 2
    assert any("2 field(s) empty" in issue.message for issue in report.issues)


def test_duplicate_ids_are_detected():
    report = assess_completeness(table_text(2), [full_item("D001"), full_item("D001")], 2, [])
    assert report.duplicate_rows == 1
    assert any("appears 2 times" in issue.message for issue in report.issues)
    assert report.status != "complete"


def test_truncated_and_mangled_text_is_flagged():
    item = full_item("D001")
    item.damage_description = "Extensive pavement fail..."
    item.asset_name = "Bucketts � Way"
    report = assess_completeness(table_text(1), [item], 1, [])
    assert report.quality_issues == 2
    messages = " ".join(issue.message for issue in report.issues)
    assert "truncated" in messages
    assert "undecodable" in messages


def test_column_that_never_extracts_is_critical():
    items = [full_item("D001"), full_item("D002")]
    for item in items:
        item.sub_category = None
    report = assess_completeness(table_text(2), items, 2, [])
    assert report.columns_extracted == len(EXPECTED_COLUMNS) - 1
    assert any(issue.severity == "critical" and "column" in issue.message for issue in report.issues)


def test_empty_table_text_is_incomplete():
    report = assess_completeness("", [], None, ["No damage item records found in the pasted table text."])
    assert report.status == "incomplete"
    assert report.score == 0
    assert report.rows_detected == 0
    assert report.manual_review_recommended


def test_unrecognised_table_lowers_confidence():
    report = assess_completeness("some pasted text that is not a table", [], None, [])
    assert report.confidence < 55
    assert report.confidence_label == "Low"
    assert report.status != "complete"


def test_export_limitation_warnings_do_not_penalise():
    warnings = [
        "D001: Asset Material selection cannot be determined from the text export.",
        "D001: Answer to 'same pre-disaster function' cannot be determined from the text export.",
    ]
    report = assess_completeness(table_text(1), [full_item("D001")], 1, warnings)
    assert report.status == "complete"
    assert any(issue.severity == "info" for issue in report.issues)


def test_real_parser_warnings_penalise_confidence():
    warnings = ["D001: Expected 5 cost amounts, found 3."]
    clean = assess_completeness(table_text(1), [full_item("D001")], 1, [])
    warned = assess_completeness(table_text(1), [full_item("D001")], 1, warnings)
    assert warned.confidence < clean.confidence
    assert warned.score < clean.score


def test_fixture_end_to_end():
    text = FIXTURE.read_text()
    items, warnings = parse_damage_table(text)
    report = assess_completeness(text, items, declared_count=7, table_warnings=warnings)
    assert report.rows_detected == 7
    assert report.rows_extracted == 7
    assert report.rows_missing == 0
    # The fixture has known gaps (D002 lacks locations/description), so the
    # verdict must not be "complete" but the score should stay high.
    assert report.status == "review"
    assert report.score >= 80
    assert report.empty_fields > 0


def test_issues_sorted_most_severe_first():
    item = full_item("D001")
    item.damage_description = None
    report = assess_completeness(table_text(3), [item], 3, [])
    severities = [issue.severity for issue in report.issues]
    assert severities == sorted(severities, key={"critical": 0, "warning": 1, "info": 2}.get)
