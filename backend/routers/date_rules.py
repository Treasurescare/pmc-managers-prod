"""v52t — shared date-chain validation for notices / corrigenda.

Mirrors frontend/src/lib/dateRules.js. Raises HTTPException 400 with a
clear, admin-readable message. All comparisons are timezone-aware UTC;
naive ISO strings (datetime-local inputs) are treated as UTC.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException


def _parse(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def require_future(v, label: str) -> None:
    """Date must be now or later (e.g. a newly set deadline)."""
    dt = _parse(v)
    if dt and dt < _utcnow():
        raise HTTPException(status_code=400,
                            detail=f"{label} cannot be in the past.")


def require_order(later, later_label: str, earlier, earlier_label: str,
                  strict: bool = False) -> None:
    """later must be on-or-after (or strictly after) earlier. Skipped when
    either side is unset."""
    a = _parse(later)
    b = _parse(earlier)
    if a is None or b is None:
        return
    bad = a <= b if strict else a < b
    if bad:
        op = "after" if strict else "on or after"
        raise HTTPException(
            status_code=400,
            detail=f"{later_label} must be {op} {earlier_label}.",
        )
