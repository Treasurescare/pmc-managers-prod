"""Wave 2 — Multi-envelope bidding, scoring, COI, award recommendation."""
from typing import Optional, Literal, List
from pydantic import BaseModel


EnvelopeKind = Literal["technical", "commercial"]


class EnvelopeLockIn(BaseModel):
    """Admin locks bidding for a tender — envelopes cannot be modified after this."""
    notice_ref: str
    kind: EnvelopeKind


class COIDeclarationIn(BaseModel):
    """Evaluator declares Conflict-of-Interest before touching bids."""
    notice_ref: str
    has_conflict: bool
    details: Optional[str] = None


class ScoreCriterionIn(BaseModel):
    code: str  # "experience", "methodology", "team", "financial_health"
    label: str
    weight: float  # 0..1
    max_score: float = 100.0


class ScoringRubricIn(BaseModel):
    notice_ref: str
    technical_criteria: List[ScoreCriterionIn]
    commercial_weight: float = 0.4  # 0..1 — split with technical (1-commercial_weight)
    minimum_technical: float = 60.0  # cutoff


class ScoreEntryIn(BaseModel):
    bid_id: str
    kind: EnvelopeKind
    scores: dict  # {criterion_code: value}
    remarks: Optional[str] = None
