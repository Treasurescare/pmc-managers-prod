"""PMC Managers v2 — FastAPI entry point.

Runs on Cloud stack (MongoDB + FastAPI) but structured per Build Sheet v2
API contract for zero-friction migration to AWS (RDS + Cognito + Fargate) in Phase 2.
"""
import logging
from datetime import datetime, timezone
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

import config
from db import db, create_indexes, ping as db_ping
from security import hash_password
from routers import (
    notices, registrations, packages, admin_auth, uploads, audit_routes, meta, vendors,
    staff_auth, vendor_auth, bids, bid_drafts, payments, committee, tasks, chat, inspections, masters,
    evaluations, boqs, vendor_intel, analytics, governance, notifications, payments_sandbox,
    mfa, tenants, kyc, vendor_invites, permissions, admin_heal, vendor_full_invite,
    tender_templates, notice_qa, bids_ai_compare, escrow, reports, products, billing,
    engagements, corrigenda, awards, auction_live, taxonomy, meetings, comparison,
    docusign, profile_ops, _temp_downloads,
    stakeholder_reports, dashboard_drill, branding_theme,
    envelope_authoritative, contracts_export,
    admin_demo, push, vendor_categories, vendor_profile_changes, vendor_licenses,
    legal_entity_types, escrow_institutions, escrow_signatories, cron_escrow,
    currencies,
)
from routers import password_reset as _password_reset


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------- Startup diagnostic (visible in `eb logs` / `docker logs`) ----------
_boot_log = logging.getLogger("pmc.boot")
_boot_log.info(
    "[PMC-BOOT] tenant=%s | db=%s | email_key_set=%s | frontend_url=%s | cors=%s",
    getattr(config, "DEFAULT_TENANT_ID", "?"),
    getattr(config, "DB_NAME", "?"),
    bool(getattr(config, "EMAIL_KEY", "")),
    getattr(config, "FRONTEND_URL", "?"),
    getattr(config, "CORS_ORIGINS", "?"),
)

app = FastAPI(title="PMC Managers v2 — Tender & Registration API")


# ---------- Root health probes for load balancers (Elastic Beanstalk / ALB)
# EB Enhanced Health hits `/` (and sometimes `/health`) on the ALB. Without a
# handler these return 404 and EB reports "100% 4xx" → environment goes
# Severe even though the app itself is healthy. Return a lightweight OK.
@app.get("/")
async def _root_probe():
    return {"ok": True, "service": "pmc-tender-v2-api", "path": "/"}


@app.get("/health")
async def _plain_health():
    return {"ok": True, "service": "pmc-tender-v2-api", "path": "/health"}


# ---------- Routers ----------
app.include_router(meta.router)
app.include_router(notices.router)
app.include_router(registrations.router)
from routers import masters_v2  # v52cm — new masters: UNSPSC, geography, country licenses
app.include_router(masters_v2.router)

@app.on_event("startup")
async def _bootstrap_masters():
    """v52cm — auto-seed UNSPSC + geography + country licenses on first boot.

    v52cr — This now runs in a BACKGROUND task so FastAPI starts answering
    HTTP within <2s. Previously the 158k UNSPSC + 150k city inserts blocked
    the startup event for 2–3 minutes, which caused Elastic Beanstalk ALB
    healthchecks to time out and roll the deploy back.
    """
    import asyncio
    import os

    # v52cq rev 4 — dump env var NAMES (not values) so EB container logs
    # confirm which secrets reached the container at boot. Essential for
    # diagnosing "50% 5xx" on EB.
    if os.environ.get("PMC_LOG_ENV_KEYS_ON_BOOT") == "1":
        want = ["MONGO_URL", "DB_NAME", "JWT_SECRET", "STRIPE_API_KEY",
                "STRIPE_WEBHOOK_SECRET", "LLM_API_KEY", "RESEND_API_KEY",
                "LOCAL_DEV", "FRONTEND_URL", "CORS_ORIGINS"]
        set_keys = [k for k in want if os.environ.get(k)]
        missing = [k for k in want if not os.environ.get(k)]
        print(f"[bootstrap-env] set: {set_keys}")
        if missing:
            print(f"[bootstrap-env] MISSING (expected): {missing}")

    async def _run():
        try:
            from scripts.seed_masters import seed_unspsc, seed_geography, seed_country_licenses, DATA_DIR
            import os as _os
            from db import db as _db
            loop = asyncio.get_running_loop()
            if await _db.masters_unspsc.estimated_document_count() == 0:
                sqlite_src = _os.path.join(DATA_DIR, "unspsc_v26.sqlite")
                if _os.path.exists(sqlite_src):
                    n = await loop.run_in_executor(None, seed_unspsc, _db.delegate, sqlite_src)
                    print(f"[bg-bootstrap] seeded masters_unspsc rows={n}")
            if await _db.masters_countries.estimated_document_count() == 0:
                geo_src = _os.path.join(DATA_DIR, "csc.json")
                if _os.path.exists(geo_src):
                    stats = await loop.run_in_executor(None, seed_geography, _db.delegate, geo_src)
                    print(f"[bg-bootstrap] seeded geography {stats}")
            if await _db.masters_country_licenses.estimated_document_count() == 0:
                added = await loop.run_in_executor(None, seed_country_licenses, _db.delegate)
                print(f"[bg-bootstrap] seeded country licenses added={added}")
            print("[bg-bootstrap] masters bootstrap complete")
        except Exception as e:
            print(f"[bg-bootstrap] masters bootstrap WARN: {e}")

    if os.environ.get("PMC_SKIP_BOOTSTRAP") == "1":
        return
    asyncio.create_task(_run())


app.include_router(packages.router)
app.include_router(admin_auth.router)
app.include_router(profile_ops.router)
app.include_router(_temp_downloads.router)
app.include_router(uploads.router)
app.include_router(audit_routes.router)
# Wave 9 vendor_invites must register BEFORE vendors.router so its specific
# `/registration-template` path wins over vendors.py `/{vendor_ref}` catch-all
app.include_router(vendor_invites.router)
# v50m — vendor_profile_changes and vendor_categories expose literal paths
# under /api/v1/vendors/… (profile-change-requests, category-requests) that
# must be registered BEFORE vendors.router or the greedy `/{vendor_ref}`
# catch-all captures them and 404s with "Vendor not found".
app.include_router(vendor_profile_changes.router)
app.include_router(vendor_categories.router)
app.include_router(vendors.router)# Wave 1 — Bidding, EMD, multi-role pipeline, CRM
app.include_router(staff_auth.router)
app.include_router(vendor_auth.router)
app.include_router(vendor_licenses.router)
app.include_router(_password_reset.router)
app.include_router(bids.router)
app.include_router(bid_drafts.router)
app.include_router(payments.router)
app.include_router(committee.router)
app.include_router(tasks.router)
app.include_router(chat.router)
app.include_router(inspections.router)
app.include_router(masters.router)
app.include_router(currencies.router)
app.include_router(legal_entity_types.router)
# Wave 2-6 — Evaluation, BOQ+Contracts, Vendor Intel, Analytics+AI, Governance, Notifications
app.include_router(evaluations.router)
app.include_router(boqs.router)
app.include_router(vendor_intel.router)
from routers import vendor_ratings as _vendor_ratings
app.include_router(_vendor_ratings.router)
app.include_router(analytics.router)
app.include_router(governance.router)
app.include_router(notifications.router)
app.include_router(push.router)
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
app.include_router(admin_demo.router)
app.include_router(vendor_full_invite.router)
# Wave 20 — Tender / RFP / RFQ template builder
app.include_router(tender_templates.router)
from routers import tender_pro as _tender_pro
app.include_router(_tender_pro.router)
app.include_router(notice_qa.router)
app.include_router(bids_ai_compare.router)
app.include_router(escrow.router)
app.include_router(escrow_institutions.router)
app.include_router(escrow_signatories.router)
app.include_router(cron_escrow.router)
app.include_router(reports.router)
app.include_router(stakeholder_reports.router)
app.include_router(dashboard_drill.router)
app.include_router(branding_theme.router)
# v50 — Option E email templates + preview
from routers import admin_emails as _admin_emails
app.include_router(_admin_emails.router)
app.include_router(envelope_authoritative.router)
app.include_router(contracts_export.router)
from routers import help_content as _help_content
app.include_router(_help_content.router)
# Wave 35 — Product catalog + Stripe billing
app.include_router(products.router)
app.include_router(billing.router)
# Wave 38 — Engagements / quote pipeline
app.include_router(engagements.router)
# Wave 39 — Corrigenda + Post-Award auto-doc generator + Two-Cover enforcement
app.include_router(corrigenda.router)
app.include_router(corrigenda._vendor_router)
from routers import filter_presets as _filter_presets  # noqa: E402
app.include_router(_filter_presets.router)
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


# ---------- Cache safety (v51a) ----------
# CloudFront in production was serving CACHED GET /api responses (e.g. the
# Masters list) after mutations, so deactivating a master row looked like a
# no-op until a hard refresh. Mark every API response non-cacheable.
@app.middleware("http")
async def _no_store_api(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


# ---------- Startup: indexes + seed ----------
async def _seed_admin() -> None:
    # v46w — the master admin + owner must hold EVERY executive-tier role so
    # they can sign in from any of the 5 portal cards (Admin / Management /
    # Partners / Agents / Vendors). Vendor is a separate collection; the
    # remaining four map to portal roles below.
    FULL_ADMIN_ROLES = [
        "admin", "reviewer", "management", "partner", "agent",
        "committee_member", "support", "auditor",
    ]
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
                "roles": FULL_ADMIN_ROLES,
                "hierarchy_level": 10,
                "tenant_id": config.DEFAULT_TENANT_ID,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logging.info(f"Seeded admin {email}")
        else:
            # Idempotent role backfill — always ensure master admins carry the
            # full executive role list so v46w's 5-portal login works for them.
            current = set(existing.get("roles") or [existing.get("role") or "admin"])
            merged = sorted(current | set(FULL_ADMIN_ROLES))
            if merged != sorted(current) or not existing.get("is_active", True):
                await db.admin_users.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"roles": merged, "is_active": True}},
                )
                logging.info(f"Backfilled admin roles for {email}: {merged}")


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


async def _seed_categories() -> None:
    """v50g — seed the procurement Category master from UNSPSC taxonomy if the
    collection is empty. Also backfills from legacy KZ_CATEGORY_LICENSE_MAP
    (so licence-mapped categories already used in notices stay available).
    Idempotent — only inserts missing codes. Admin UI can edit / add after."""
    if await db.categories.count_documents({}) > 0:
        return
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    # Race-guard: EB rolling deploys can boot two instances concurrently and
    # both pass the count==0 check. Per-insert try/except + a find_one check
    # keeps the seed idempotent even under a race.
    async def _try_insert(doc: dict) -> bool:
        try:
            if await db.categories.find_one({"code": doc["code"]}):
                return False
            await db.categories.insert_one(doc)
            return True
        except Exception:
            return False
    # 1) Hospital/construction legacy categories with licence requirements.
    for name, licences in config.KZ_CATEGORY_LICENSE_MAP.items():
        code = name.lower().replace("&", "and").replace("/", "-")
        code = "-".join(w for w in code.replace("(", "").replace(")", "").split() if w)[:40]
        if await _try_insert({
            "code": code, "name": name,
            "country_scope": ["KZ"],
            "required_licences": list(licences),
            "source": "legacy", "is_active": True, "created_at": now,
        }):
            inserted += 1
    # 2) UNSPSC taxonomy — populate from pre-seeded taxonomy_nodes collection
    #    if present; else lazy-import the seed module.
    taxo_rows = [n async for n in db.taxonomy_nodes.find({}).sort("code", 1)]
    if not taxo_rows:
        try:
            from unspsc_seed import UNSPSC_NODES
            taxo_rows = UNSPSC_NODES
        except Exception:
            taxo_rows = []
    for n in taxo_rows:
        # Use UNSPSC code as unique category code (prefixed to avoid collisions).
        code = f"unspsc-{n['code']}"
        if await _try_insert({
            "code": code, "name": n["title"],
            "country_scope": None,
            "unspsc_code": n["code"],
            "parent_code": (f"unspsc-{n['parent_code']}" if n.get("parent_code") else None),
            "source": "unspsc", "is_active": True, "created_at": now,
        }):
            inserted += 1
    if inserted:
        logging.info(f"Seeded {inserted} procurement categories (UNSPSC + legacy KZ)")


async def _seed_default_rubric() -> None:
    """v46y — ensure a default 1-10 rating rubric exists so the vendor peer
    review flow always finds a rubric. Idempotent — migrates any existing
    1-5 rubric to 1-10 on cold-start."""
    existing = await db.rating_criteria_sets.find_one({"is_default": True})
    default_criteria = [
        {"code": "quality",   "label": "Quality of work",         "description": "Overall workmanship and finish",       "weight": 3.0, "scale_min": 1, "scale_max": 10},
        {"code": "delivery",  "label": "Delivery timeliness",     "description": "Adherence to agreed schedule",         "weight": 2.0, "scale_min": 1, "scale_max": 10},
        {"code": "comms",     "label": "Communication",           "description": "Responsiveness and clarity",           "weight": 1.0, "scale_min": 1, "scale_max": 10},
        {"code": "compliance","label": "Compliance & paperwork",  "description": "KYC, licences, HSE, documentation",    "weight": 2.0, "scale_min": 1, "scale_max": 10},
        {"code": "cost",      "label": "Cost discipline",         "description": "Sticking to quoted cost, no scope-creep","weight": 2.0, "scale_min": 1, "scale_max": 10},
    ]
    if not existing:
        await db.rating_criteria_sets.insert_one({
            "name": "PMC default vendor scorecard",
            "country": None, "industry": None,
            "criteria": default_criteria,
            "is_default": True, "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logging.info("Seeded default vendor rating rubric (1-10 scale)")
        return
    # Migrate any 1-5 rubric to 1-10 (keep custom codes but bump the range).
    migrated = False
    new_crit = []
    for c in existing.get("criteria") or []:
        if int(c.get("scale_max", 10)) < 10:
            c = {**c, "scale_min": 1, "scale_max": 10}
            migrated = True
        new_crit.append(c)
    if migrated:
        await db.rating_criteria_sets.update_one(
            {"_id": existing["_id"]},
            {"$set": {"criteria": new_crit,
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        logging.info("Migrated default rubric to 1-10 scale")


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
    await db_ping()   # fail-fast Mongo reachability check
    await create_indexes()
    await _seed_admin()
    await _seed_staff()
    await _seed_default_rubric()
    await _seed_demo_notices()
    await _seed_packages()
    await _seed_product_catalog()
    await _seed_taxonomy()
    await _seed_categories()
    # v52bk — ISO-4217 currency master used by Notice/Bid/EMD money fields
    try:
        from routers.currencies import seed_defaults as _seed_currencies
        await _seed_currencies()
    except Exception as exc:
        logging.warning("currencies seed skipped: %s", exc)
    # v50y — legal entity types master used by vendor registration Section A
    try:
        from routers.legal_entity_types import seed_defaults as _seed_legal_entity_types
        await _seed_legal_entity_types()
    except Exception as exc:
        logging.warning("legal_entity_types seed skipped: %s", exc)
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
