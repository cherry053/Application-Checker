import streamlit as st

st.set_page_config(page_title="Results | Grant Application Quality Checker", layout="wide")

from core.filters import VALID_STATUSES, filter_applications, status_counts
from core.models import ApplicationResult, CheckResult
from core.report_pdf import build_feedback_pdf
from core.sections import group_by_section, section_passed_counts
from utils.ui import (
    render_criteria_rows,
    render_empty_state,
    render_footer,
    render_header,
    render_readiness_badge,
    render_status_pill,
    render_validation_panel,
)

render_header("Grant Application Quality Checker")

# --- Session state ----------------------------------------------------------
#
# Filter values live in their own session keys (FILTER_*), separate from the
# widget keys. Streamlit discards widget-bound state whenever the widget is
# not rendered - i.e. every time the user visits the upload page - so binding
# the widgets directly to the stored values silently reset the filters on
# navigation. Each run re-seeds the widget keys from the stored values and the
# widgets sync back through on_change callbacks.

FILTER_STATUS = "filter_status"
FILTER_SEARCH = "filter_search"
_STATUS_WIDGET = "filter_status_widget"
_SEARCH_WIDGET = "filter_search_widget"

st.session_state.setdefault("processed_applications", [])
st.session_state.setdefault(FILTER_STATUS, list(VALID_STATUSES))
st.session_state.setdefault(FILTER_SEARCH, "")
st.session_state[_STATUS_WIDGET] = st.session_state[FILTER_STATUS]
st.session_state[_SEARCH_WIDGET] = st.session_state[FILTER_SEARCH]


def sync_status_filter() -> None:
    st.session_state[FILTER_STATUS] = st.session_state[_STATUS_WIDGET]


def sync_search_filter() -> None:
    st.session_state[FILTER_SEARCH] = st.session_state[_SEARCH_WIDGET]


def clear_search_filter() -> None:
    st.session_state[FILTER_SEARCH] = ""


def clear_all_filters() -> None:
    st.session_state[FILTER_STATUS] = list(VALID_STATUSES)
    st.session_state[FILTER_SEARCH] = ""


def handle_new_application_submit() -> None:
    """Open the new-application intake flow.

    Flags the intake flow so the main script navigates to the upload form.
    """
    st.session_state["open_new_application"] = True


def handle_close_results() -> None:
    """Close the detail view for the currently selected application."""
    st.session_state["check_result"] = None


def handle_view_details(application: ApplicationResult) -> None:
    st.session_state["check_result"] = application.check


applications: list[ApplicationResult] = st.session_state["processed_applications"]

# An application checked before the list existed still appears in it.
active_result = st.session_state.get("check_result")
if active_result is not None and not any(a.check is active_result for a in applications):
    applications.append(ApplicationResult.from_check(active_result))

if st.session_state.pop("open_new_application", False):
    st.switch_page("app.py")

title_col, close_col, new_col = st.columns([3, 0.7, 1.3], vertical_alignment="center")

with title_col:
    st.header("Processed applications", anchor=False)

with close_col:
    st.button(
        "Close",
        use_container_width=True,
        on_click=handle_close_results,
        help="Close the detailed results view",
    )

with new_col:
    st.button(
        "Submit New Application",
        type="primary",
        use_container_width=True,
        on_click=handle_new_application_submit,
    )

if not applications:
    render_empty_state(
        "No applications checked yet",
        "Upload a SmartyGrants export on the home page to see its quality check results here.",
    )
    st.page_link("app.py", label="Back to upload", icon=":material/arrow_back:")
    st.stop()

counts = status_counts(applications)
search_active = bool(st.session_state[FILTER_SEARCH].strip())
filters_active = search_active or set(st.session_state[FILTER_STATUS]) != set(VALID_STATUSES)

with st.container(key="filter_panel"):
    st.markdown('<p class="filter-panel__heading">Filter applications</p>', unsafe_allow_html=True)

    status_col, search_col, actions_col = st.columns([2, 2, 1], vertical_alignment="bottom")

    with status_col:
        st.multiselect(
            "Application status",
            options=list(VALID_STATUSES),
            key=_STATUS_WIDGET,
            on_change=sync_status_filter,
            format_func=lambda status: f"{status} ({counts[status]})",
            placeholder="All statuses",
            help="Remove a status chip to hide those applications; leave empty to show none.",
        )

    with search_col:
        st.text_input(
            "Search applications",
            key=_SEARCH_WIDGET,
            on_change=sync_search_filter,
            placeholder="Application ID or applicant name",
            help="Matches anywhere in the application ID or applicant name; press Enter to apply.",
        )

    with actions_col:
        st.button(
            "Clear search",
            use_container_width=True,
            on_click=clear_search_filter,
            disabled=not search_active,
        )
        st.button(
            "Clear all filters",
            use_container_width=True,
            on_click=clear_all_filters,
            disabled=not filters_active,
        )

    # Filtering is an in-memory scan, fast even for hundreds of applications;
    # no loading indicator is needed here.
    visible = filter_applications(
        applications, set(st.session_state[FILTER_STATUS]), st.session_state[FILTER_SEARCH]
    )

    st.markdown(
        f'<p class="filter-panel__count" role="status">Showing <strong>{len(visible)}</strong> '
        f"of {len(applications)} application(s)</p>",
        unsafe_allow_html=True,
    )

if not visible:
    render_empty_state(
        "No applications match the current filters",
        "Adjust the search term or status selection, or clear the filters to see every "
        "processed application.",
    )
    st.button("Clear all filters", key="clear_filters_empty", type="primary", on_click=clear_all_filters)

for application in visible:
    with st.container(border=True):
        info_col, status_col, action_col = st.columns([4, 1, 1], vertical_alignment="center")

        with info_col:
            st.markdown(f"**{application.application_id} — {application.applicant_name}**")
            st.caption(f"Scanned on {application.scanned_at}")

        with status_col:
            render_status_pill(application.status)

        with action_col:
            st.button(
                "View details",
                key=f"view_details_{application.application_id}_{id(application)}",
                use_container_width=True,
                on_click=handle_view_details,
                args=(application,),
                help=f"Show detailed results for {application.application_id}",
            )

st.divider()

result: CheckResult | None = st.session_state.get("check_result")


def _report_pdf_bytes(check: CheckResult) -> bytes:
    """Build the feedback PDF once per application and cache it for reruns."""
    cache: dict = st.session_state.setdefault("_report_pdf_cache", {})
    key = (check.application_id, check.scanned_at)
    if key not in cache:
        if len(cache) >= 8:  # keep the session cache small
            cache.clear()
        with st.spinner("Generating PDF report..."):
            cache[key] = build_feedback_pdf(check)
    return cache[key]


def _section_icon(criteria) -> str:
    failed = [c for c in criteria if not c.passed]
    if not failed:
        return ":material/check_circle:"
    if all(c.severity == "warning" for c in failed):
        return ":material/warning:"
    return ":material/error:"


if result is None:
    st.caption("Select an application above to see its detailed results.")
else:
    passed_count = sum(1 for c in result.criteria if c.passed)
    total_count = len(result.criteria)
    flags_raised = total_count - passed_count

    items_total = sum(item.cost_total for item in result.damage_items if item.cost_total is not None)
    estimated_cost = result.total_requested if result.total_requested is not None else items_total

    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.caption("APPLICATION")
        st.subheader(
            f"{result.application_id or 'Unknown ID'} - {result.applicant_name or 'Unknown applicant'}",
            anchor=False,
        )
        st.caption(f"Scanned on {result.scanned_at}")
        st.caption(f"{len(result.damage_items)} damaged item(s) parsed")

    with col_right:
        render_readiness_badge(result.overall_status)
        st.download_button(
            "Download feedback (PDF)",
            data=_report_pdf_bytes(result),
            file_name=f"{result.application_id or 'application'}_feedback.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Criteria passed", f"{passed_count} / {total_count}")

    with col2:
        st.metric("Flags raised", flags_raised)

    with col3:
        st.metric("Total ERC", f"${estimated_cost:,.0f}")

    with col4:
        st.metric("Damage items", len(result.damage_items))

    st.divider()

    st.header("Table Completeness Check", anchor=False)
    if result.completeness is None:
        st.caption(
            "Not available for this application - it was checked before the Table "
            "Completeness Check was introduced. Re-check the application to run it."
        )
    else:
        render_validation_panel(result.completeness)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.header("Criteria summary", anchor=False)
        for section, criteria in group_by_section(result.criteria).items():
            section_passed, section_total = section_passed_counts(criteria)
            label = f"{section} — {section_passed}/{section_total} passed"
            with st.expander(label, icon=_section_icon(criteria)):
                for criterion in criteria:
                    render_criteria_rows(
                        {
                            "name": criterion.name,
                            "passed": criterion.passed,
                            "severity": criterion.severity,
                        }
                    )
                    if not criterion.passed:
                        st.caption(criterion.detail)

    with col2:
        st.header("Active flags", anchor=False)
        flagged = [c for c in result.criteria if not c.passed]
        if not flagged:
            st.success("No flags raised.")
        for criterion in flagged:
            with st.expander(f"{criterion.section or 'General'} · {criterion.name}"):
                st.write(criterion.detail)

st.divider()

render_footer()
