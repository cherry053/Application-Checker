"""Table Completeness Check.

Verifies that the information contained in the pasted damage-table text was
fully extracted into the application. Three views of the same data are
compared:

1. the raw pasted table text (what the applicant supplied),
2. the parsed damage items (what the extraction produced), and
3. the damage-item count the PDF itself declares (an independent cross-check).

The check goes beyond row counting: it looks for missing rows, columns that
never extracted, blank fields, duplicated records, truncated text and
encoding/OCR artefacts, and parser misalignment (the signature of merged or
wrapped cells). The result is a scored `CompletenessReport` with an explicit
confidence level - a "complete" verdict is never issued on low confidence.

Free of Streamlit imports so it can be unit-tested directly.
"""

import logging
from typing import Optional

from core.damage_table_parser import count_table_records
from core.models import CompletenessIssue, CompletenessReport, DamageItem

logger = logging.getLogger(__name__)

# The damage-table columns the extraction is expected to recover, as
# (display label, DamageItem attribute) pairs. Asset Material and the
# pre-disaster-function answer are excluded: the plain-text export does not
# mark those selections, so their absence is a known export limitation rather
# than an extraction failure (the parser records it as an informational note).
EXPECTED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("Asset Category", "asset_category"),
    ("Damage Item ID", "damage_item_id"),
    ("Asset ID", "asset_id"),
    ("Asset Name", "asset_name"),
    ("Date Asset Accessible", "date_accessible"),
    ("Damage Location Start", "location_start"),
    ("Damage Location End", "location_end"),
    ("Chainage Focal Point", "chainage_focal"),
    ("Chainage From", "chainage_from"),
    ("Chainage To", "chainage_to"),
    ("Longitude From", "longitude_from"),
    ("Latitude From", "latitude_from"),
    ("Longitude To", "longitude_to"),
    ("Latitude To", "latitude_to"),
    ("Asset Sub-Category", "sub_category"),
    ("Classification Type", "classification_type"),
    ("Asset Capacity", "capacity"),
    ("Asset Layout", "layout"),
    ("Asset Dimensions", "dimensions"),
    ("Pre-Disaster Evidence File", "pre_disaster_evidence_file"),
    ("Damage Evidence File", "damage_evidence_file"),
    ("Damage Description", "damage_description"),
    ("Estimation Method", "estimation_method"),
    ("Construction Cost", "cost_construction"),
    ("PM & Design Cost", "cost_pm_design"),
    ("Contingency Cost", "cost_contingency"),
    ("Escalation Cost", "cost_escalation"),
    ("Total Damage Estimate", "cost_total"),
    ("Cost Evidence File", "cost_evidence_file"),
    ("Cost Estimation Methodology", "methodology"),
)

# Parser notes containing this phrase describe information the text export
# cannot carry at all; they are reported as info, not extraction failures.
_EXPORT_LIMITATION_MARKER = "cannot be determined from the text export"

# Signs of truncated or corrupted text in an extracted value.
_TRUNCATION_SUFFIXES = ("...", "…", "-")
_REPLACEMENT_CHAR = "�"

# Scoring weights and thresholds.
_ROW_WEIGHT = 0.55
_FIELD_WEIGHT = 0.45
_MAX_QUALITY_PENALTY = 15
_COMPLETE_MIN_SCORE = 98
_REVIEW_MIN_SCORE = 80
_COMPLETE_MIN_CONFIDENCE = 80  # never report "complete" below this


def _display_label(item: DamageItem, position: int) -> str:
    return item.damage_item_id or f"Item {position}"


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _text_quality_problems(value: str) -> list[str]:
    """Signs that a value was truncated or mangled during extraction."""
    problems: list[str] = []
    stripped = value.strip()
    if _REPLACEMENT_CHAR in stripped:
        problems.append("contains undecodable characters (possible OCR/encoding failure)")
    if any(ord(ch) < 32 and ch not in "\t\n" for ch in stripped):
        problems.append("contains control characters")
    if stripped.endswith(_TRUNCATION_SUFFIXES) and len(stripped) > 3:
        problems.append("appears truncated (ends mid-sentence)")
    return problems


def _duplicate_row_count(items: list[DamageItem], issues: list[CompletenessIssue]) -> int:
    """Extra occurrences of records sharing an ID or identical key content."""
    seen_ids: dict[str, int] = {}
    seen_content: dict[tuple, int] = {}
    duplicates = 0
    for item in items:
        if item.damage_item_id:
            seen_ids[item.damage_item_id] = seen_ids.get(item.damage_item_id, 0) + 1
        else:
            key = (item.asset_id, item.asset_name, str(item.cost_total))
            seen_content[key] = seen_content.get(key, 0) + 1

    for item_id, count in seen_ids.items():
        if count > 1:
            duplicates += count - 1
            issues.append(
                CompletenessIssue(
                    "warning", f"Damage item ID '{item_id}' appears {count} times in the extracted table."
                )
            )
    for key, count in seen_content.items():
        if count > 1 and any(key):
            duplicates += count - 1
            issues.append(
                CompletenessIssue("warning", f"{count} extracted rows without an ID have identical content.")
            )
    return duplicates


def assess_completeness(
    table_text: str,
    items: list[DamageItem],
    declared_count: Optional[int],
    table_warnings: Optional[list[str]] = None,
) -> CompletenessReport:
    """Score how completely the pasted damage table was extracted.

    `table_text` is the raw pasted export, `items` the parsed damage items,
    `declared_count` the item count stated in the PDF (None when the PDF does
    not declare one), and `table_warnings` the parser's warning list.
    """
    issues: list[CompletenessIssue] = []
    warnings = table_warnings or []

    rows_detected = count_table_records(table_text)
    rows_extracted = len(items)
    expected_rows = max(rows_detected, declared_count or 0)
    rows_missing = max(0, expected_rows - rows_extracted)

    # --- Row-level findings -------------------------------------------------
    if not table_text.strip():
        issues.append(CompletenessIssue("critical", "No damage-table text was supplied."))
    elif rows_detected == 0:
        issues.append(
            CompletenessIssue(
                "critical",
                "No damage-item records could be recognised in the pasted table text; "
                "the table format may not match the expected export.",
            )
        )
    if rows_detected and rows_extracted < rows_detected:
        issues.append(
            CompletenessIssue(
                "critical",
                f"{rows_detected} record(s) detected in the table text but only "
                f"{rows_extracted} extracted.",
            )
        )
    if declared_count is not None and declared_count != rows_extracted:
        issues.append(
            CompletenessIssue(
                "critical" if declared_count > rows_extracted else "warning",
                f"The application declares {declared_count} damage item(s) but "
                f"{rows_extracted} were extracted from the table text.",
            )
        )
    duplicate_rows = _duplicate_row_count(items, issues)

    # --- Column/field-level findings ----------------------------------------
    columns_expected = len(EXPECTED_COLUMNS)
    fields_expected = columns_expected * rows_extracted
    fields_extracted = 0
    column_hits = {attribute: 0 for _, attribute in EXPECTED_COLUMNS}
    quality_issues = 0

    for position, item in enumerate(items, start=1):
        blank_labels: list[str] = []
        for label, attribute in EXPECTED_COLUMNS:
            value = getattr(item, attribute)
            if _is_blank(value):
                blank_labels.append(label)
                continue
            fields_extracted += 1
            column_hits[attribute] += 1
            if isinstance(value, str):
                for problem in _text_quality_problems(value):
                    quality_issues += 1
                    issues.append(
                        CompletenessIssue(
                            "warning", f"{_display_label(item, position)}: {label} {problem}."
                        )
                    )
        if blank_labels:
            shown = ", ".join(blank_labels[:6]) + ("…" if len(blank_labels) > 6 else "")
            issues.append(
                CompletenessIssue(
                    "warning",
                    f"{_display_label(item, position)}: {len(blank_labels)} field(s) empty ({shown}).",
                )
            )

    columns_extracted = sum(1 for hits in column_hits.values() if hits > 0) if items else 0
    if items:
        missing_columns = [label for label, attribute in EXPECTED_COLUMNS if column_hits[attribute] == 0]
        if missing_columns:
            shown = ", ".join(missing_columns[:6]) + ("…" if len(missing_columns) > 6 else "")
            issues.append(
                CompletenessIssue(
                    "critical",
                    f"{len(missing_columns)} column(s) extracted no values in any row ({shown}); "
                    "the source table may use merged cells or an unexpected layout.",
                )
            )

    # --- Parser warnings: misalignment is the signature of merged/wrapped cells
    structural_notes = [w for w in warnings if _EXPORT_LIMITATION_MARKER in w]
    real_warnings = [w for w in warnings if _EXPORT_LIMITATION_MARKER not in w]
    for warning in real_warnings:
        issues.append(CompletenessIssue("warning", f"Parser: {warning}"))
    if structural_notes:
        issues.append(
            CompletenessIssue(
                "info",
                "Asset Material and pre-disaster-function selections are not carried by the "
                "plain-text export and require manual confirmation.",
            )
        )

    # --- Score ----------------------------------------------------------------
    row_score = rows_extracted / expected_rows if expected_rows else 0.0
    row_score = min(row_score, 1.0)
    field_score = fields_extracted / fields_expected if fields_expected else 0.0
    base = 100 * (_ROW_WEIGHT * row_score + _FIELD_WEIGHT * field_score)
    penalty = min(_MAX_QUALITY_PENALTY, 2 * (quality_issues + len(real_warnings)) + 3 * duplicate_rows)
    score = max(0, round(base - penalty))

    # --- Confidence: how much the assessment itself can be trusted -------------
    empty_fields = max(0, fields_expected - fields_extracted)
    confidence = 100
    if rows_detected == 0:
        confidence -= 60  # nothing recognisable to compare against
    if declared_count is None:
        confidence -= 15  # no independent count to cross-check
    elif declared_count != rows_extracted:
        confidence -= 20
    confidence -= min(30, 5 * len(real_warnings))
    confidence -= min(15, 2 * empty_fields)  # blanks cannot be confirmed empty at source
    if duplicate_rows:
        confidence -= 10
    confidence = max(0, confidence)

    # --- Status. "Complete" requires everything extracted (no missing rows, no
    # blanks - a blank cannot be told apart from a dropped value automatically)
    # AND high confidence in the assessment itself; otherwise degrade honestly.
    if score >= _COMPLETE_MIN_SCORE and rows_missing == 0 and empty_fields == 0 and duplicate_rows == 0:
        status = "complete" if confidence >= _COMPLETE_MIN_CONFIDENCE else "review"
    elif score >= _REVIEW_MIN_SCORE:
        status = "review"
    else:
        status = "incomplete"

    logger.info(
        "Completeness check: %s (score=%d, confidence=%d, rows %d/%d, fields %d/%d)",
        status, score, confidence, rows_extracted, expected_rows, fields_extracted, fields_expected,
    )

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda issue: severity_order[issue.severity])

    return CompletenessReport(
        rows_declared=declared_count,
        rows_detected=rows_detected,
        rows_extracted=rows_extracted,
        rows_missing=rows_missing,
        duplicate_rows=duplicate_rows,
        columns_expected=columns_expected,
        columns_extracted=columns_extracted,
        fields_expected=fields_expected,
        fields_extracted=fields_extracted,
        empty_fields=empty_fields,
        quality_issues=quality_issues,
        score=score,
        confidence=confidence,
        status=status,
        issues=issues,
    )
