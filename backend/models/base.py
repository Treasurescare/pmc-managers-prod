from datetime import datetime, timezone
from typing import Any, Annotated
from bson import ObjectId
from pydantic import BeforeValidator, PlainSerializer


def _validate_objectid(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError(f"Invalid ObjectId: {v!r}")


PyObjectId = Annotated[str, BeforeValidator(_validate_objectid), PlainSerializer(lambda x: str(x), return_type=str)]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseDocument:
    """Mixin helpers to translate between Mongo `_id` and API `id`."""

    @staticmethod
    def out(doc: dict) -> dict:
        if not doc:
            return doc
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc
