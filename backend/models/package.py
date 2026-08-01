from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


PackageStatus = Literal["backlog", "scoping", "sbd_draft", "ready", "published", "cancelled"]


class PackageIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str = Field(min_length=3)
    category: str
    phase: Optional[str] = None
    value: Optional[float] = None
    currency: str = "USD"
    float_target_date: Optional[str] = None
    status: PackageStatus = "backlog"
    attached_documents: List[dict] = []


class PackagePatchIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: Optional[str] = None
    category: Optional[str] = None
    phase: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    float_target_date: Optional[str] = None
    status: Optional[PackageStatus] = None
    attached_documents: Optional[List[dict]] = None


class Package(BaseModel):
    id: str
    package_ref: str
    title: str
    category: str
    phase: Optional[str] = None
    value: Optional[float] = None
    currency: str
    float_target_date: Optional[str] = None
    status: PackageStatus
    attached_documents: List[dict] = []
    tenant_id: str
    created_at: str
