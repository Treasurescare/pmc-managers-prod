"""Site Inspection module — used by Certifier role.

Admin (or delegated staff) assigns a Certifier to a tender/bid; the certifier
schedules site visits, uploads photos/videos, and submits a verification report.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel


InspectionStatus = Literal["scheduled", "in_progress", "completed", "cancelled"]
InspectionResult = Literal["pass", "fail", "conditional_pass", "pending"]


class InspectionAssignIn(BaseModel):
    notice_ref: str
    bid_id: Optional[str] = None
    certifier_id: str  # staff_id with certifier role
    scheduled_at: str
    location: Optional[str] = None
    notes: Optional[str] = None


class InspectionUpdateIn(BaseModel):
    status: Optional[InspectionStatus] = None
    result: Optional[InspectionResult] = None
    report_summary: Optional[str] = None
    media: Optional[List[dict]] = None  # [{key, kind:"photo"|"video", filename, ...}]
    scheduled_at: Optional[str] = None
    location: Optional[str] = None
