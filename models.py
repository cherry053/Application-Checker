from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ApplicationData:
    primary_address: Optional[str] = None
    postal_address: Optional[str] = None
    email_address: Optional[str] = None
    primary_contact_email: Optional[str] = None
    authoriser_email: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    primary_initiative_location: Optional[str] = None


@dataclass
class CriterionResult:
    name: str
    passed: bool
    severity: Literal["critical", "warning"]
    detail: str


@dataclass
class CheckResult:
    overall_status: Literal["PASS", "FAIL", "PARTIAL"]
    confidence_score: int
    criteria: list[CriterionResult] = field(default_factory=list)
