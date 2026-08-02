"""Wave 4 — Vendor Intelligence (rating, blacklist, watchlist, ESG, risk)."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field


RatingBand = Literal["excellent", "good", "fair", "poor", "blacklisted"]


class VendorRatingIn(BaseModel):
    vendor_ref: str
    score: float = Field(ge=0, le=100)
    band: RatingBand
    delivery_score: Optional[float] = None
    quality_score: Optional[float] = None
    financial_score: Optional[float] = None
    esg_score: Optional[float] = None
    remarks: Optional[str] = None


class BlacklistIn(BaseModel):
    vendor_ref: str
    reason: str
    until: Optional[str] = None  # ISO — permanent if null


class WatchlistIn(BaseModel):
    vendor_ref: str
    reason: str


class ESGDeclarationIn(BaseModel):
    vendor_ref: str
    environmental_policy: bool = False
    social_policy: bool = False
    governance_policy: bool = False
    certifications: List[str] = []
    notes: Optional[str] = None
