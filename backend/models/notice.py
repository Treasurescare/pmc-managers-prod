from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict


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
    budget_amount: Optional[float] = None
    required_licenses: List[str] = []
    # Primary tender/RFP/RFQ document (single canonical PDF/DOCX)
    primary_document: Optional[dict] = None  # {file_name, url, content_type, size_bytes}
    attachments: List[dict] = []  # supplementary: BOQ, drawings, addenda, etc.
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    is_published: bool = False
    # EMD (Earnest Money Deposit) config — vendors pay this on bid submission
    emd_config: Optional[dict] = None
    # Wave 7 — optional approval matrix for this tender (falls back to default pipeline)
    approval_matrix_id: Optional[str] = None
    # Wave 7 — tenant assignment (defaults to config.DEFAULT_TENANT_ID)
    tenant_id: Optional[str] = None


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
