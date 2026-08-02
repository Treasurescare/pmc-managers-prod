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
]

ALL_STAFF_ROLES: List[str] = [
    "admin", "reviewer",
    "escrow_agent", "certifier", "legal_counsel", "accounting",
    "committee_member", "auditor", "support",
]


class StaffLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    active_role: StaffRole


class StaffCreateIn(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)
    roles: List[StaffRole]
    hierarchy_level: int = 1
    company_id: Optional[str] = None
    reports_to: Optional[str] = None  # staff_id of manager


class StaffUpdateIn(BaseModel):
    name: Optional[str] = None
    roles: Optional[List[StaffRole]] = None
    hierarchy_level: Optional[int] = None
    reports_to: Optional[str] = None
    is_active: Optional[bool] = None


class StaffPublic(BaseModel):
    id: str
    email: str
    name: str
    roles: List[str]
    active_role: Optional[str] = None
    hierarchy_level: int = 1
    company_id: Optional[str] = None
    reports_to: Optional[str] = None
    is_active: bool = True
