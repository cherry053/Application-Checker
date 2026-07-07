from datetime import datetime

from core.damage_table_parser import parse_damage_table
from core.field_parser import parse_application_header, parse_post_table_fields, parse_pre_table_fields
from core.models import ApplicationData, CheckResult
from core.pdf_extract import clean_lines, extract_pages
from core.section_splitter import split_sections
from core.validators import run_checks


def check_application(pdf_file, damage_table_text: str) -> CheckResult:
    """Run a SmartyGrants PDF export plus its pasted damage-table text through all checks.

    The PDF is parsed up to the damage table and again after it; the table
    itself (which does not survive PDF text extraction) is read from
    `damage_table_text`, the table copied out of the web form as plain text.
    """
    pages = extract_pages(pdf_file)
    meta = parse_application_header(pages)
    pre_lines, post_lines = split_sections(clean_lines(pages))

    data = ApplicationData()
    parse_pre_table_fields(pre_lines, data)
    parse_post_table_fields(post_lines, data)

    items, table_warnings = parse_damage_table(damage_table_text)

    result = run_checks(data, items, table_warnings)
    result.application_id = meta.get("application_id")
    result.applicant_name = data.organisation_name or meta.get("applicant_name")
    result.scanned_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    result.total_requested = data.total_amount_requested
    return result
