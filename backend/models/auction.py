"""Wave 6 — Auction module & Governance."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field


AuctionType = Literal["reverse", "forward", "live", "sealed"]


class AuctionIn(BaseModel):
    notice_ref: str
    auction_type: AuctionType
    start_at: str
    end_at: str
    starting_price: float
    currency: str = "USD"
    minimum_decrement: float = 100  # only for reverse
    is_anonymous: bool = True


class AuctionBidIn(BaseModel):
    auction_id: str
    price: float


class TicketIn(BaseModel):
    """Wave 4 — Helpdesk."""
    subject: str
    body: str
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    category: Optional[str] = None


class TicketReplyIn(BaseModel):
    ticket_id: str
    body: str
    attachments: List[dict] = []
