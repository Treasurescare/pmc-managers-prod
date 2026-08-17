"""PMC Managers v2 — FastAPI entry point.

Runs on Cloud stack (MongoDB + FastAPI) but structured per Build Sheet v2
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
    mfa, tenants, kyc, vendor_invites, permissions, admin_heal, vendor_full_invite,
    tender_templates, notice_qa, bids_ai_compare, escrow, reports, products, billing,
    engagements, corrigenda, awards, auction_live, taxonomy, meetings, comparison,
    docusign, profile_ops, _temp_downloads,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="PMC Managers v2 — Tender & Registration API")

# ---------- Routers ----------
app.include_router(meta.router)
app.include_router(notices.router)
app.include_router(registrations.router)
app.include_router(packages.router)
app.include_router(admin_auth.router)
app.include_router(profile_ops.router)
app.include_router(_temp_downloads.router)
app.include_router(uploads.router)
app.include_router(audit_routes.router)
# Wave 9 vendor_invites must register BEFORE vendors.router so its specific
# `/registration-template` path wins over vendors.py `/{vendor_ref}` catch-all
app.include_router(vendor_invites.router)
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
# Wave 8 — KYC (stub → live via KYC-Checks / Sumsub / Onfido)
app.include_router(kyc.router)
# Wave 9 — Admin vendor invites + Permissions matrix
app.include_router(vendor_invites.router)
app.include_router(permissions.router)
# Wave 14 — Admin heal + admin creates full vendor
app.include_router(admin_heal.router)
app.include_router(vendor_full_invite.router)
# Wave 20 — Tender / RFP / RFQ template builder
app.include_router(tender_templates.router)
app.include_router(notice_qa.router)
app.include_router(bids_ai_compare.router)
app.include_router(escrow.router)
app.include_router(reports.router)
# Wave 35 — Product catalog + Stripe billing
app.include_router(products.router)
app.include_router(billing.router)
# Wave 38 — Engagements / quote pipeline
app.include_router(engagements.router)
# Wave 39 — Corrigenda + Post-Award auto-doc generator + Two-Cover enforcement
app.include_router(corrigenda.router)
app.include_router(awards.router)
# Wave 40 — Reverse Auction Live Room + UNSPSC-lite taxonomy
app.include_router(auction_live.router)
app.include_router(taxonomy.router)
# Wave 41 — Meeting Scheduler + Jitsi + L1 Auto-Comparison
app.include_router(meetings.router)
app.include_router(comparison.router)
# Wave 43 — DocuSign eSignature (JWT Grant)
app.include_router(docusign.router)


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
    for email, pw, name in (
        (config.ADMIN_EMAIL, config.ADMIN_PASSWORD, "PMC Master Admin"),
        (config.OWNER_EMAIL, config.OWNER_PASSWORD, "PMC Owner (Kannan)"),
    ):
        existing = await db.admin_users.find_one({"email": email})
        if not existing:
            await db.admin_users.insert_one({
                "email": email,
                "password_hash": hash_password(pw),
                "name": name,
                "role": "admin",
                "roles": ["admin", "committee_member", "support"],
                "hierarchy_level": 10,
                "tenant_id": config.DEFAULT_TENANT_ID,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logging.info(f"Seeded admin {email}")
        elif not existing.get("roles"):
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
    await _seed_product_catalog()
    await _seed_taxonomy()
    from routers.tender_templates import seed_master_templates
    seeded = await seed_master_templates()
    if seeded:
        logging.info(f"Seeded {seeded} tender template masters")
    # Wave 35 — Auto-Snapshot On Change
    await _refresh_reports_snapshot()


async def _seed_product_catalog() -> None:
    """Idempotent — only inserts rows whose `code` is missing.
    Also back-fills `is_active=True` on any legacy row where it's null so the
    public catalog works after schema addition."""
    from product_catalog_seed import DEFAULT_PRODUCTS
    inserted = 0
    for row in DEFAULT_PRODUCTS:
        if await db.products.find_one({"code": row["code"]}):
            continue
        doc = dict(row)
        doc.setdefault("is_active", True)   # explicit default
        doc.update({"created_at": datetime.now(timezone.utc).isoformat(),
                     "updated_at": datetime.now(timezone.utc).isoformat(),
                     "created_by": "system"})
        await db.products.insert_one(doc)
        inserted += 1
    # Migrate legacy rows with null is_active → True
    fixed = await db.products.update_many(
        {"is_active": {"$in": [None]}},
        {"$set": {"is_active": True}},
    )
    if inserted or fixed.modified_count:
        logging.info(f"Product catalog: seeded {inserted} new, backfilled is_active on {fixed.modified_count}")


async def _seed_taxonomy() -> None:
    """Wave 40 — Seed the UNSPSC-lite taxonomy on startup (idempotent)."""
    from unspsc_seed import UNSPSC_NODES
    inserted = 0
    for row in UNSPSC_NODES:
        if await db.taxonomy_nodes.find_one({"code": row["code"]}):
            continue
        doc = dict(row)
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.taxonomy_nodes.insert_one(doc)
        inserted += 1
    if inserted:
        logging.info(f"Taxonomy: seeded {inserted} UNSPSC-lite nodes")


async def _refresh_reports_snapshot() -> None:
    """Wave 35 · Auto-Snapshot On Change — regenerate all 5 stakeholder-brief
    files at startup so the /app/docs/reports/ folder never drifts from the
    ROWS defined in `reports.py`. Safe/idempotent — writes in-place."""
    try:
        from routers.reports import snapshot_to_disk
        result = snapshot_to_disk()
        logging.info(f"Refreshed stakeholder-report snapshot ({len(result['files'])} files)")
    except Exception as e:  # never block startup on a snapshot failure
        logging.warning(f"Report snapshot refresh failed: {e}")


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
