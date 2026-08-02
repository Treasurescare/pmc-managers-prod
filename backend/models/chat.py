"""Internal chat model — thread per {related_type, related_id}."""
from typing import List, Optional, Literal
from pydantic import BaseModel


ChatContext = Literal["bid", "notice", "task", "inspection", "vendor", "general"]


class ChatMessageIn(BaseModel):
    context_type: ChatContext
    context_id: str  # e.g. bid_id, notice_ref, task_id
    body: str
    attachments: List[dict] = []  # [{key, filename, content_type, size_bytes, kind}]
    reply_to: Optional[str] = None
