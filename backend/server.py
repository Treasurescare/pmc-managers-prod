"""PMC Managers v2 — FastAPI entry point.

Runs on Emergent stack (MongoDB + FastAPI) but structured per Build Sheet v2
API contract for zero-friction migration to AWS (RDS + Cognito + Fargate) in Phase 2.
"""
import logging
from datetime import datetime, timezone
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

import config
from db import db, create_indexes
from security import hash_password
from routers import (
    notices, registrations, packages, admin_auth, uploads, audit_routes, meta, vendors,
    staff_auth, vendor_auth, bids, payments, committee, tasks, chat, inspections, masters,
    evaluations, boqs, vendor_intel, analytics, governance, notifications, payments_sandbox,
    mfa, tenants,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="PMC Managers v2 — Tender & Registration API")

# ---------- Routers ----------
app.include_router(meta.router)
app.include_router(notices.router)
app.include_router(registrations.router)
app.include_router(packages.router)
app.include_router(admin_auth.router)
app.include_router(uploads.router)
app.include_router(audit_routes.router)
app.include_router(vendors.router)
# Wave 1 — Bidding, EMD, multi-role pipeline, CRM
app.include_router(staff_auth.router)
app.include_router(vendor_auth.router)
app.include_router(bids.router)
app.include_router(payments.router)
app.include_router(committee.router)
app.include_router(tasks.router)
app.include_router(chat.router)
app.include_router(inspections.router)
app.include_router(masters.router)
# Wave 2-6 — Evaluation, BOQ+Contracts, Vendor Intel, Analytics+AI, Governance, Notifications
app.include_router(evaluations.router)
app.include_router(boqs.router)
app.include_router(vendor_intel.router)
app.include_router(analytics.router)
app.include_router(governance.router)
app.include_router(notifications.router)
app.include_router(payments_sandbox.router)
# Wave 7 — MFA + Tenants
app.include_router(mfa.router)
app.include_router(tenants.router)


# ---------- CORS ----------
if config.CORS_ORIGINS == "*":
    _cors = {"allow_origins": ["*"], "allow_credentials": False}
else:
    _cors = {
        "allow_origins": [o.strip() for o in config.CORS_ORIGINS.split(",") if o.strip()],
        "allow_credentials": True,
    }
app.add_middleware(CORSMiddleware, allow_methods=["*"], allow_headers=["*"], **_cors)


# ---------- Startup: indexes + seed ----------
async def _seed_admin() -> None:
    existing = await db.admin_users.find_one({"email": config.ADMIN_EMAIL})
    if not existing:
        await db.admin_users.insert_one({
            "email": config.ADMIN_EMAIL,
            "password_hash": hash_password(config.ADMIN_PASSWORD),
            "name": "PMC Master Admin",
            "role": "admin",
            "roles": ["admin", "committee_member", "support"],
            "hierarchy_level": 10,
            "tenant_id": config.DEFAULT_TENANT_ID,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logging.info(f"Seeded master admin {config.ADMIN_EMAIL}")
    else:
        # Backfill roles list on legacy single-role docs
        if not existing.get("roles"):
            await db.admin_users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"roles": [existing.get("role") or "admin"],
                          "is_active": True}},
            )


async def _seed_staff() -> None:
    """Seed the 4 specialist role accounts + committee chair."""
    for email, pw, name, roles in config.STAFF_SEEDS:
        if await db.admin_users.find_one({"email": email}):
            continue
        await db.admin_users.insert_one({
            "email": email,
            "password_hash": hash_password(pw),
            "name": name,
            "role": roles[0],
            "roles": roles,
            "hierarchy_level": 5,
            "tenant_id": config.DEFAULT_TENANT_ID,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logging.info(f"Seeded staff {email} with roles {roles}")


async def _seed_demo_notices() -> None:
    """Seed a couple of published tender notices so the public board isn't empty."""
    if await db.notices.count_documents({}) > 0:
        return
    from db import next_sequence
    year = datetime.now(timezone.utc).year
    demo = [
        {
            "title": "Modular Operation Theatres — Astana Medical Campus (Phase 1)",
            "description": (
                "Design, supply, install and commission modular operation theatres for the Astana "
                "Medical Campus Phase 1. Scope covers 8 OTs with laminar-flow ceilings, "
                "medical-gas pipeline systems, HVAC, integration with hospital BMS, "
                "commissioning, training and 24-month AMC."
            ),
            "document_type": "tender",
            "category": "Modular operation theatres (OTs)",
            "delivery_country": "KZ",
            "submission_deadline": "2026-04-30T14:00:00Z",
            "pre_bid_meeting_date": "2026-03-15T10:00:00Z",
            "budget_currency": "USD",
            "budget_amount": 6800000,
            "contact_email": "tenders@pmcmanagers.com",
            "contact_name": "PMC Procurement Office",
            "is_published": True,
        },
        {
            "title": "External Power Supply Grid Connection — University Precinct",
            "description": (
                "Design and construct the external 110/10 kV grid connection for the university "
                "precinct including switchyard, protection, telemetry and RTU tie-in to the "
                "national grid operator. Live commissioning coordinated with KEGOC."
            ),
            "document_type": "rfp",
            "category": "External power supply grid connection",
            "delivery_country": "KZ",
            "submission_deadline": "2026-05-20T14:00:00Z",
            "budget_currency": "USD",
            "budget_amount": 12500000,
            "contact_email": "tenders@pmcmanagers.com",
            "contact_name": "PMC Procurement Office",
            "is_published": True,
        },
        {
            "title": "Hostel Bathrooms & Plumbing — Blocks A–D",
            "description": (
                "Supply and install sanitary fixtures, hot/cold-water distribution, waste stacks, "
                "vent lines and pressure-testing for hostel Blocks A through D (760 units total)."
            ),
            "document_type": "rfq",
            "category": "Hostel bathrooms & plumbing",
            "delivery_country": "KZ",
            "submission_deadline": "2026-03-30T14:00:00Z",
            "budget_currency": "USD",
            "budget_amount": 1800000,
            "contact_email": "tenders@pmcmanagers.com",
            "contact_name": "PMC Procurement Office",
            "is_published": True,
        },
    ]
    for n in demo:
        seq = await next_sequence("notice_seq")
        notice_ref = f"PMC-NOT-{year}-{seq:04d}"
        # Auto-license attach
        auto = config.KZ_CATEGORY_LICENSE_MAP.get(n["category"], [])
        n.update({
            "notice_ref": notice_ref,
            "required_licenses": auto,
            "attachments": [],
            "tenant_id": config.DEFAULT_TENANT_ID,
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "published_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.notices.insert_one(n)
    logging.info(f"Seeded {len(demo)} demo notices")


@app.on_event("startup")
async def on_start() -> None:
    await create_indexes()
    await _seed_admin()
    await _seed_staff()
    await _seed_demo_notices()
    await _seed_packages()


async def _seed_packages() -> None:
    if await db.packages.count_documents({}) > 0:
        return
    from kz_packages import KZ_PACKAGES
    from db import next_sequence
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    inserted = 0
    for p in KZ_PACKAGES:
        seq = await next_sequence("package_seq")
        pkg = dict(p)
        pkg.update({
            "package_ref": f"PMC-PKG-{year}-{seq:04d}",
            "currency": "USD",
            "attached_documents": [],
            "tenant_id": config.DEFAULT_TENANT_ID,
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.packages.insert_one(pkg)
        inserted += 1
    logging.info(f"Seeded {inserted} KZ packages")


@app.on_event("shutdown")
async def on_stop() -> None:
    pass
