"""Behavioural tests for the Results page, driven through Streamlit's AppTest.

These cover the interactive filter behaviour the pure-function tests in
test_filters.py cannot: widget/session-state wiring, the clear actions, the
match counter, and the zero-result empty state.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.models import ApplicationResult, CheckResult, CriterionResult

APP_PY = str(Path(__file__).parent.parent / "app.py")

FILTER_STATUS = "filter_status"
FILTER_SEARCH = "filter_search"


def sample_applications() -> list[ApplicationResult]:
    return [
        ApplicationResult("UTS00001", "Hawkesbury City Council", "Pass"),
        ApplicationResult("UTS00002", "Lismore City Council", "Fail"),
        ApplicationResult("UTS00003", "Ballina Shire Council", "Review"),
        ApplicationResult("UTS00004", "Hawkesbury Sports Club", "Fail"),
    ]


def run_page(applications: list[ApplicationResult] | None = None, **state) -> AppTest:
    """Load the Results page through the real app entrypoint.

    AppTest.from_file on a pages/*.py file directly leaves the multipage
    registry empty, so any st.page_link/st.switch_page call inside that page
    raises. Routing through app.py + switch_page (as Streamlit's own testing
    docs recommend) gives the page a real registry, matching production.
    """
    at = AppTest.from_file(APP_PY, default_timeout=15)
    at.switch_page("pages/1_Results.py")
    at.session_state["processed_applications"] = applications if applications is not None else sample_applications()
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def visible_count_text(at: AppTest) -> str:
    for block in at.markdown:
        if "Showing" in block.value:
            return block.value
    raise AssertionError("match counter not rendered")


def test_page_runs_without_exceptions():
    at = run_page()
    assert not at.exception


def test_all_applications_shown_by_default():
    at = run_page()
    assert "<strong>4</strong>" in visible_count_text(at)


def test_status_filter_narrows_results():
    at = run_page()
    at.multiselect[0].set_value(["Fail"]).run()
    assert "<strong>2</strong>" in visible_count_text(at)
    assert at.session_state[FILTER_STATUS] == ["Fail"]


def test_search_and_status_combine():
    at = run_page()
    at.multiselect[0].set_value(["Fail"]).run()
    at.text_input[0].set_value("hawkesbury").run()
    assert "<strong>1</strong>" in visible_count_text(at)


def test_filters_survive_widget_state_loss():
    """Navigating to another page discards widget keys; stored filters must not reset.

    Running the page with the stored filter keys present but no widget keys is
    exactly the state Streamlit leaves behind after visiting the upload page:
    widget-bound state was garbage-collected, only our own keys survive.
    """
    at = run_page(**{FILTER_STATUS: ["Fail"], FILTER_SEARCH: "council"})
    assert at.session_state[FILTER_STATUS] == ["Fail"]
    assert at.multiselect[0].value == ["Fail"]
    assert at.text_input[0].value == "council"
    assert "<strong>1</strong>" in visible_count_text(at)


def test_clear_search_button_clears_only_search():
    at = run_page(**{FILTER_SEARCH: "hawkesbury", FILTER_STATUS: ["Fail"]})
    clear_search = next(b for b in at.button if b.label == "Clear search")
    clear_search.click().run()
    assert at.session_state[FILTER_SEARCH] == ""
    assert at.session_state[FILTER_STATUS] == ["Fail"]


def test_clear_all_filters_restores_defaults():
    at = run_page(**{FILTER_SEARCH: "hawkesbury", FILTER_STATUS: ["Fail"]})
    clear_all = next(b for b in at.button if b.label == "Clear all filters")
    clear_all.click().run()
    assert at.session_state[FILTER_SEARCH] == ""
    assert set(at.session_state[FILTER_STATUS]) == {"Pass", "Fail", "Review"}
    assert "<strong>4</strong>" in visible_count_text(at)


def test_zero_results_shows_empty_state_and_recovery():
    at = run_page(**{FILTER_SEARCH: "wollongong"})
    assert "<strong>0</strong>" in visible_count_text(at)
    body = " ".join(block.value for block in at.markdown)
    assert "No applications match the current filters" in body
    assert any(b.label == "Clear all filters" for b in at.button)


def test_empty_list_shows_onboarding_empty_state():
    at = run_page(applications=[])
    assert not at.exception
    body = " ".join(block.value for block in at.markdown)
    assert "No applications checked yet" in body


def test_detail_view_renders_flag_cards():
    check = CheckResult(
        overall_status="PARTIAL",
        confidence_score=60,
        criteria=[
            CriterionResult("Organisation Name Provided", True, "critical", "ok", "2. Agency"),
            CriterionResult(
                "Pre-disaster evidence presence", False, "critical",
                "No pre-disaster evidence attached for Damage Item 3.", "4. Damage Information",
            ),
            CriterionResult(
                "Contingency percentage", False, "warning",
                "Contingency 9.2% is below the recommended threshold.", "5. EPAR Funding Request",
            ),
        ],
        application_id="UTS00009",
        applicant_name="Test Council",
        scanned_at="15 Jun 2026, 11:42 AM",
    )
    application = ApplicationResult.from_check(check)
    at = run_page(applications=[application], check_result=check)
    assert not at.exception
    body = " ".join(block.value for block in at.markdown)
    assert "flag-card--fail" in body
    assert "flag-card--review" in body
    # The critical flag card must appear before the warning card (most severe first).
    assert body.index("flag-card--fail") < body.index("flag-card--review")
    # No completeness panel remains.
    assert "completeness-panel" not in body


def test_detail_view_with_no_flags_shows_success_note():
    check = CheckResult(
        overall_status="PASS",
        confidence_score=100,
        criteria=[CriterionResult("Organisation Name Provided", True, "critical", "ok", "2. Agency")],
        application_id="UTS00010",
        applicant_name="Clean Council",
        scanned_at="15 Jun 2026, 11:42 AM",
    )
    application = ApplicationResult.from_check(check)
    at = run_page(applications=[application], check_result=check)
    assert not at.exception
    body = " ".join(block.value for block in at.markdown)
    assert "flags-empty" in body
