from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class CPVCode(BaseModel):
    code: str
    description: str
    category: str

    @field_validator("code")
    @classmethod
    def validate_cpv_code(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 8:
            raise ValueError("CPV code must be exactly 8 digits")
        return v


class Supplier(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    tax_id: str
    contact_email: str
    certifications: list[str] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 9:
            raise ValueError("ΑΦΜ must be exactly 9 digits")
        return v


class EvaluationCriteria(BaseModel):
    criterion_name: str
    weight: float
    scoring_method: Literal["price", "quality", "technical", "combined"]

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("weight must be between 0 and 1")
        return v


class BudgetAllocation(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    total_amount: Decimal
    currency: str = "EUR"
    fiscal_year: int
    kae: str

    @field_serializer("total_amount")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class ComplianceCheck(BaseModel):
    check_type: str
    passed: bool
    legal_reference: str
    notes: Optional[str] = None


class RiskAssessment(BaseModel):
    risk_level: Literal["low", "medium", "high", "critical"]
    risk_factors: list[str]
    mitigation: Optional[str] = None
    score: float

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        if not 0.0 <= v <= 10.0:
            raise ValueError("score must be between 0 and 10")
        return v


class ApprovalStage(BaseModel):
    stage_name: str
    approver_role: str
    status: Literal["pending", "approved", "rejected", "skipped"]
    decision_at: Optional[datetime] = None
    comments: Optional[str] = None


class Tender(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    cpv_codes: list[CPVCode]
    budget: BudgetAllocation
    deadline: datetime
    evaluation_criteria: list[EvaluationCriteria]
    compliance_checks: list[ComplianceCheck]
    status: Literal["draft", "published", "closed", "awarded", "cancelled"]


class Contract(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    tender_id: str
    supplier: Supplier
    signed_at: Optional[datetime] = None
    value: Decimal
    duration_months: int
    status: Literal["draft", "active", "expired", "terminated"]

    @field_serializer("value")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class ProcurementRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    requester_id: str
    budget: BudgetAllocation
    justification: str
    risk_assessment: Optional[RiskAssessment] = None
    approval_stages: list[ApprovalStage]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: Literal["draft", "in_review", "approved", "rejected"]
