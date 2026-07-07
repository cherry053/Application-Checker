import streamlit as st

from core.report_pdf import build_feedback_pdf
from core.sections import group_by_section, section_passed_counts
from utils.ui import render_header, render_readiness_badge, render_criteria_rows, render_footer

st.set_page_config(page_title="Results | Grant Application Quality Checker", layout="wide")

render_header("Grant Application Quality Checker")

result = st.session_state.get("check_result")

if result is None:
    st.info("No application has been checked yet. Upload an export on the home page first.")
    st.page_link("app.py", label="Back to upload")
    st.stop()

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
