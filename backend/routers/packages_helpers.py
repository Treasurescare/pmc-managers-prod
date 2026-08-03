"""Helpers for routers/packages.py — CSV import row parsing."""
import csv
import io
from typing import Optional

VALID_STATUSES = ("backlog", "scoping", "sbd_draft", "ready", "published", "cancelled")


def read_csv_body(body: str) -> csv.DictReader:
    reader = csv.DictReader(io.StringIO(body))
    if not reader.fieldnames:
        raise ValueError("Empty or invalid CSV")
    return reader


def make_col_lookup(fieldnames):
    header_map = {name.lower().strip(): name for name in fieldnames}

    def col(row: dict, name: str) -> Optional[str]:
        real = header_map.get(name)
        return row.get(real) if real else None

    return col


def parse_row(row: dict, col_fn) -> tuple[Optional[dict], Optional[str]]:
    """Return (doc_partial, error_msg). Never raises."""
    title = (col_fn(row, "title") or "").strip()
    category = (col_fn(row, "category") or "").strip()
    if not title or not category:
        return None, "missing title or category"

    status_val = (col_fn(row, "status") or "backlog").strip().lower()
    if status_val not in VALID_STATUSES:
        status_val = "backlog"

    value_str = (col_fn(row, "value") or "").replace(",", "").strip()
    try:
        value_num = float(value_str) if value_str else None
    except ValueError:
        value_num = None

    return {
        "title": title,
        "category": category,
        "phase": (col_fn(row, "phase") or None),
        "value": value_num,
        "currency": (col_fn(row, "currency") or "USD").strip() or "USD",
        "float_target_date": (col_fn(row, "float_target_date") or None),
        "status": status_val,
        "attached_documents": [],
    }, None
