"""Tests for the standalone Processing (loading) page."""

import io
from pathlib import Path

from reportlab.pdfgen import canvas
from streamlit.testing.v1 import AppTest

APP_PY = str(Path(__file__).parent.parent / "app.py")
FIXTURE = Path(__file__).parent / "fixtures" / "damage_table.txt"


def load_processing_page(default_timeout: float = 20) -> AppTest:
    """Load the Processing page through the real app entrypoint.

    AppTest.from_file on a pages/*.py file directly leaves the multipage
    registry empty, so the page's own st.page_link/st.switch_page calls
    raise. Routing through app.py + switch_page (as Streamlit's own testing
    docs recommend) gives the page a real registry, matching production.
    """
    at = AppTest.from_file(APP_PY, default_timeout=default_timeout)
    at.switch_page("pages/2_Processing.py")
    return at


def make_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(40, 800, "Application No. UTS00042 From Test Council - EPAR")
    c.drawString(40, 780, "Organisation Name *")
    c.drawString(40, 760, "Test Council")
    c.drawString(40, 740, "Damage Information")
    c.drawString(40, 720, "Number of Damage Items")
    c.save()
    return buffer.getvalue()


def test_processing_without_input_redirects():
    at = load_processing_page().run()
    assert not at.exception
    body = " ".join(block.value for block in at.info)
    assert "No application is currently being processed" in body


def test_processing_runs_pipeline_and_stores_result():
    at = load_processing_page(default_timeout=60)
    at.session_state["processing_input"] = {
        "pdf_bytes": make_pdf(),
        "table_text": FIXTURE.read_text(),
        "filename": "Application-UTS00042.pdf",
    }
    at.run()
    assert not at.exception
    # The pipeline ran and produced a result that the page stashed for Results.
    assert at.session_state["check_result"] is not None
    # The input is consumed so a refresh does not reprocess.
    assert "processing_input" not in at.session_state
