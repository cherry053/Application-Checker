from core.filters import filter_applications, status_counts, upsert_application
from core.models import ApplicationResult, CheckResult


def make_application(app_id: str, name: str, status: str) -> ApplicationResult:
    return ApplicationResult(application_id=app_id, applicant_name=name, status=status)


APPLICATIONS = [
    make_application("UTS00001", "Hawkesbury City Council", "Pass"),
    make_application("UTS00002", "Lismore City Council", "Fail"),
    make_application("UTS00003", "Ballina Shire Council", "Review"),
    make_application("UTS00004", "Hawkesbury Sports Club", "Fail"),
]

ALL_STATUSES = {"Pass", "Fail", "Review"}


def test_all_statuses_and_empty_search_returns_everything():
    assert filter_applications(APPLICATIONS, ALL_STATUSES, "") == APPLICATIONS


def test_filters_by_status():
    result = filter_applications(APPLICATIONS, {"Fail"}, "")
    assert [a.application_id for a in result] == ["UTS00002", "UTS00004"]


def test_no_statuses_selected_returns_nothing():
    assert filter_applications(APPLICATIONS, set(), "") == []


def test_search_matches_application_id():
    result = filter_applications(APPLICATIONS, ALL_STATUSES, "UTS00003")
    assert [a.application_id for a in result] == ["UTS00003"]


def test_search_matches_applicant_name_case_insensitively():
    result = filter_applications(APPLICATIONS, ALL_STATUSES, "hawkesbury")
    assert [a.application_id for a in result] == ["UTS00001", "UTS00004"]


def test_search_and_status_combine_with_and_logic():
    result = filter_applications(APPLICATIONS, {"Fail"}, "hawkesbury")
    assert [a.application_id for a in result] == ["UTS00004"]


def test_whitespace_only_search_matches_everything():
    assert filter_applications(APPLICATIONS, ALL_STATUSES, "   ") == APPLICATIONS


def test_search_with_no_match_returns_nothing():
    assert filter_applications(APPLICATIONS, ALL_STATUSES, "wollongong") == []


def test_status_counts_include_every_status():
    assert status_counts(APPLICATIONS) == {"Pass": 1, "Fail": 2, "Review": 1}


def test_status_counts_on_empty_list_are_zero():
    assert status_counts([]) == {"Pass": 0, "Fail": 0, "Review": 0}


def test_from_check_maps_overall_status():
    for overall, expected in [("PASS", "Pass"), ("FAIL", "Fail"), ("PARTIAL", "Review")]:
        check = CheckResult(
            overall_status=overall,
            confidence_score=80,
            application_id="UTS00009",
            applicant_name="Test Council",
            scanned_at="15 Jun 2026, 11:42 AM",
        )
        application = ApplicationResult.from_check(check)
        assert application.status == expected
        assert application.application_id == "UTS00009"
        assert application.applicant_name == "Test Council"
        assert application.check is check


def test_from_check_fills_missing_metadata():
    check = CheckResult(overall_status="PASS", confidence_score=50)
    application = ApplicationResult.from_check(check)
    assert application.application_id == "Unknown ID"
    assert application.applicant_name == "Unknown applicant"


def test_upsert_appends_new_application():
    applications = [make_application("UTS00001", "Hawkesbury City Council", "Pass")]
    upsert_application(applications, make_application("UTS00002", "Lismore City Council", "Fail"))
    assert [a.application_id for a in applications] == ["UTS00001", "UTS00002"]


def test_upsert_replaces_rechecked_application_in_place():
    applications = [
        make_application("UTS00001", "Hawkesbury City Council", "Fail"),
        make_application("UTS00002", "Lismore City Council", "Pass"),
    ]
    updated = make_application("UTS00001", "Hawkesbury City Council", "Pass")
    upsert_application(applications, updated)
    assert len(applications) == 2
    assert applications[0] is updated
    assert applications[0].status == "Pass"


def test_upsert_never_merges_unknown_ids():
    applications = [make_application("Unknown ID", "First unparsed upload", "Review")]
    upsert_application(applications, make_application("Unknown ID", "Second unparsed upload", "Fail"))
    assert len(applications) == 2
