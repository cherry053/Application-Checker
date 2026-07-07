import streamlit as st

from utils.mock_data import MOCK_RESULT

from utils.ui import render_header, render_readiness_badge, render_criteria_rows, render_footer

st.set_page_config(page_title="Results | Grant Application Quality Checker", layout="wide")

render_header("Grant Application Quality Checker")

result = MOCK_RESULT

passed_count = sum(1 for c in result["criteria"] if c["passed"])
total_count = len(result["criteria"])
flags_raised = total_count - passed_count

col_left, col_right = st.columns([3, 1])

with col_left:
    st.caption("APPLICATION")
    st.subheader(f"{result['application_id']} - {result['applicant_name']}", anchor=False)
    st.caption(f"{result['agrn']} . Scanned on {result['scanned_at']}")
    st.caption(f"{result['damage_items']} damaged item(s) parsed")

with col_right:
    render_readiness_badge(result["overall_status"])

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Criteria passed", f"{passed_count} / {total_count}")

with col2:
    st.metric("Flags raised", flags_raised)

with col3:
    st.metric("Total ERC", f"${result['estimated_cost']:,.0f}")

with col4:
    st.metric("Damage items", result["damage_items"])

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.header("Criteria summary", anchor=False)
    for criterion in result["criteria"]:
        render_criteria_rows(criterion)


with col2: 
    st.header("Active flags", anchor=False)

st.divider()

render_footer()

