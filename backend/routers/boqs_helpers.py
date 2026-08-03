"""Helpers for routers/boqs.py — Excel row parsing."""
from typing import List, Tuple


def parse_boq_excel_row(row: tuple, running_sl: int) -> dict:
    """Convert one Excel row tuple into a normalized BOQ item dict.

    Expects (Sl.No, Description, Unit, Quantity, Unit Rate, Remarks?).
    Returns a normalized dict; caller decides whether to keep it.
    """
    return {
        "sl_no": int(row[0]) if row[0] is not None else running_sl,
        "description": str(row[1] or "").strip(),
        "unit": str(row[2] or "nos"),
        "quantity": float(row[3] or 0),
        "unit_rate": float(row[4] or 0),
        "remarks": str(row[5] or "") if len(row) > 5 else None,
    }


def rows_to_items(rows: List[tuple]) -> Tuple[List[dict], int]:
    """Parse the data rows (skip header + blanks). Returns (items, skipped)."""
    items: List[dict] = []
    skipped = 0
    for r in rows[1:]:  # skip header
        if not r or all(c is None for c in r):
            continue
        try:
            items.append(parse_boq_excel_row(r, running_sl=len(items) + 1))
        except (ValueError, TypeError):
            skipped += 1
    return items, skipped
