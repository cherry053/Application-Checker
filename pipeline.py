from core.field_parser import parse_fields
from core.models import CheckResult
from core.pdf_extract import extract_lines
from core.validators import run_checks


def check_application(uploaded_file) -> CheckResult:
    """Run a SmartyGrants PDF export through extraction, field parsing, and validation."""
    lines = extract_lines(uploaded_file)
    data = parse_fields(lines)
    return run_checks(data)
