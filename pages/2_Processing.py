import logging
from html import escape

import streamlit as st

st.set_page_config(page_title="Processing | Grant Application Quality Checker", layout="wide")

from core.pipeline import TOTAL_STAGES, check_application
from utils.ui import render_header

logger = logging.getLogger(__name__)

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

_last_rendered_step = 0


def _on_progress(step: int, total: int, message: str, stage_fraction: float = 0.0) -> None:
    # Reflect the pipeline's real progress only; any artificial delay here
    # directly slows down every check. `stage_fraction` arrives once per
    # extracted page during the reading stage, so the bar fills as the
    # parser works through the document; the checklist only needs redrawing
    # when the stage itself changes.
    global _last_rendered_step
    if step != _last_rendered_step:
        _render_steps(step)
        _last_rendered_step = step
    progress.progress(min((step + stage_fraction) / total, 1.0), text=message)


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

st.session_state["check_result"] = result
st.session_state.pop("processing_input", None)

st.switch_page("pages/1_Results.py")
