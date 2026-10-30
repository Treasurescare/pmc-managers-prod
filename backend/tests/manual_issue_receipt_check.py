# v62: unit check that issue_receipt renders + attaches the PDF without raising (send_email mocked).
import asyncio
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

import emails  # noqa: E402
from db import db  # noqa: E402
from routers import _fees  # noqa: E402

CAPTURED = {}


async def fake_send(to, subject, html, attachments=None, cc=None):
    CAPTURED.update(to=to, subject=subject, attachments=attachments)
    return True


async def main():
    emails.send_email = fake_send
    v = await db.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    rec = await _fees.issue_receipt(str(v["_id"]), "category_fee", [{"name": "TEST_ cat", "amount": 10}],
                                    "gbp", "TEST_issue_sess", {"category": "TEST cat"})
    await asyncio.sleep(1.5)
    att = CAPTURED.get("attachments")
    print("receipt", rec["receipt_no"], "to", CAPTURED.get("to"), "subject", CAPTURED.get("subject"))
    print("attachments", [(a["filename"], a["content_type"], len(a["content_b64"])) for a in att or []])
    assert att and att[0]["content_type"] == "application/pdf"
    again = await _fees.issue_receipt(str(v["_id"]), "category_fee", [{"name": "x", "amount": 1}], "gbp", "TEST_issue_sess", {})
    assert again["receipt_no"] == rec["receipt_no"], "idempotency broken"
    await db.fee_receipts.delete_many({"session_id": "TEST_issue_sess"})
    await db.messages.delete_many({"subject": {"$regex": rec["receipt_no"]}})
    print("OK")

asyncio.run(main())
