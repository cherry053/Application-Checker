import streamlit as st

from core.filters import VALID_STATUSES, filter_applications, status_counts
from core.models import ApplicationResult
from core.report_pdf import build_feedback_pdf
from core.sections import group_by_section, section_passed_counts
from utils.ui import (
    render_header,
    render_readiness_badge,
    render_criteria_rows,
    render_footer,
    render_status_pill,
)

st.set_page_config(page_title="Results | Grant Application Quality Checker", layout="wide")

render_header("Grant Application Quality Checker")

st.session_state.setdefault("processed_applications", [])
st.session_state.setdefault("status_filter", list(VALID_STATUSES))
st.session_state.setdefault("search_term", "")


def handle_new_application_submit() -> None:
    """Open the new-application intake flow.

    Placeholder: the actual submission logic is wired separately. For now it
    flags the intake flow so the main script navigates to the upload form.
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
    st.button("Close", use_container_width=True, on_click=handle_close_results)

with new_col:
    st.button(
        "Submit New Application",
        type="primary",
        use_container_width=True,
        on_click=handle_new_application_submit,
    )

if not applications:
    st.info("No application has been checked yet. Upload an export on the home page first.")
    st.page_link("app.py", label="Back to upload")
    st.stop()

counts = status_counts(applications)

filter_col, search_col = st.columns(2)

with filter_col:
    selected_statuses = st.multiselect(
        "Filter by status",
        options=list(VALID_STATUSES),
        key="status_filter",
        format_func=lambda status: f"{status} ({counts[status]})",
    )

with search_col:
    search_term = st.text_input(
        "Search applications",
        key="search_term",
        placeholder="Application ID or applicant name",
    )

visible = filter_applications(applications, set(selected_statuses), search_term)

st.caption(f"Showing {len(visible)} of {len(applications)} application(s)")

if not visible:
    st.warning("No applications match the current filters.")

for index, application in enumerate(visible):
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
                key=f"view_details_{index}",
                use_container_width=True,
                on_click=handle_view_details,
                args=(application,),
            )

st.divider()

result = st.session_state.get("check_result")

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
        st.subheader(f"{result.application_id or 'Unknown ID'} - {result.applicant_name or 'Unknown applicant'}", anchor=False)
        st.caption(f"Scanned on {result.scanned_at}")
        st.caption(f"{len(result.damage_items)} damaged item(s) parsed")

    with col_right:
        render_readiness_badge(result.overall_status)
        st.download_button(
            "Download feedback (PDF)",
            data=build_feedback_pdf(result),
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

    col1, col2 = st.columns(2)


    def _section_icon(criteria) -> str:
        failed = [c for c in criteria if not c.passed]
        if not failed:
            return "✅"
        if all(c.severity == "warning" for c in failed):
            return "⚠️"
        return "❌"


    with col1:
        st.header("Criteria summary", anchor=False)
        for section, criteria in group_by_section(result.criteria).items():
            section_passed, section_total = section_passed_counts(criteria)
            label = f"{_section_icon(criteria)} {section} — {section_passed}/{section_total} passed"
            with st.expander(label):
                for criterion in criteria:
                    render_criteria_rows(
                        {"name": criterion.name, "passed": criterion.passed, "severity": criterion.severity}
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
