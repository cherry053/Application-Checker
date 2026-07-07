from decimal import Decimal

from core.field_parser import (
    parse_application_header,
    parse_currency,
    parse_post_table_fields,
    parse_pre_table_fields,
)
from core.models import ApplicationData

PRE_TABLE_LINES = [
    "I confirm that I have read and understood all information provided above,",
    "including the Essential Public Assets Restoration Program (EPAR) and DRFA",
    "Funding Guidelines. *",
    "☑ Yes",
    "Organisation Name *",
    "MidCoast Council",
    "Primary Address *",
    "57 King Valley Dr",
    "Taree NSW 2430 Australia",
    "Latitude: -31.87525 | Longitude: 152.43125",
    "Postal Address *",
    "57 King Valley Dr",
    "Taree NSW 2430 Australia",
    "Primary Phone Number *",
    "0451 403 825",
    "Must be an Australian phone number.",
    "Other Phone Number",
    "Must be an Australian phone number.",
    "Email Address *",
    "shahneela.ahmed@student.uts.edu.au",
    "Website",
    "Must be a URL.",
    "Primary Contact *",
    "Ms Shahneela Ahmed",
    "Primary Contact Position *",
    "Board Member",
    "Primary Contact Phone Number *",
    "0451 403 825",
    "Primary Contact Email *",
    "shahneela.ahmed@student.uts.edu.au",
    "Does the applicant have an Australian Business Number (ABN)? *",
    "◉ Yes ○ No",
    "ABN *",
    "44 961 208 161",
    "insurance, or is willing to obtain $20 million in public liability insurance? *",
    "◉ Yes",
    "○ No, but willing to obtain",
    "Please provide evidence that the applicant organisation holds Public Liability",
    "Insurance. *",
    "Filename: Public Liability Insurance.pdf",
    "File size: 48.3 kB",
    "Title *",
    "MidCoast Regional Flood Recovery and Infrastructure Reconstruction Program 2026",
    "Must be no more than 25 words.",
    "Brief description *",
    "Reconstruction of flood-damaged roads, bridges, culverts and stormwater infrastructure",
    "across the MidCoast local government area to restore essential public assets and improve",
    "community resilience following severe flooding.",
    "Must be no more than 50 words.",
    "Anticipated start date *",
    "01/11/2026",
    "Anticipated end date *",
    "31/12/2027",
    "Primary location of your initiative *",
    "Taree NSW 2430 Australia",
    "Latitude: -31.9135 | Longitude: 152.46081",
    "Predominant NSW LGA *",
    "Mid-Coast",
    "State Electorate *",
    "Myall Lakes",
    "Federal Electorate *",
    "Division of Lyne",
    "Predominant Asset Type *",
    "◉ Local road/s ○ Culverts ○ Police, fire and emergency",
    "services' stations",
    "Is this a re-damaged asset? *",
    "○ Yes",
    "◉ No",
]

POST_TABLE_LINES = [
    "Number of Damage Items (Line items)",
    "Number of damaged items being restored within the EPAR application *",
    "7",
    "Must be a number.",
    "Total Amount Requested $20,890,000.00",
    "* Represents the total projected cost of the project, encompassing",
    "Has any insurance compensation been claimed or received for any of the",
    "damaged items listed in this EPAR application? *",
    "○ Yes",
    "○ No",
    "I agree * ☐ Yes",
    "Name of authorised Must be a senior staff member, board member or appropriately",
    "person * authorised volunteer",
    "Position *",
    "Position held in applicant organisation (e.g. CEO, Treasurer)",
    "Phone number *",
    "Must be an Australian phone number.",
    "Email *",
    "Must be an email address.",
]


def test_parse_pre_table_fields():
    data = parse_pre_table_fields(PRE_TABLE_LINES, ApplicationData())

    assert data.eligibility_confirmed is True
    assert data.organisation_name == "MidCoast Council"
    assert data.primary_address == "57 King Valley Dr Taree NSW 2430 Australia"
    assert data.postal_address == "57 King Valley Dr Taree NSW 2430 Australia"
    assert data.primary_phone == "0451 403 825"
    assert data.other_phone is None
    assert data.email_address == "shahneela.ahmed@student.uts.edu.au"
    assert data.website is None
    assert data.primary_contact == "Ms Shahneela Ahmed"
    assert data.primary_contact_position == "Board Member"
    assert data.has_abn == "Yes"
    assert data.abn == "44 961 208 161"
    assert data.insurance_answer == "Yes"
    assert data.insurance_evidence_file == "Public Liability Insurance.pdf"
    assert data.title == "MidCoast Regional Flood Recovery and Infrastructure Reconstruction Program 2026"
    assert data.brief_description.startswith("Reconstruction of flood-damaged roads")
    assert data.brief_description.endswith("severe flooding.")
    assert data.start_date == "01/11/2026"
    assert data.end_date == "31/12/2027"
    assert data.primary_initiative_location == "Taree NSW 2430 Australia"
    assert data.predominant_lga == "Mid-Coast"
    assert data.state_electorate == "Myall Lakes"
    assert data.federal_electorate == "Division of Lyne"
    assert data.predominant_asset_type == "Local road/s"
    assert data.re_damaged_answer == "No"


def test_parse_post_table_fields():
    data = parse_post_table_fields(POST_TABLE_LINES, ApplicationData())

    assert data.declared_item_count == 7
    assert data.total_amount_requested == Decimal("20890000.00")
    assert data.insurance_compensation_answer is None
    assert data.declaration_agreed is False
    assert data.authoriser_name is None
    assert data.authoriser_position is None
    assert data.authoriser_phone is None
    assert data.authoriser_email is None


def test_post_table_fields_when_authorisation_completed():
    lines = [
        "Has any insurance compensation been claimed or received for any of the",
        "damaged items listed in this EPAR application? *",
        "○ Yes",
        "◉ No",
        "I agree * ☑ Yes",
        "Name of authorised John Citizen Must be a senior staff member, board member or appropriately",
        "person * authorised volunteer",
        "Position * General Manager",
        "Phone number * 0298765432",
        "Email * john.citizen@council.nsw.gov.au",
    ]
    data = parse_post_table_fields(lines, ApplicationData())

    assert data.insurance_compensation_answer == "No"
    assert data.declaration_agreed is True
    assert data.authoriser_name == "John Citizen"
    assert data.authoriser_position == "General Manager"
    assert data.authoriser_phone == "0298765432"
    assert data.authoriser_email == "john.citizen@council.nsw.gov.au"


def test_parse_currency():
    assert parse_currency("$3,600,000.00") == Decimal("3600000.00")
    assert parse_currency("$0.50") == Decimal("0.50")
    assert parse_currency("not money") is None


def test_parse_application_header():
    pages = [
        [
            "TEST - UTS Project",
            "Essential Public Asset Restoration (EPAR) - Application Form",
            "Application No. UTS00018-TEST From Shahneela Ahmed - DRAFT",
            "Grant Program Information (EPAR)",
        ]
    ]
    meta = parse_application_header(pages)
    assert meta["application_id"] == "UTS00018-TEST"
    assert meta["applicant_name"] == "Shahneela Ahmed"
