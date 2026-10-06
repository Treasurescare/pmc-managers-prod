"""Investor Demo Mode — one-click seed a curated showcase dataset.

Creates a polished "PMC Live Demo" slice inside the current tenant:
  * 3 published notices (real-world flavored, with attachments-metadata)
  * 3 approved vendors with KZ licenses + KPI-friendly profiles
  * 5 bids covering the full lifecycle (submitted → emd_paid → admin_flagged
    → certifier_cleared → awarded)
  * 1 signed contract on the awarded bid

Every seeded row carries `is_demo: True` so an admin can call the reset
endpoint before/after an investor demo run without touching real data.

Endpoints:
  POST /api/v1/admin/demo/seed   idempotent — returns { created, existing }
  POST /api/v1/admin/demo/reset  removes every {is_demo: True} row
  GET  /api/v1/admin/demo/status counts of demo entities currently in the tenant
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends

import config
from db import db, next_sequence
from models.base import now_iso
from security import require_role, hash_password
from audit import audit_log

router = APIRouter(prefix="/api/v1/admin/demo", tags=["admin-demo"])


def _future_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


DEMO_NOTICES = [
    {
        "title": "Construction of Astana Metro Line 2 — Design & Build (Package A)",
        "description": ("Turnkey design, procurement and construction of the "
                        "12-station Line 2 extension including tunneling, "
                        "civil works, MEP, signalling, rolling-stock depot, "
                        "and 5-year O&M. QCBS 70:30, EPC delivery model."),
        "document_type": "tender",
        "category": "Infrastructure · Rail",
        "delivery_country": "KZ",
        "budget_currency": "USD",
        "budget_amount": 480_000_000,
        "days_to_deadline": 45,
        "emd_config": {"fixed_amount": 250_000, "percentage": 0, "currency": "USD"},
        "publish": True,
    },
    {
        "title": "Data Lake Modernisation for Sovereign Wealth Fund — RFP",
        "description": ("18-month engagement to migrate 40+ TB of legacy "
                        "financial holdings data into a governed lakehouse "
                        "with real-time analytics for board reporting."),
        "document_type": "rfp",
        "category": "IT · Data Platform",
        "delivery_country": "AE",
        "budget_currency": "USD",
        "budget_amount": 22_500_000,
        "days_to_deadline": 30,
        "emd_config": {"fixed_amount": 25_000, "percentage": 0, "currency": "USD"},
        "publish": True,
    },
    {
        "title": "Supply of 240 Electric Buses & Depot Charging — RFQ",
        "description": ("Framework RFQ for BYD-class electric buses, "
                        "depot chargers, telematics platform and 8-year "
                        "battery warranty. Delivery in three phases."),
        "document_type": "rfq",
        "category": "Transport · Fleet",
        "delivery_country": "KZ",
        "budget_currency": "USD",
        "budget_amount": 84_000_000,
        "days_to_deadline": 21,
        "emd_config": {"fixed_amount": 100_000, "percentage": 0, "currency": "USD"},
        "publish": True,
    },
]

DEMO_VENDORS = [
    {
        "email": "director@astana-rail-consortium.demo",
        "company_name": "Astana Rail Consortium LLP",
        "country": "KZ",
        "primary_sector": "Infrastructure · Rail",
        "kz_licenses": ["Category I · General Contracting",
                        "Category II · Underground Works",
                        "Category III · MEP Installation"],
        "employees_count": 1240,
        "categories_declared": ["Rail", "Tunneling", "Rolling Stock", "MEP"],
        "operating_regions": ["Astana", "Almaty", "Karaganda"],
    },
    {
        "email": "cto@blueshift-analytics.demo",
        "company_name": "Blueshift Analytics FZ-LLC",
        "country": "AE",
        "primary_sector": "IT · Data Platform",
        "kz_licenses": [],
        "employees_count": 320,
        "categories_declared": ["Data Engineering", "Lakehouse",
                                "Governed AI", "Board Reporting"],
        "operating_regions": ["Dubai", "Abu Dhabi", "Riyadh"],
    },
    {
        "email": "sales@zhandos-emobility.demo",
        "company_name": "Zhandos e-Mobility JSC",
        "country": "KZ",
        "primary_sector": "Transport · Fleet",
        "kz_licenses": ["Category IV · EV Import & Depot Ops"],
        "employees_count": 480,
        "categories_declared": ["Electric Bus", "Fleet Telematics",
                                "Depot Charging", "Battery O&M"],
        "operating_regions": ["Astana", "Almaty", "Aktau"],
    },
]


async def _find_demo_summary(tenant_id: str) -> dict:
    return {
        "notices": await db.notices.count_documents({"tenant_id": tenant_id, "is_demo": True}),
        "vendors": await db.vendors.count_documents({"tenant_id": tenant_id, "is_demo": True}),
        "bids": await db.bids.count_documents({"tenant_id": tenant_id, "is_demo": True}),
        "contracts": await db.contracts.count_documents({"tenant_id": tenant_id, "is_demo": True}),
    }


@router.get("/status")
async def demo_status(admin=Depends(require_role("admin"))):
    return await _find_demo_summary(admin["tenant_id"])


@router.post("/seed")
async def seed_demo(admin=Depends(require_role("admin"))):
    """Idempotent — inserts demo data only if it doesn't already exist for
    this tenant. Existing rows are left alone."""
    tenant_id = admin["tenant_id"]
    year = datetime.now(timezone.utc).year
    created = {"notices": 0, "vendors": 0, "bids": 0, "contracts": 0}

    # --- Notices ------------------------------------------------------------
    notice_refs: list[str] = []
    for n in DEMO_NOTICES:
        exists = await db.notices.find_one({
            "tenant_id": tenant_id, "is_demo": True, "title": n["title"],
        })
        if exists:
            notice_refs.append(exists["notice_ref"])
            continue
        seq = await next_sequence("notice_seq")
        notice_ref = f"PMC-NOT-{year}-{seq:04d}"
        doc = {
            "notice_ref": notice_ref,
            "title": n["title"],
            "description": n["description"],
            "document_type": n["document_type"],
            "category": n["category"],
            "delivery_country": n["delivery_country"],
            "submission_deadline": _future_iso(n["days_to_deadline"]),
            "budget_currency": n["budget_currency"],
            "budget_amount": n["budget_amount"],
            "emd_config": n["emd_config"],
            "is_published": n["publish"],
            "tenant_id": tenant_id,
            "is_demo": True,
            "created_by": admin["id"],
            "created_by_email": admin.get("email"),
            "created_at": now_iso(),
            "published_at": now_iso() if n["publish"] else None,
        }
        await db.notices.insert_one(doc)
        notice_refs.append(notice_ref)
        created["notices"] += 1

    # --- Vendors ------------------------------------------------------------
    vendor_refs: list[str] = []
    for v in DEMO_VENDORS:
        exists = await db.vendors.find_one({
            "tenant_id": tenant_id, "is_demo": True, "email": v["email"],
        })
        if exists:
            vendor_refs.append(exists["vendor_ref"])
            continue
        seq = await next_sequence("vendor_seq")
        vendor_ref = f"PMC-SUP-{seq:06d}"
        doc = {
            "vendor_ref": vendor_ref,
            "email": v["email"],
            "company_name": v["company_name"],
            "country": v["country"],
            "kz_licenses": v["kz_licenses"],
            "profile": {
                "primary_sector": v["primary_sector"],
                "employees_count": v["employees_count"],
                "business_categories": v["categories_declared"],
                "operating_regions": v["operating_regions"],
                "submitted_at": now_iso(),
                "reviewed_at": now_iso(),
            },
            "tenant_id": tenant_id,
            "is_demo": True,
            "is_active": True,
            "email_verified": True,
            "must_change_password": False,
            "password_hash": hash_password("Demo@12345"),
            "created_at": now_iso(),
        }
        await db.vendors.insert_one(doc)
        vendor_refs.append(vendor_ref)
        created["vendors"] += 1

    # --- Bids (5-stage lifecycle) ------------------------------------------
    # Only seed if we have at least 1 notice + 1 vendor
    lifecycle = [
        # (notice_idx, vendor_idx, status, price_pct_of_budget)
        (0, 0, "submitted",          0.92),
        (0, 2, "emd_paid",           0.95),
        (1, 1, "admin_flagged",      0.88),
        (1, 0, "certifier_cleared",  0.91),
        (2, 2, "awarded",            0.90),
    ]
    for (ni, vi, status, pct) in lifecycle:
        if ni >= len(notice_refs) or vi >= len(vendor_refs):
            continue
        notice_ref = notice_refs[ni]
        vendor_ref = vendor_refs[vi]
        exists = await db.bids.find_one({
            "tenant_id": tenant_id, "is_demo": True,
            "notice_ref": notice_ref, "vendor_ref": vendor_ref,
        })
        if exists:
            continue
        notice = await db.notices.find_one({"notice_ref": notice_ref})
        budget = float(notice.get("budget_amount") or 1_000_000)
        currency = notice.get("budget_currency") or "USD"
        emd_due = float((notice.get("emd_config") or {}).get("fixed_amount") or 0)
        seq = await next_sequence("bid_seq")
        bid_ref = f"PMC-BID-{year}-{seq:05d}"
        bid_doc = {
            "bid_ref": bid_ref,
            "notice_ref": notice_ref,
            "vendor_ref": vendor_ref,
            "price_currency": currency,
            "price_amount": round(budget * pct, 2),
            "emd_currency": currency,
            "emd_due_amount": emd_due,
            "emd_paid_amount": emd_due if status not in ("submitted",) else 0,
            "status": status,
            "documents": [],
            "tenant_id": tenant_id,
            "is_demo": True,
            "submitted_at": now_iso(),
            "created_at": now_iso(),
        }
        if status == "awarded":
            bid_doc["awarded_at"] = now_iso()
            bid_doc["awarded_by"] = admin.get("email")
        await db.bids.insert_one(bid_doc)
        created["bids"] += 1

        # Contract on awarded bid
        if status == "awarded":
            cseq = await next_sequence("contract_seq")
            contract_ref = f"PMC-CON-{year}-{cseq:04d}"
            await db.contracts.insert_one({
                "contract_ref": contract_ref,
                "bid_ref": bid_ref,
                "notice_ref": notice_ref,
                "vendor_ref": vendor_ref,
                "value_currency": currency,
                "value_amount": bid_doc["price_amount"],
                "status": "active",
                "signed_at": now_iso(),
                "tenant_id": tenant_id,
                "is_demo": True,
                "created_at": now_iso(),
            })
            created["contracts"] += 1

    await audit_log("admin.demo.seed", admin, "tenant", tenant_id, created)
    summary = await _find_demo_summary(tenant_id)
    return {"ok": True, "created": created, "totals": summary}


@router.post("/reset")
async def reset_demo(admin=Depends(require_role("admin"))):
    """Remove every row tagged is_demo=True for the current tenant.
    Use this before an investor demo (to wipe old state) or after (to keep
    prod data clean)."""
    tenant_id = admin["tenant_id"]
    q = {"tenant_id": tenant_id, "is_demo": True}
    deleted = {
        "notices": (await db.notices.delete_many(q)).deleted_count,
        "vendors": (await db.vendors.delete_many(q)).deleted_count,
        "bids": (await db.bids.delete_many(q)).deleted_count,
        "contracts": (await db.contracts.delete_many(q)).deleted_count,
    }
    await audit_log("admin.demo.reset", admin, "tenant", tenant_id, deleted)
    return {"ok": True, "deleted": deleted}
