"""Bid & EMD models — Wave 1 core."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

BidStatus = Literal[
    "draft", "submitted", "emd_pending", "emd_paid",
    "escrow_accepted", "admin_flagged", "certifier_review", "certifier_cleared",
    "legal_review", "legal_cleared", "accounting_review", "accounting_cleared",
    "committee_review", "awarded", "rejected", "withdrawn", "closed",
]


class BidDocument(BaseModel):
    kind: Literal["technical", "commercial", "supporting"]
    key: str
    filename: str
    size_bytes: int
    uploaded_at: str


class BidCreateIn(BaseModel):
    notice_ref: str
    price_amount: float = Field(ge=0)
    price_currency: str = "USD"
    technical_notes: Optional[str] = None
    commercial_notes: Optional[str] = None
    documents: List[BidDocument] = []


class BidUpdateIn(BaseModel):
    price_amount: Optional[float] = None
    technical_notes: Optional[str] = None
    commercial_notes: Optional[str] = None
    documents: Optional[List[BidDocument]] = None


class BidDecisionIn(BaseModel):
    action: Literal["accept", "reject", "flag", "clear", "award"]
    role: Literal["escrow_agent", "certifier", "legal_counsel", "accounting", "admin", "committee"]
    notes: Optional[str] = None
