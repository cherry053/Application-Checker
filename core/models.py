from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional

UNKNOWN_APPLICATION_ID = "Unknown ID"
UNKNOWN_APPLICANT_NAME = "Unknown applicant"


@dataclass
class ApplicationData:
    """Application-level fields parsed from the PDF (everything outside the damage table)."""

    # Eligibility
    eligibility_confirmed: Optional[bool] = None

    # Organisation details
    organisation_name: Optional[str] = None
    primary_address: Optional[str] = None
    postal_address: Optional[str] = None
    primary_phone: Optional[str] = None
    other_phone: Optional[str] = None
    email_address: Optional[str] = None
    website: Optional[str] = None

    # Primary contact
    primary_contact: Optional[str] = None
    primary_contact_position: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    primary_contact_email: Optional[str] = None

    # ABN
    has_abn: Optional[str] = None
    abn: Optional[str] = None

    # Public liability insurance
    insurance_answer: Optional[str] = None
    insurance_evidence_file: Optional[str] = None

    # Project details
    title: Optional[str] = None
    brief_description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    primary_initiative_location: Optional[str] = None
    predominant_lga: Optional[str] = None
    state_electorate: Optional[str] = None
    federal_electorate: Optional[str] = None
    predominant_asset_type: Optional[str] = None
    re_damaged_answer: Optional[str] = None

    # Post-table: totals and reconciliation
    declared_item_count: Optional[int] = None
    total_amount_requested: Optional[Decimal] = None
    insurance_compensation_answer: Optional[str] = None

    # Declaration and authorisation
    declaration_agreed: Optional[bool] = None
    authoriser_name: Optional[str] = None
    authoriser_position: Optional[str] = None
    authoriser_phone: Optional[str] = None
    authoriser_email: Optional[str] = None


@dataclass
class DamageItem:
    """One damage line item parsed from the pasted damage-table text export."""

    asset_category: Optional[str] = None
    damage_item_id: Optional[str] = None
    asset_id: Optional[str] = None
    asset_name: Optional[str] = None
    date_accessible: Optional[str] = None

    location_start: Optional[str] = None
    location_end: Optional[str] = None

    chainage_focal: Optional[float] = None
    chainage_from: Optional[float] = None
    chainage_to: Optional[float] = None
    longitude_from: Optional[float] = None
    latitude_from: Optional[float] = None
    longitude_to: Optional[float] = None
    latitude_to: Optional[float] = None

    sub_category: Optional[str] = None
    classification_type: Optional[str] = None
    capacity: Optional[str] = None
    layout: Optional[str] = None
    dimensions: Optional[str] = None
    material: Optional[str] = None
    same_pre_disaster_function: Optional[str] = None
    deviation_reason: Optional[str] = None

    pre_disaster_evidence_file: Optional[str] = None
    pre_disaster_evidence_bytes: Optional[int] = None
    damage_evidence_file: Optional[str] = None
    damage_evidence_bytes: Optional[int] = None

    damage_description: Optional[str] = None
    estimation_method: Optional[str] = None

    cost_construction: Optional[Decimal] = None
    cost_pm_design: Optional[Decimal] = None
    cost_contingency: Optional[Decimal] = None
    cost_escalation: Optional[Decimal] = None
    cost_total: Optional[Decimal] = None

    cost_evidence_file: Optional[str] = None
    cost_evidence_bytes: Optional[int] = None
    methodology: Optional[str] = None

    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class CriterionResult:
    name: str
    passed: bool
    severity: Literal["critical", "warning"]
    detail: str
    section: str = ""


@dataclass
class CompletenessIssue:
    """One finding raised while validating table extraction completeness."""

    severity: Literal["info", "warning", "critical"]
    message: str


@dataclass
class CompletenessReport:
    """Outcome of the Table Completeness Check for one application.

    Compares the pasted damage-table text (source), the parsed damage items
    (extraction), and the count the PDF declares, then scores how completely
    the source data made it into the application.
    """

    rows_declared: Optional[int]  # count the PDF declares; None when absent
    rows_detected: int  # records found in the pasted table text
    rows_extracted: int  # damage items actually parsed
    rows_missing: int
    duplicate_rows: int
    columns_expected: int
    columns_extracted: int  # columns with at least one extracted value
    fields_expected: int
    fields_extracted: int
    empty_fields: int
    quality_issues: int  # truncation/OCR/encoding findings
    score: int  # overall completeness, 0-100
    confidence: int  # how trustworthy this assessment is, 0-100
    status: Literal["complete", "review", "incomplete"]
    issues: list[CompletenessIssue] = field(default_factory=list)

    @property
    def confidence_label(self) -> str:
        if self.confidence >= 80:
            return "High"
        if self.confidence >= 55:
            return "Medium"
        return "Low"

    @property
    def manual_review_recommended(self) -> bool:
        return self.status != "complete" or self.confidence < 80


@dataclass
class CheckResult:
    overall_status: Literal["PASS", "FAIL", "PARTIAL"]
    confidence_score: int
    criteria: list[CriterionResult] = field(default_factory=list)
    damage_items: list[DamageItem] = field(default_factory=list)

    # Header metadata for the results page
    application_id: Optional[str] = None
    applicant_name: Optional[str] = None
    scanned_at: Optional[str] = None
    total_requested: Optional[Decimal] = None

    # Table Completeness Check outcome; None for results created before the
    # check existed (e.g. entries restored from an older session).
    completeness: Optional[CompletenessReport] = None


@dataclass
class ApplicationResult:
    """One processed application as it appears in the results list."""

    application_id: str
    applicant_name: str
    status: str  # "Pass", "Fail" or "Review"
    scanned_at: Optional[str] = None
    check: Optional[CheckResult] = None

    @classmethod
    def from_check(cls, check: CheckResult) -> "ApplicationResult":
        status_map = {"PASS": "Pass", "FAIL": "Fail", "PARTIAL": "Review"}
        return cls(
            application_id=check.application_id or UNKNOWN_APPLICATION_ID,
            applicant_name=check.applicant_name or UNKNOWN_APPLICANT_NAME,
            status=status_map.get(check.overall_status, "Review"),
            scanned_at=check.scanned_at,
            check=check,
        )
