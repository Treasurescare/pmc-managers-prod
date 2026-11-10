"""Staff user model — multi-role capable.

A single staff record can hold any combination of the enterprise roles below.
At login the user picks which role to act as; the JWT carries the active role.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, EmailStr, Field


StaffRole = Literal[
    "admin", "reviewer",
    "escrow_agent", "certifier", "legal_counsel", "accounting",
    "committee_member", "auditor", "support",
    "management", "partner", "agent", "buyer",
]

ALL_STAFF_ROLES: List[str] = [
    "admin", "reviewer",
    "escrow_agent", "certifier", "legal_counsel", "accounting",
    "committee_member", "auditor", "support",
    "management", "partner", "agent",
]


class StaffLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    active_role: StaffRole
    otp_code: Optional[str] = None  # required when the user has mfa_enabled


class StaffCreateIn(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)
    roles: List[StaffRole]
    hierarchy_level: int = 1
    company_id: Optional[str] = None
    reports_to: Optional[str] = None  # staff_id of manager
    designation: Optional[str] = None  # e.g. "Chief Procurement Officer"
    # v53k — flag that this staff member can co-sign EMD escrow releases
    # on behalf of PMC. Only staff with this flag appear in the "PMC
    # officer" dropdown when creating a joint escrow account.
    is_escrow_signatory: bool = False
    # v55 — portal type. "admin" accounts sign in via the Administrator login
    # and reach the admin console; "staff" accounts sign in via the staff login
    # and only ever reach the /staff specialist dashboard. A "staff" account may
    # NOT hold the admin/reviewer roles (enforced server-side on create/update).
    account_type: Literal["admin", "staff"] = "staff"
    # v55 — country scope for work distribution. None/[] = all countries
    # (global); otherwise a list of ISO country codes this staff member covers.
    country_scope: Optional[List[str]] = None


class StaffUpdateIn(BaseModel):
    name: Optional[str] = None
    roles: Optional[List[StaffRole]] = None
    hierarchy_level: Optional[int] = None
    reports_to: Optional[str] = None
    designation: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)
    is_escrow_signatory: Optional[bool] = None
    account_type: Optional[Literal["admin", "staff"]] = None
    company_id: Optional[str] = None
    country_scope: Optional[List[str]] = None


class StaffPublic(BaseModel):
    id: str
    email: str
    name: str
    roles: List[str]
    active_role: Optional[str] = None
    hierarchy_level: int = 1
    company_id: Optional[str] = None
    country_scope: Optional[List[str]] = None
    reports_to: Optional[str] = None
    is_active: bool = True
