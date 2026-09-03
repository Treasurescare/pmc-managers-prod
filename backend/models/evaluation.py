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

    # Bug #56 — cross-field validation so a rubric with weights >1 or max<=0
    # cannot be persisted; API returns a clear 422 instead of silently saving.
    @classmethod
    def _validate_after(cls, m):
        s = sum(c.weight for c in m.technical_criteria)
        if abs(s - 1.0) > 0.01:
            raise ValueError(
                f"Technical criteria weights must sum to 1.0 (got {s:.3f}). "
                f"Adjust each row so they add up to 100%.")
        for c in m.technical_criteria:
            if c.max_score <= 0:
                raise ValueError(f"'{c.label}': max_score must be > 0")
            if c.weight < 0 or c.weight > 1:
                raise ValueError(f"'{c.label}': weight must be between 0 and 1")
        if not (0 <= m.commercial_weight <= 1):
            raise ValueError("commercial_weight must be between 0 and 1")
        return m

    def model_post_init(self, _ctx):
        ScoringRubricIn._validate_after(self)


class ScoreEntryIn(BaseModel):
    bid_id: str
    kind: EnvelopeKind
    scores: dict  # {criterion_code: value}
    remarks: Optional[str] = None
