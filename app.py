import streamlit as st

from core.models import ApplicationResult
from core.pipeline import check_application
from utils.ui import render_header, render_footer, render_cards, render_masthead, render_nosection, render_errormessage, render_uploadinfo

render_masthead()

st.set_page_config(page_title="Grant Application Quality Checker", layout="wide")


render_header("Grant Application Quality Checker")

render_uploadinfo()

render_nosection()
render_nosection()

st.title("Upload SmartyGrants export", text_alignment="center", anchor=False)

render_nosection()


with st.form("application_checker"):

    uploads = st.file_uploader(
        "Drag and drop your files here",
        type=None,
        accept_multiple_files=True
    )

    tabletext = st.text_area(
        "Enter Asset Damage Table information here:"
    )

    submitted = st.form_submit_button("Check application")


if submitted:
    uploads = uploads or []
    pdf_file = next((f for f in uploads if f.name.lower().endswith(".pdf")), None)
    txt_file = next((f for f in uploads if f.name.lower().endswith(".txt")), None)

    table_text = tabletext.strip()
    if not table_text and txt_file is not None:
        table_text = txt_file.getvalue().decode("utf-8", errors="replace")

    if pdf_file is None or not table_text:
        render_errormessage()
    else:
        try:
            result = check_application(pdf_file, table_text)
        except Exception as error:
            st.error(f"Could not check the application: {error}")
        else:
            st.session_state["check_result"] = result
            st.session_state.setdefault("processed_applications", []).append(
                ApplicationResult.from_check(result)
            )
            st.switch_page("pages/1_Results.py")


render_cards()

render_nosection()

render_footer()
