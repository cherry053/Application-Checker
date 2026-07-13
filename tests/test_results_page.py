"""Behavioural tests for the Results page, driven through Streamlit's AppTest.

These cover the interactive filter behaviour the pure-function tests in
test_filters.py cannot: widget/session-state wiring, the clear actions, the
match counter, and the zero-result empty state.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.models import CheckResult, CriterionResult

APP_PY = str(Path(__file__).parent.parent / "app.py")

FILTER_STATUS = "filter_status"
FILTER_SEARCH = "filter_search"


def sample_check() -> CheckResult:
    """One checked application: two passes, one fail, one review."""
    return CheckResult(
        overall_status="PARTIAL",
        confidence_score=50,
        criteria=[
            CriterionResult(
                "Organisation Name Provided", True, "critical",
                "Value: 'Test Council'.", "2. Eligible Delivery Agency Details",
            ),
            CriterionResult(
                "Email Address Valid", True, "critical",
                "Email 'clerk@test.nsw.gov.au' looks valid.", "2. Eligible Delivery Agency Details",
            ),
            CriterionResult(
                "Start Date Before End Date", False, "critical",
                "Start date 2026-09-01 is after end date 2026-06-30.", "3. EPAR Project Details",
            ),
            CriterionResult(
                "D001 - Evidence File Naming Convention", False, "warning",
                "'photo.png' does not start with 'D001_'.", "4. Damage Information",
            ),
        ],
        application_id="UTS00009",
        applicant_name="Test Council",
        scanned_at="15 Jun 2026, 11:42 AM",
    )


def run_page(check: CheckResult | None = None, **state) -> AppTest:
    """Load the Results page through the real app entrypoint.

    AppTest.from_file on a pages/*.py file directly leaves the multipage
    registry empty, so any st.page_link/st.switch_page call inside that page
    raises. Routing through app.py + switch_page (as Streamlit's own testing
    docs recommend) gives the page a real registry, matching production.
    """
    at = AppTest.from_file(APP_PY, default_timeout=15)
    at.switch_page("pages/1_Results.py")
    at.session_state["check_result"] = check if check is not None else sample_check()
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def visible_count_text(at: AppTest) -> str:
    for block in at.markdown:
        if "Showing" in block.value and "criteria" in block.value:
            return block.value
    raise AssertionError("match counter not rendered")


def page_body(at: AppTest) -> str:
    return " ".join(block.value for block in at.markdown)


def test_page_runs_without_exceptions():
    at = run_page()
    assert not at.exception


def test_all_criteria_shown_by_default():
    at = run_page()
    assert "<strong>4</strong>" in visible_count_text(at)


def test_status_filter_narrows_results():
    at = run_page()
    at.multiselect[0].set_value(["Pass"]).run()
    assert "<strong>2</strong>" in visible_count_text(at)
    assert at.session_state[FILTER_STATUS] == ["Pass"]


def test_search_and_status_combine():
    at = run_page()
    at.multiselect[0].set_value(["Fail"]).run()
    at.text_input[0].set_value("date").run()
    assert "<strong>1</strong>" in visible_count_text(at)


def test_filters_survive_widget_state_loss():
    """Navigating to another page discards widget keys; stored filters must not reset.

    Running the page with the stored filter keys present but no widget keys is
    exactly the state Streamlit leaves behind after visiting the upload page:
    widget-bound state was garbage-collected, only our own keys survive.
    """
    at = run_page(**{FILTER_STATUS: ["Fail"], FILTER_SEARCH: "date"})
    assert at.session_state[FILTER_STATUS] == ["Fail"]
    assert at.multiselect[0].value == ["Fail"]
    assert at.text_input[0].value == "date"
    assert "<strong>1</strong>" in visible_count_text(at)


def test_clear_search_button_clears_only_search():
    at = run_page(**{FILTER_SEARCH: "date", FILTER_STATUS: ["Fail"]})
    clear_search = next(b for b in at.button if b.label == "Clear search")
    clear_search.click().run()
    assert at.session_state[FILTER_SEARCH] == ""
    assert at.session_state[FILTER_STATUS] == ["Fail"]


def test_clear_all_filters_restores_defaults():
    at = run_page(**{FILTER_SEARCH: "date", FILTER_STATUS: ["Fail"]})
    clear_all = next(b for b in at.button if b.label == "Clear all filters")
    clear_all.click().run()
    assert at.session_state[FILTER_SEARCH] == ""
    assert set(at.session_state[FILTER_STATUS]) == {"Pass", "Fail", "Review"}
    assert "<strong>4</strong>" in visible_count_text(at)


def test_zero_results_shows_empty_state_and_recovery():
    at = run_page(**{FILTER_SEARCH: "postcode"})
    assert "<strong>0</strong>" in visible_count_text(at)
    assert "No criteria match the current filters" in page_body(at)
    assert any(b.label == "Clear all filters" for b in at.button)


def test_no_check_result_shows_onboarding_empty_state():
    at = run_page(check=None)
    at.session_state["check_result"] = None
    at.run()
    assert not at.exception
    assert "No application checked yet" in page_body(at)


# The full class attribute of a rendered row; the bare modifier names also
# appear in the injected stylesheet, so tests must match the row markup.
def row_markup(status: str) -> str:
    return f'class="criteria-row criteria-row--{status}"'


def test_criteria_rows_are_status_coloured_with_icons():
    at = run_page()
    body = page_body(at)
    assert body.count(row_markup("pass")) == 2
    assert body.count(row_markup("review")) == 1
    assert body.count(row_markup("fail")) == 1
    # Each row carries an inline SVG status icon.
    assert body.count('class="criteria-row__icon"') == 4
    assert "<svg" in body


def test_status_filter_hides_non_matching_sections():
    at = run_page()
    at.multiselect[0].set_value(["Review"]).run()
    body = page_body(at)
    assert row_markup("review") in body
    assert row_markup("pass") not in body
    assert row_markup("fail") not in body


def test_flag_cards_render_most_severe_first():
    at = run_page()
    body = page_body(at)
    assert "flag-card--fail" in body
    assert "flag-card--review" in body
    # The critical flag card must appear before the warning card (most severe first).
    assert body.index("flag-card--fail") < body.index("flag-card--review")


def test_no_flags_shows_success_note():
    check = CheckResult(
        overall_status="PASS",
        confidence_score=100,
        criteria=[
            CriterionResult(
                "Organisation Name Provided", True, "critical",
                "Value: 'Clean Council'.", "2. Eligible Delivery Agency Details",
            ),
        ],
        application_id="UTS00010",
        applicant_name="Clean Council",
        scanned_at="15 Jun 2026, 11:42 AM",
    )
    at = run_page(check=check)
    assert not at.exception
    assert "flags-empty" in page_body(at)
