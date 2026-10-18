"""Master data models: Company, Role, Hierarchy, Approval Matrix."""
from typing import List, Optional
from pydantic import BaseModel


class CompanyIn(BaseModel):
    """v56 — full company profile. Documents + licenses are managed through
    the dedicated company-document endpoints, NOT this payload, so saving the
    profile never wipes uploaded files."""
    name: str
    code: str
    country: str = "KZ"              # ISO-2 code
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    address: Optional[str] = None
    reg_number: Optional[str] = None       # incorporation / registration no.
    incorporation_date: Optional[str] = None  # ISO date
    tax_id: Optional[str] = None
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
    # v50h — pin a specific person for this step. When null, the step is
    # pool-routed to anyone with the role. When set, only that user can
    # approve; email is kept for notifications even if the admin_user_id
    # is later removed.
    assignee_user_id: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_name: Optional[str] = None


class ApprovalMatrixIn(BaseModel):
    name: str
    applies_to: str = "bid"  # "bid" | "notice" | "contract"
    tender_value_min: float = 0.0
    tender_value_max: Optional[float] = None
    country: Optional[str] = None
    steps: List[ApprovalStepIn]
    is_active: bool = True
