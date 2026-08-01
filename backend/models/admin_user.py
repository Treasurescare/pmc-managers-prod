from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field


AdminRole = Literal["admin", "reviewer"]


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class AdminUser(BaseModel):
    id: str
    email: str
    name: str
    role: AdminRole
    tenant_id: str
    created_at: str
