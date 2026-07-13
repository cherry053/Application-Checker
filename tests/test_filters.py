from core.filters import (
    criterion_status,
    filter_criteria,
    section_status,
    status_counts,
)
from core.models import CriterionResult


def make_criterion(name: str, passed: bool, severity: str, section: str, detail: str = "") -> CriterionResult:
    return CriterionResult(name, passed, severity, detail, section)


CRITERIA = [
    make_criterion("Organisation Name Provided", True, "critical", "2. Eligible Delivery Agency Details"),
    make_criterion("Email Address Valid", True, "critical", "2. Eligible Delivery Agency Details"),
    make_criterion(
        "Start Date Before End Date", False, "critical", "3. EPAR Project Details",
        "Start date 2026-09-01 is after end date 2026-06-30.",
    ),
    make_criterion(
        "D001 - Evidence File Naming Convention", False, "warning", "4. Damage Information",
        "'photo.png' does not start with 'D001_'.",
    ),
]

ALL_STATUSES = {"Pass", "Fail", "Review"}


def test_criterion_status_mapping():
    assert criterion_status(make_criterion("a", True, "critical", "s")) == "Pass"
    assert criterion_status(make_criterion("a", True, "warning", "s")) == "Pass"
    assert criterion_status(make_criterion("a", False, "warning", "s")) == "Review"
    assert criterion_status(make_criterion("a", False, "critical", "s")) == "Fail"


def test_section_status_is_worst_criterion_status():
    passing = [make_criterion("a", True, "critical", "s")]
    reviewing = passing + [make_criterion("b", False, "warning", "s")]
    failing = reviewing + [make_criterion("c", False, "critical", "s")]
    assert section_status(passing) == "Pass"
    assert section_status(reviewing) == "Review"
    assert section_status(failing) == "Fail"


def test_all_statuses_and_empty_search_returns_everything():
    assert filter_criteria(CRITERIA, ALL_STATUSES, "") == CRITERIA


def test_filters_by_status():
    result = filter_criteria(CRITERIA, {"Pass"}, "")
    assert [c.name for c in result] == ["Organisation Name Provided", "Email Address Valid"]


def test_no_statuses_selected_returns_nothing():
    assert filter_criteria(CRITERIA, set(), "") == []


def test_search_matches_criterion_name_case_insensitively():
    result = filter_criteria(CRITERIA, ALL_STATUSES, "email")
    assert [c.name for c in result] == ["Email Address Valid"]


def test_search_matches_section():
    result = filter_criteria(CRITERIA, ALL_STATUSES, "damage information")
    assert [c.name for c in result] == ["D001 - Evidence File Naming Convention"]


def test_search_matches_detail_text():
    result = filter_criteria(CRITERIA, ALL_STATUSES, "photo.png")
    assert [c.name for c in result] == ["D001 - Evidence File Naming Convention"]


def test_search_and_status_combine_with_and_logic():
    assert filter_criteria(CRITERIA, {"Fail"}, "date") == [CRITERIA[2]]
    assert filter_criteria(CRITERIA, {"Pass"}, "date") == []


def test_whitespace_only_search_matches_everything():
    assert filter_criteria(CRITERIA, ALL_STATUSES, "   ") == CRITERIA


def test_search_with_no_match_returns_nothing():
    assert filter_criteria(CRITERIA, ALL_STATUSES, "postcode") == []


def test_status_counts_include_every_status():
    assert status_counts(CRITERIA) == {"Pass": 2, "Review": 1, "Fail": 1}


def test_status_counts_on_empty_list_are_zero():
    assert status_counts([]) == {"Pass": 0, "Review": 0, "Fail": 0}
