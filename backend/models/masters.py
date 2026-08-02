"""Master data models: Company, Role, Hierarchy, Approval Matrix."""
from typing import List, Optional
from pydantic import BaseModel


class CompanyIn(BaseModel):
    name: str
    code: str
    country: str = "KZ"
    address: Optional[str] = None
    parent_id: Optional[str] = None  # for branches
    is_active: bool = True


class RoleIn(BaseModel):
    """Role master — extends the built-in StaffRole enum with tenant-specific roles."""
    code: str
    label: str
    description: Optional[str] = None
    permissions: List[str] = []  # ["bid.read", "bid.approve", "committee.close", ...]


class ApprovalStepIn(BaseModel):
    order: int
    role_code: str  # matches Role.code
    action_label: str  # "Escrow acceptance", "Certifier review", ...
    sla_hours: int = 48
    required: bool = True


class ApprovalMatrixIn(BaseModel):
    name: str
    applies_to: str = "bid"  # "bid" | "notice" | "contract"
    tender_value_min: float = 0.0
    tender_value_max: Optional[float] = None
    country: Optional[str] = None
    steps: List[ApprovalStepIn]
    is_active: bool = True
