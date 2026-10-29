from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator, field_validator


DocumentType = Literal["tender", "rfp", "rfq"]


class NoticeIn(BaseModel):
    """Admin creates or publishes a tender notice."""
    model_config = ConfigDict(extra="allow")

    title: str = Field(min_length=3)
    description: str = Field(min_length=10)
    document_type: DocumentType = "tender"
    category: str
    delivery_country: str = "KZ"
    submission_deadline: str
    pre_bid_meeting_date: Optional[str] = None
    budget_currency: str = "USD"
    # Bug #16 fix — reject negative budget amounts server-side
    budget_amount: Optional[float] = Field(default=None, ge=0)
    required_licenses: List[str] = []
    # Primary tender/RFP/RFQ document (single canonical PDF/DOCX)
    primary_document: Optional[dict] = None  # {file_name, url, content_type, size_bytes}
    attachments: List[dict] = []  # supplementary: BOQ, drawings, addenda, etc.
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None

    # v51aa — coerce empty-string contact_email ("" from the admin form when the
    # tester cleared the field) to None, so an optional email behaves like an
    # optional email. Previously the pydantic EmailStr validator rejected ""
    # with HTTP 422 "value is not a valid email address: An email address must
    # have an @-sign." — which users saw when submitting a notice for approval.
    @field_validator("contact_email", mode="before")
    @classmethod
    def _blank_email_is_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
    is_published: bool = False
    # v51an — admin can pin a specific joint escrow account to this notice so
    # the auto-ledger routes vendor EMD receipts there. If None, the newest
    # active account is used by escrow.auto_init_from_emd_payment().
    escrow_account_id: Optional[str] = None
    # EMD (Earnest Money Deposit) config — vendors pay this on bid submission
    emd_config: Optional[dict] = None
    # Who collects the EMD: pmc | escrow | escrow_institution | tender_caller | authorised_party
    emd_collector: Optional[dict] = None
    # Wave 7 — optional approval matrix for this tender (falls back to default pipeline)
    approval_matrix_id: Optional[str] = None
    # Wave 7 — tenant assignment (defaults to config.DEFAULT_TENANT_ID)
    tenant_id: Optional[str] = None
    # Wave 28 — optional link to a Tender Builder template. When set, the public
    # Notice detail exposes a "Download composed tender PDF" button that renders
    # the template via WeasyPrint.
    tender_template_id: Optional[str] = None

    @model_validator(mode="after")
    def _no_negative_amounts(self):
        """v49k — reject negative money anywhere in the payload.

        budget_amount is typed with ge=0, but extra="allow" lets fields like
        tender_fee and emd_config pass through unvalidated. Sweep every
        numeric field whose name mentions amount/fee/emd/value/price and
        refuse negatives so a tender can never be created with -$3,000 etc.
        """
        def check(name: str, val):
            if isinstance(val, (int, float)) and val < 0:
                raise ValueError(f"{name} cannot be negative")
            if isinstance(val, dict):
                for k, v in val.items():
                    check(f"{name}.{k}", v)

        check("budget_amount", self.budget_amount)
        for fname in ("tender_fee",):
            check(fname, getattr(self, fname, None))
        check("emd_config", self.emd_config)
        # extras accepted via extra="allow"
        for k, v in (self.model_extra or {}).items():
            if any(t in k.lower() for t in ("amount", "fee", "emd", "price", "value")):
                check(k, v)
        return self


class NoticePatchIn(BaseModel):
    """Partial update for PATCH /notices/{ref}. Every field optional; the
    handler uses model_dump(exclude_unset=True) so only keys actually sent
    are $set. Fixes the HTTP 422 the Escrow routing picker hit when it
    PATCHed just `escrow_account_id` (the handler reused the full NoticeIn)."""
    model_config = ConfigDict(extra="allow")

    title: Optional[str] = Field(default=None, min_length=3)
    description: Optional[str] = Field(default=None, min_length=10)
    document_type: Optional[DocumentType] = None
    category: Optional[str] = None
    delivery_country: Optional[str] = None
    submission_deadline: Optional[str] = None
    pre_bid_meeting_date: Optional[str] = None
    budget_currency: Optional[str] = None
    budget_amount: Optional[float] = Field(default=None, ge=0)
    required_licenses: Optional[List[str]] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    is_published: Optional[bool] = None
    escrow_account_id: Optional[str] = None
    emd_config: Optional[dict] = None
    # Who collects the EMD: pmc | escrow | escrow_institution | tender_caller | authorised_party
    emd_collector: Optional[dict] = None
    approval_matrix_id: Optional[str] = None
    tender_template_id: Optional[str] = None

    @field_validator("contact_email", mode="before")
    @classmethod
    def _blank_email_is_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @model_validator(mode="after")
    def _no_negative_amounts(self):
        """Same negative-money sweep as NoticeIn, applied to sent keys only."""
        def check(name: str, val):
            if isinstance(val, (int, float)) and val < 0:
                raise ValueError(f"{name} cannot be negative")
            if isinstance(val, dict):
                for k, v in val.items():
                    check(f"{name}.{k}", v)

        check("budget_amount", self.budget_amount)
        for fname in ("tender_fee",):
            check(fname, getattr(self, fname, None))
        check("emd_config", self.emd_config)
        for k, v in (self.model_extra or {}).items():
            if any(t in k.lower() for t in ("amount", "fee", "emd", "price", "value")):
                check(k, v)
        return self


class NoticePublic(BaseModel):
    """Public shape — safe to serve without authentication."""
    id: str
    notice_ref: str
    title: str
    description: str
    document_type: DocumentType
    category: str
    delivery_country: str
    submission_deadline: str
    pre_bid_meeting_date: Optional[str] = None
    budget_currency: str
    budget_amount: Optional[float] = None
    required_licenses: List[str] = []
    attachments: List[dict] = []
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    published_at: Optional[str] = None
    created_at: str


class Notice(NoticePublic):
    """Internal view — includes tenant/audit fields."""
    is_published: bool
    tenant_id: str
    created_by: Optional[str] = None
