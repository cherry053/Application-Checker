from datetime import datetime

from core.models import ApplicationData, CheckResult, CriterionResult

DATE_FORMAT = "%d/%m/%Y"


def _missing(name: str) -> CriterionResult:
    return CriterionResult(name=name, passed=False, severity="critical", detail="Field not found in application.")


def check_primary_address_in_nsw(data: ApplicationData) -> CriterionResult:
    value = data.primary_address
    if value is None:
        return _missing("Primary Address Within NSW")
    passed = "NSW" in value
    detail = f"Primary address '{value}' is in NSW." if passed else f"Primary address '{value}' is not in NSW."
    return CriterionResult("Primary Address Within NSW", passed, "critical", detail)


def check_postal_address_in_nsw(data: ApplicationData) -> CriterionResult:
    value = data.postal_address
    if value is None:
        return _missing("Postal Address Within NSW")
    passed = "NSW" in value
    detail = f"Postal address '{value}' is in NSW." if passed else f"Postal address '{value}' is not in NSW."
    return CriterionResult("Postal Address Within NSW", passed, "critical", detail)


def check_primary_initiative_location_in_nsw(data: ApplicationData) -> CriterionResult:
    value = data.primary_initiative_location
    if value is None:
        return _missing("Primary Initiative Location Within NSW")
    passed = "NSW" in value
    detail = (
        f"Initiative location '{value}' is in NSW." if passed else f"Initiative location '{value}' is not in NSW."
    )
    return CriterionResult("Primary Initiative Location Within NSW", passed, "critical", detail)


def check_email_address_valid(data: ApplicationData) -> CriterionResult:
    value = data.email_address
    if value is None:
        return _missing("Email Address Valid")
    passed = "@" in value
    detail = f"Email '{value}' looks valid." if passed else f"Email '{value}' is missing an '@'."
    return CriterionResult("Email Address Valid", passed, "critical", detail)


def check_primary_contact_email_valid(data: ApplicationData) -> CriterionResult:
    value = data.primary_contact_email
    if value is None:
        return _missing("Primary Contact Email Valid")
    passed = "@" in value
    detail = f"Email '{value}' looks valid." if passed else f"Email '{value}' is missing an '@'."
    return CriterionResult("Primary Contact Email Valid", passed, "critical", detail)


def check_authoriser_email_valid(data: ApplicationData) -> CriterionResult:
    value = data.authoriser_email
    if value is None:
        return _missing("Authoriser Email Valid")
    passed = "@" in value
    detail = f"Email '{value}' looks valid." if passed else f"Email '{value}' is missing an '@'."
    return CriterionResult("Authoriser Email Valid", passed, "critical", detail)


def check_date_range_valid(data: ApplicationData) -> CriterionResult:
    name = "Start Date Before End Date"
    if not data.start_date or not data.end_date:
        return CriterionResult(name, False, "critical", "Missing start date or end date.")

    try:
        start = datetime.strptime(data.start_date, DATE_FORMAT).date()
        end = datetime.strptime(data.end_date, DATE_FORMAT).date()
    except ValueError:
        return CriterionResult(
            name, False, "critical", f"Could not parse dates '{data.start_date}' / '{data.end_date}'."
        )

    passed = start <= end
    detail = f"{start} to {end} is a valid range." if passed else f"Start date {start} is after end date {end}."
    return CriterionResult(name, passed, "critical", detail)


def run_checks(data: ApplicationData) -> CheckResult:
    criteria = [
        check_primary_address_in_nsw(data),
        check_postal_address_in_nsw(data),
        check_primary_initiative_location_in_nsw(data),
        check_email_address_valid(data),
        check_primary_contact_email_valid(data),
        check_authoriser_email_valid(data),
        check_date_range_valid(data),
    ]

    passed_count = sum(1 for c in criteria if c.passed)
    confidence_score = round(100 * passed_count / len(criteria))

    if passed_count == len(criteria):
        overall_status = "PASS"
    elif passed_count == 0:
        overall_status = "FAIL"
    else:
        overall_status = "PARTIAL"

    return CheckResult(overall_status=overall_status, confidence_score=confidence_score, criteria=criteria)
