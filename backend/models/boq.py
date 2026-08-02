"""Wave 3 — BOQ (Bill of Quantities) & Contract Management."""
from typing import Optional, List
from pydantic import BaseModel, Field


class BOQItemIn(BaseModel):
    sl_no: int
    description: str
    unit: str = "nos"
    quantity: float = 0
    unit_rate: float = 0
    remarks: Optional[str] = None


class BOQTemplateIn(BaseModel):
    name: str
    notice_ref: Optional[str] = None  # optional — link to a tender
    currency: str = "USD"
    items: List[BOQItemIn] = []


class BOQVendorSubmissionIn(BaseModel):
    """Vendor submits priced BOQ against a template."""
    template_id: str
    bid_id: str
    prices: List[dict]  # [{sl_no, unit_rate}]
    notes: Optional[str] = None


class ContractMilestoneIn(BaseModel):
    order: int
    title: str
    amount: float
    due_date: str  # ISO date
    status: str = "pending"  # pending | in_progress | completed | delayed


class ContractIn(BaseModel):
    notice_ref: str
    bid_id: str
    vendor_id: str
    contract_ref: Optional[str] = None
    title: str
    value: float
    currency: str = "USD"
    start_date: str
    end_date: str
    milestones: List[ContractMilestoneIn] = []
    obligations: List[str] = []


class VariationOrderIn(BaseModel):
    contract_id: str
    reason: str
    amount_delta: float  # + / -
    approved_by: Optional[str] = None
