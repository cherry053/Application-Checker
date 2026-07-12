"""Tests for the incomplete-paste gate on the upload page."""

import io
from pathlib import Path

from reportlab.pdfgen import canvas

from core.paste_check import scan_paste

FIXTURE = Path(__file__).parent / "fixtures" / "damage_table.txt"


def make_pdf(declared_count: int | None) -> bytes:
    """A tiny SmartyGrants-style PDF that declares `declared_count` damage items."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(40, 800, "Application No. UTS00042 From Test Council - EPAR")
    c.drawString(40, 780, "Damage Information")
    c.drawString(40, 760, "Number of Damage Items")
    if declared_count is not None:
        c.drawString(40, 740, "Number of damaged items being restored")
        c.drawString(40, 720, str(declared_count))
    c.save()
    return buffer.getvalue()


def table_text(records: int) -> str:
    lines: list[str] = []
    for n in range(1, records + 1):
        lines.append("Public Infrastructure")
        lines.append(f"D{n:03d}")
    return "\n".join(lines)


def test_complete_paste_is_not_flagged():
    scan = scan_paste(make_pdf(2), table_text(2))
    assert scan.declared_count == 2
    assert scan.pasted_count == 2
    assert not scan.is_incomplete
    assert scan.incomplete_reason is None


def test_fewer_rows_than_declared_is_flagged():
    scan = scan_paste(make_pdf(7), table_text(3))
    assert scan.is_incomplete
    assert "7" in scan.incomplete_reason
    assert "3" in scan.incomplete_reason


def test_empty_but_nonblank_text_is_flagged():
    scan = scan_paste(make_pdf(2), "some notes that are not a table")
    assert scan.pasted_count == 0
    assert scan.is_incomplete
    assert "No complete damage-item rows" in scan.incomplete_reason


def test_no_declared_count_and_complete_paste_passes():
    scan = scan_paste(make_pdf(None), table_text(4))
    assert scan.declared_count is None
    assert not scan.is_incomplete


def test_unreadable_pdf_does_not_block():
    scan = scan_paste(b"not a real pdf", table_text(2))
    assert scan.declared_count is None
    # A recognisable table with no count to compare against is allowed through.
    assert not scan.is_incomplete


def test_real_fixture_matches_declared_count():
    scan = scan_paste(make_pdf(7), FIXTURE.read_text())
    assert scan.pasted_count == 7
    assert not scan.is_incomplete


def test_real_fixture_flagged_when_more_declared():
    scan = scan_paste(make_pdf(12), FIXTURE.read_text())
    assert scan.is_incomplete
    assert "12" in scan.incomplete_reason
