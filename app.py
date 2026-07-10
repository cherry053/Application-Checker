import logging

import streamlit as st

st.set_page_config(page_title="Grant Application Quality Checker", layout="wide")

from core.filters import upsert_application
from core.models import ApplicationResult
from core.pipeline import check_application
from utils.ui import (
    render_cards,
    render_errormessage,
    render_footer,
    render_header,
    render_nosection,
    render_splash,
    render_uploadinfo,
)

logger = logging.getLogger(__name__)

render_splash()
render_header("Grant Application Quality Checker")

render_uploadinfo()

render_nosection()
render_nosection()

st.header("Upload SmartyGrants export", text_alignment="center", anchor=False)

render_nosection()


with st.form("application_checker"):

    uploads = st.file_uploader(
        "Drag and drop your files here",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        help="Upload the SmartyGrants PDF export, plus optionally the damage table as a .txt file.",
    )

    tabletext = st.text_area(
        "Enter Asset Damage Table information here:",
        help="Copy the damage table out of the web form and paste it as plain text, "
        "or upload it as a .txt file above.",
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
        progress = st.progress(0, text="Loading application...")

        def _report_progress(step: int, total: int, message: str) -> None:
            progress.progress(step / total, text=message)

        try:
            result = check_application(pdf_file, table_text, on_progress=_report_progress)
        except Exception as error:
            progress.empty()
            logger.exception("Application check failed for %s", pdf_file.name)
            st.error(f"Could not check the application: {error}")
        else:
            progress.progress(1.0, text="Finalising report...")
            st.session_state["check_result"] = result
            applications = st.session_state.setdefault("processed_applications", [])
            upsert_application(applications, ApplicationResult.from_check(result))
            st.switch_page("pages/1_Results.py")


render_cards()

render_nosection()

render_footer()
