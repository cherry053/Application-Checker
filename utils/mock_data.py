MOCK_RESULT = {

    "application_id": "UTS00001",
    "applicant_name": "Hawkesbury City Council",
    "agrn": "AGRN 1045",
    "scanned_at": "15 Jun 2026, 11:42 AM",
    "overall_status": "PARTIAL",
    "confidence_score": 73,
    "estimated_cost": 240000,
    "damage_items": 4,
    "criteria": [
        {
            "name": "Organisation Name Provided",
            "passed": True,
            "severity": "critical",
            "detail": "Organisation name 'Hawkesbury City Council' provided."
        },
        {
            "name": "Primary Address Within NSW",
            "passed": True,
            "severity": "critical",
            "detail": "Primary address '1 Dight Street, Windsor NSW 2756' is in NSW."
        },
        {
            "name": "Email Address Valid",
            "passed": True,
            "severity": "critical",
            "detail": "'council@hawkesbury.nsw.gov.au' looks like a valid email."
        },
        {
            "name": "Primary Contact Email Valid",
            "passed": False,
            "severity": "critical",
            "detail": "'john.smith@council..nsw.gov.au' does not look like a valid email address."
        },
        {
            "name": "Start Date Before End Date",
            "passed": True,
            "severity": "critical",
            "detail": "2024-01-15 to 2024-06-30 is a valid range."
        },
        {
            "name": "Public Liability Insurance Held or Obtainable",
            "passed": True,
            "severity": "critical",
            "detail": "Insurance answer: 'Yes'."
        },
        {
            "name": "Predominant Asset Type Selected",
            "passed": True,
            "severity": "critical",
            "detail": "Selected: 'Road'."
        },
        {
            "name": "Declaration Agreed",
            "passed": True,
            "severity": "critical",
            "detail": "Declaration answer: 'Yes'."
        },
        {
            "name": "Declaration Authoriser Details Present",
            "passed": False,
            "severity": "critical",
            "detail": "Missing declaration field(s): phone, email."
        },
        {
            "name": "Damage Item Count Reconciles",
            "passed": True,
            "severity": "warning",
            "detail": "PDF declares 4 damage item(s); CSV yielded 4."
        },
        {
            "name": "Total Amount Requested Reconciles",
            "passed": False,
            "severity": "warning",
            "detail": "Mismatch: PDF declares $240,000.00 but CSV items sum to $218,500.00."
        }
    ]
}