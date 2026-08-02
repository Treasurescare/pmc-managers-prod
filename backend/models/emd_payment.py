"""EMD (Earnest Money Deposit) Stripe payment model."""
from typing import Optional, Literal
from pydantic import BaseModel


PaymentStatus = Literal["pending", "paid", "failed", "expired", "refunded"]


class EMDConfig(BaseModel):
    """Set by admin on a tender notice."""
    fixed_amount: float = 0.0
    percentage: float = 0.0  # 0..100
    currency: str = "USD"

    def compute(self, tender_value: float) -> float:
        pct = (self.percentage / 100.0) * (tender_value or 0.0)
        return round(self.fixed_amount + pct, 2)


class EMDCheckoutIn(BaseModel):
    bid_id: str
    origin_url: str


class EMDRefundIn(BaseModel):
    bid_id: str
    reason: Optional[str] = None
