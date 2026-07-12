"""Lightweight check for an incompletely pasted damage table.

When the applicant pastes the damage table into the upload form, only part of
it may have been copied. This module compares the number of complete records
in the pasted text against the item count the PDF itself declares, so the
upload page can warn the user before running the full analysis. It
deliberately does *not* score field-level extraction quality - that is
surfaced through the normal validation criteria on the results page.

Free of Streamlit imports so it can be unit-tested directly.
"""

import io
import logging
from dataclasses import dataclass
from typing import Optional

from core.damage_table_parser import count_table_records
from core.field_parser import parse_post_table_fields
from core.models import ApplicationData
from core.pdf_extract import clean_lines, extract_pages
from core.section_splitter import split_sections

logger = logging.getLogger(__name__)


@dataclass
class PasteScan:
    """Result of scanning a pasted damage table for completeness."""

    declared_count: Optional[int]  # damage items the PDF declares, if stated
    pasted_count: int  # complete records recognised in the pasted text
    incomplete_reason: Optional[str] = None  # user-facing message, or None

    @property
    def is_incomplete(self) -> bool:
        return self.incomplete_reason is not None


def _declared_item_count(pdf_bytes: bytes) -> Optional[int]:
    """Read 'Number of damaged items being restored' from the PDF, if present."""
    pages = extract_pages(io.BytesIO(pdf_bytes))
    _, post_lines = split_sections(clean_lines(pages))
    data = ApplicationData()
    parse_post_table_fields(post_lines, data)
    return data.declared_item_count


def scan_paste(pdf_bytes: bytes, table_text: str) -> PasteScan:
    """Decide whether the pasted damage table looks incomplete.

    A table is flagged as incomplete when the pasted text yields no complete
    records, or fewer records than the PDF declares. Any failure to read the
    PDF is treated as "cannot tell" and does not block the user.
    """
    try:
        declared = _declared_item_count(pdf_bytes)
    except Exception:
        logger.exception("Could not read the declared item count for the paste check")
        declared = None

    pasted = count_table_records(table_text)

    reason: Optional[str] = None
    if table_text.strip() and pasted == 0:
        reason = "No complete damage-item rows could be recognised in the pasted table."
    elif declared is not None and pasted < declared:
        missing = declared - pasted
        reason = (
            f"The application form lists {declared} damage item(s), but only "
            f"{pasted} complete row(s) were found in the pasted table "
            f"({missing} missing)."
        )

    if reason:
        logger.info("Incomplete paste detected: %s", reason)
    return PasteScan(declared_count=declared, pasted_count=pasted, incomplete_reason=reason)
