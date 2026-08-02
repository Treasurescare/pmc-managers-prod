"""Vendor login user — created automatically when a registration is approved."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class VendorLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class VendorPasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class VendorPublic(BaseModel):
    id: str
    email: str
    vendor_ref: Optional[str] = None
    company_name: Optional[str] = None
    must_change_password: bool = False
