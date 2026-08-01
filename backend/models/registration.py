from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict


RegistrationStatus = Literal["draft", "submitted", "under_review", "approved", "rejected", "needs_clarification"]
DecisionAction = Literal["approve", "reject", "clarify"]


class RegistrationDraftIn(BaseModel):
    """Initial draft creation — only email required, everything else optional."""
    email: EmailStr
    company_name: Optional[str] = None
    country: str = "KZ"


class RegistrationUpdateIn(BaseModel):
    """Progressive save while filling Sections A–E. All fields optional."""
    model_config = ConfigDict(extra="allow")

    # A — Identity
    company_name: Optional[str] = None
    trade_name: Optional[str] = None
    registered_address: Optional[str] = None
    mailing_address: Optional[str] = None
    country: Optional[str] = None
    country_id_label: Optional[str] = None
    registration_number: Optional[str] = None
    incorporation_date: Optional[str] = None
    tax_id: Optional[str] = None
    legal_entity_type: Optional[str] = None
    website: Optional[str] = None
    employees_count: Optional[int] = None

    # B — Contact & Signatory
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_office_phone: Optional[str] = None
    contact_mobile: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    signatory_name: Optional[str] = None
    signatory_title: Optional[str] = None
    signatory_contact: Optional[str] = None

    # C — Banking & Financial
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_swift: Optional[str] = None
    bank_address: Optional[str] = None
    turnover_year1: Optional[float] = None
    turnover_year2: Optional[float] = None
    turnover_year3: Optional[float] = None
    turnover_currency: Optional[str] = "USD"

    # D — Business Profile
    primary_sector: Optional[str] = None
    business_description: Optional[str] = None
    operating_regions: List[str] = []
    business_categories: List[str] = []
    previous_projects: List[dict] = []
    references: List[dict] = []
    iso_certifications: Optional[str] = None
    licenses_permits: Optional[str] = None
    insurance_details: Optional[str] = None
    litigation_history: Optional[str] = None
    kz_licenses: List[str] = []

    # E — Documents & Declarations
    documents: List[dict] = []
    decl_conflict_of_interest: Optional[bool] = None
    decl_integrity: Optional[bool] = None
    decl_accuracy: Optional[bool] = None
    decl_data_consent: Optional[bool] = None
    decl_fee: Optional[bool] = None
    decl_notification: Optional[bool] = None
    signature_name: Optional[str] = None
    signature_title: Optional[str] = None
    signature_date: Optional[str] = None


class RegistrationDecisionIn(BaseModel):
    action: DecisionAction
    notes: Optional[str] = None


class Registration(BaseModel):
    id: str
    email: str
    company_name: Optional[str] = None
    status: RegistrationStatus
    tenant_id: str
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewer_notes: Optional[str] = None
    vendor_ref: Optional[str] = None  # populated on approve
    created_at: str
