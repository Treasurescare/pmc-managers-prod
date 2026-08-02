"""Bid Committee — formed per tender from Admin pool."""
from typing import List, Optional, Literal
from pydantic import BaseModel


CommitteeDecision = Literal["open", "closed_awarded", "closed_rejected", "closed_no_award"]


class CommitteeCreateIn(BaseModel):
    notice_ref: str
    chairperson_id: str  # staff_id
    member_ids: List[str]
    quorum: int = 3
    notes: Optional[str] = None


class CommitteeVoteIn(BaseModel):
    committee_id: str
    bid_id: str
    vote: Literal["approve", "reject", "abstain"]
    remarks: Optional[str] = None


class CommitteeCloseIn(BaseModel):
    committee_id: str
    decision: CommitteeDecision
    awarded_bid_id: Optional[str] = None
    remarks: Optional[str] = None
