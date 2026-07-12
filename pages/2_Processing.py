import logging
import time
from html import escape

import streamlit as st

st.set_page_config(page_title="Processing | Grant Application Quality Checker", layout="wide")

from core.filters import upsert_application
from core.models import ApplicationResult
from core.pipeline import TOTAL_STAGES, check_application
from utils.ui import render_footer, render_header

logger = logging.getLogger(__name__)

# Time each stage stays visible, so users can watch the checker move through
# the steps rather than staring at a frozen screen. The real work is fast; this
# deliberate pacing keeps the staged progress legible without a long wait.
STEP_DELAY_SECONDS = 0.45

# User-facing checklist, aligned with core.pipeline._STAGES (one row per stage).
STEP_LABELS = (
    "Reading document",
    "Parsing application fields",
    "Extracting damage table",
    "Validating criteria",
    "Generating report",
)

render_header("Grant Application Quality Checker")

payload = st.session_state.get("processing_input")
if not payload:
    st.info("No application is currently being processed. Upload an export to begin a check.")
    st.page_link("app.py", label="Back to upload", icon=":material/arrow_back:")
    st.stop()

filename = payload.get("filename") or "your application"

st.markdown(
    '<div class="processing-hero" id="main-content">'
    f'<p class="processing-hero__file">Analysing {escape(filename)}</p>'
    '<p class="processing-hero__sub">Please wait while the checker validates your application&hellip;</p>'
    "</div>",
    unsafe_allow_html=True,
)

progress = st.progress(0.0)
checklist = st.empty()


def _render_steps(current: int, all_done: bool = False) -> None:
    rows = []
    for index, label in enumerate(STEP_LABELS):
        if all_done or index < current:
            state, icon = "done", "&#10003;"
        elif index == current:
            state, icon = "active", ""
        else:
            state, icon = "pending", str(index + 1)
        rows.append(
            f'<li class="processing-step processing-step--{state}">'
            f'<span class="processing-step__icon">{icon}</span>{label}</li>'
        )
    checklist.markdown(
        f'<ol class="processing-steps">{"".join(rows)}</ol>', unsafe_allow_html=True
    )


_render_steps(0)


def _on_progress(step: int, total: int, message: str) -> None:
    _render_steps(step)
    progress.progress(step / total)
    time.sleep(STEP_DELAY_SECONDS)


try:
    result = check_application(
        payload["pdf_bytes"], payload["table_text"], on_progress=_on_progress
    )
except Exception as error:  # noqa: BLE001 - surface any parsing failure to the user
    logger.exception("Application check failed for %s", filename)
    checklist.empty()
    progress.empty()
    st.error(f"Could not check the application: {error}")
    st.page_link("app.py", label="Back to upload", icon=":material/arrow_back:")
    st.stop()

_render_steps(TOTAL_STAGES, all_done=True)
progress.progress(1.0)

note = payload.get("note")
if note:
    st.markdown(
        f'<p class="processing-note"><strong>Note:</strong> {note} '
        "You chose to continue - review the flagged damage items on the results page.</p>",
        unsafe_allow_html=True,
    )

st.session_state["check_result"] = result
applications = st.session_state.setdefault("processed_applications", [])
upsert_application(applications, ApplicationResult.from_check(result))
st.session_state.pop("processing_input", None)

time.sleep(0.4)
st.switch_page("pages/1_Results.py")

render_footer()
