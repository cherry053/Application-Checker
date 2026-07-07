from core.models import ApplicationData

PRIMARY_ADDRESS_LABEL = "Primary Address *"
POSTAL_ADDRESS_LABEL = "Postal Address *"
EMAIL_ADDRESS_LABEL = "Email Address *"
PRIMARY_CONTACT_EMAIL_LABEL = "Primary Contact Email *"
START_DATE_LABEL = "Anticipated start date *"
END_DATE_LABEL = "Anticipated end date *"
PRIMARY_INITIATIVE_LOCATION_LABEL = "Primary location of your initiative *"
AUTHORISER_EMAIL_LABEL = "by the applicant organisation"


def _value_after(lines: list[str], index: int, span: int = 1) -> str:
    """Join the `span` line(s) following `index` into one value string."""
    return " ".join(lines[index + 1 : index + 1 + span]).strip()


def parse_fields(lines: list[str]) -> ApplicationData:
    """Find each labelled field in the extracted PDF lines and return it as structured data.

    SmartyGrants PDF exports put the field label on its own line, with the
    answer on the line(s) immediately after it.
    """
    data = ApplicationData()

    for i, line in enumerate(lines):
        if PRIMARY_ADDRESS_LABEL in line:
            data.primary_address = _value_after(lines, i, span=2)
        elif POSTAL_ADDRESS_LABEL in line:
            data.postal_address = _value_after(lines, i, span=2)
        elif EMAIL_ADDRESS_LABEL in line:
            data.email_address = _value_after(lines, i)
        elif PRIMARY_CONTACT_EMAIL_LABEL in line:
            data.primary_contact_email = _value_after(lines, i)
        elif START_DATE_LABEL in line:
            data.start_date = _value_after(lines, i)
        elif END_DATE_LABEL in line:
            data.end_date = _value_after(lines, i)
        elif PRIMARY_INITIATIVE_LOCATION_LABEL in line:
            data.primary_initiative_location = _value_after(lines, i, span=2)
        elif AUTHORISER_EMAIL_LABEL in line:
            data.authoriser_email = _value_after(lines, i)

    return data
