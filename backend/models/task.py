"""CRM Task & Followup models."""
from typing import List, Optional, Literal
from pydantic import BaseModel


TaskPriority = Literal["low", "medium", "high", "urgent"]
TaskStatus = Literal["open", "in_progress", "blocked", "done", "cancelled"]


class TaskCreateIn(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: str  # staff_id
    watchers: List[str] = []
    related_type: Optional[str] = None  # "bid" | "notice" | "vendor" | None
    related_id: Optional[str] = None
    priority: TaskPriority = "medium"
    due_date: Optional[str] = None


class TaskUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[str] = None


class FollowupIn(BaseModel):
    task_id: str
    message: str
    attachments: List[dict] = []  # [{key, filename, content_type, size_bytes}]
