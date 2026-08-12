from typing import Optional, Literal, List
from pydantic import BaseModel, EmailStr, Field


AdminRole = Literal[
    "admin", "reviewer",
    "escrow_agent", "certifier", "legal_counsel", "accounting",
    "committee_member", "auditor", "support",
]


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class AdminPasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=6)
    new_password: str = Field(min_length=10)


class AdminUser(BaseModel):
    id: str
    email: str
    name: str
    role: AdminRole
    roles: List[AdminRole] = []
    tenant_id: str
    hierarchy_level: int = 1
    created_at: str
