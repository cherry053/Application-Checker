import logging

import streamlit as st

st.set_page_config(page_title="Grant Application Quality Checker", layout="wide")

from core.paste_check import scan_paste
from utils.ui import (
    render_cards,
    render_errormessage,
    render_footer,
    render_header,
    render_incomplete_warning,
    render_nosection,
    render_splash,
    render_uploadinfo,
)

logger = logging.getLogger(__name__)

_AWAITING = "awaiting_paste_confirm"

render_splash()
render_header("Grant Application Quality Checker")

render_uploadinfo()

render_nosection()
render_nosection()

st.header("Upload SmartyGrants export", text_alignment="center", anchor=False)

render_nosection()


def _start_processing(pdf_bytes: bytes, table_text: str, filename: str, note: str | None = None) -> None:
    """Hand the inputs to the dedicated loading page and navigate there."""
    st.session_state["processing_input"] = {
        "pdf_bytes": pdf_bytes,
        "table_text": table_text,
        "filename": filename,
        "note": note,
    }
    st.session_state.pop(_AWAITING, None)
    st.switch_page("pages/2_Processing.py")


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
        st.session_state.pop(_AWAITING, None)
        render_errormessage()
    else:
        pdf_bytes = pdf_file.getvalue()
        with st.spinner("Checking your upload..."):
            scan = scan_paste(pdf_bytes, table_text)

        if scan.is_incomplete:
            # Warn before running the full analysis; the user confirms below.
            st.session_state[_AWAITING] = {
                "reason": scan.incomplete_reason,
                "pdf_bytes": pdf_bytes,
                "table_text": table_text,
                "filename": pdf_file.name,
            }
        else:
            _start_processing(pdf_bytes, table_text, pdf_file.name)


# Incomplete-paste confirmation gate. Persists across reruns until answered.
awaiting = st.session_state.get(_AWAITING)
if awaiting:
    render_incomplete_warning(awaiting["reason"])
    yes_col, no_col, _spacer = st.columns([1.2, 1.2, 3])
    with yes_col:
        if st.button("Yes, continue", type="primary", use_container_width=True):
            _start_processing(
                awaiting["pdf_bytes"],
                awaiting["table_text"],
                awaiting["filename"],
                note=awaiting["reason"],
            )
    with no_col:
        if st.button("No, re-paste the table", use_container_width=True):
            st.session_state.pop(_AWAITING, None)
            st.rerun()


render_cards()

render_nosection()

render_footer()
