"""Pure filtering logic for the processed-applications results view.

Free of Streamlit imports so it can be unit-tested directly.
"""

from core.models import UNKNOWN_APPLICATION_ID, ApplicationResult

VALID_STATUSES: tuple[str, ...] = ("Pass", "Fail", "Review")


def upsert_application(
    applications: list[ApplicationResult], new: ApplicationResult
) -> list[ApplicationResult]:
    """Insert `new`, replacing any existing entry with the same application ID.

    Re-checking an application updates its row instead of duplicating it.
    Results without a recognisable ID are always appended, since two
    unidentified applications cannot be told apart. The list is modified in
    place (it lives in session state) and returned for convenience.
    """
    if new.application_id != UNKNOWN_APPLICATION_ID:
        for index, existing in enumerate(applications):
            if existing.application_id == new.application_id:
                applications[index] = new
                return applications
    applications.append(new)
    return applications


def filter_applications(
    applications: list[ApplicationResult],
    statuses: set[str],
    search_term: str,
) -> list[ApplicationResult]:
    """Return the applications whose status is in `statuses` and that match `search_term`.

    Both conditions must hold (AND logic). The search term is matched
    case-insensitively as a substring of the application ID or the applicant
    name; an empty or whitespace-only term matches every application.
    """
    term = search_term.strip().casefold()
    return [
        application
        for application in applications
        if application.status in statuses and _matches_search(application, term)
    ]


def status_counts(applications: list[ApplicationResult]) -> dict[str, int]:
    """Count applications per status, with a zero entry for every valid status."""
    counts: dict[str, int] = {status: 0 for status in VALID_STATUSES}
    for application in applications:
        counts[application.status] = counts.get(application.status, 0) + 1
    return counts


def _matches_search(application: ApplicationResult, term: str) -> bool:
    if not term:
        return True
    return (
        term in (application.application_id or "").casefold()
        or term in (application.applicant_name or "").casefold()
    )
