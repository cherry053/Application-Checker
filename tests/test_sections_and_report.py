from decimal import Decimal
from pathlib import Path

import pytest

from core.damage_table_parser import parse_damage_table
from core.models import ApplicationData
from core.report_pdf import build_feedback_pdf
from core.sections import FORM_SECTIONS, group_by_section, section_passed_counts
from core.validators import run_checks

FIXTURE = Path(__file__).parent / "fixtures" / "damage_table.txt"


@pytest.fixture(scope="module")
def result():
    data = ApplicationData(
        eligibility_confirmed=True,
        organisation_name="MidCoast Council",
        primary_address="57 King Valley Dr Taree NSW 2430 Australia",
        postal_address="57 King Valley Dr Taree NSW 2430 Australia",
        primary_phone="0451 403 825",
        email_address="someone@council.nsw.gov.au",
        primary_contact="Ms Example",
        primary_contact_position="Board Member",
        primary_contact_phone="0451 403 825",
        primary_contact_email="someone@council.nsw.gov.au",
        has_abn="Yes",
        abn="44 961 208 161",
        insurance_answer="Yes",
        insurance_evidence_file="Public Liability Insurance.pdf",
        title="Flood Recovery Program",
        brief_description="Reconstruction of flood-damaged roads.",
        start_date="01/11/2026",
        end_date="31/12/2027",
        primary_initiative_location="Taree NSW 2430 Australia",
        predominant_lga="Mid-Coast",
        state_electorate="Myall Lakes",
        federal_electorate="Division of Lyne",
        predominant_asset_type="Local road/s",
        re_damaged_answer="No",
        declared_item_count=7,
        total_amount_requested=Decimal("20890000.00"),
        insurance_compensation_answer="No",
        declaration_agreed=True,
        authoriser_name="John Citizen",
        authoriser_position="General Manager",
        authoriser_phone="0298765432",
        authoriser_email="john@council.nsw.gov.au",
    )
    items, warnings = parse_damage_table(FIXTURE.read_text())
    checked = run_checks(data, items, warnings)
    checked.application_id = "UTS00018-TEST"
    checked.applicant_name = "MidCoast Council"
    checked.scanned_at = "07 Jul 2026, 10:00 AM"
    checked.total_requested = data.total_amount_requested
    return checked


def test_every_criterion_has_a_known_section(result):
    assert all(criterion.section in FORM_SECTIONS for criterion in result.criteria)


def test_grouping_covers_all_six_sections_in_order(result):
    groups = group_by_section(result.criteria)
    assert list(groups) == list(FORM_SECTIONS)


def test_grouping_preserves_every_criterion(result):
    groups = group_by_section(result.criteria)
    assert sum(len(checks) for checks in groups.values()) == len(result.criteria)


def test_section_passed_counts(result):
    groups = group_by_section(result.criteria)
    for checks in groups.values():
        passed, total = section_passed_counts(checks)
        assert 0 <= passed <= total == len(checks)


def test_feedback_pdf_builds(result):
    pdf = build_feedback_pdf(result)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 5_000


def test_feedback_pdf_handles_empty_result():
    empty = run_checks(ApplicationData())
    pdf = build_feedback_pdf(empty)
    assert pdf.startswith(b"%PDF")
