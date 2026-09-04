"""PMC Managers v2 — Master Training Manual v3 · Exhaustive Playwright capture.

Every route + every tab + every relevant sub-tab + key modals.
Each screen is described with full novice-grade metadata:
  · purpose · audience · fields · tutorial · API refs · pitfalls · errors

Output:
  /app/deliverables/manual_v3_shots/*.png
  /app/deliverables/manual_v3_shots/manifest.json
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")

from playwright.async_api import async_playwright, Page

BASE = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://tender-hub-57.preview.emergentagent.com",
)
OUT = Path("/app/deliverables/manual_v3_shots")
OUT.mkdir(parents=True, exist_ok=True)

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASS = "Admin@12345"
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PASS = "Vendor@12345"
STAFF_EMAIL = "escrow@pmcmanagers.com"
STAFF_PASS = "Escrow@123"
STAFF_ROLE = "escrow_agent"

VIEWPORT = {"width": 1440, "height": 900}

# Seeded runtime tokens (from scripts/seed_manual_v4.py)
REG_RESUME_TOKEN = "pYafyue0vvTaBAZMq9-2PqBm_Hq0aN-4"
AUCTION_AID = "RA-MANUAL-0875"
MEETING_TOKEN = "c_pol_VUsWMi0Rqhuux9_-iTlc2en7W6"
ESCROW_TOKEN = "s38VBcn6V6G7dcH0TnnfSgdC8S0dQadp"
BID_NOTICE_REF = "PMC-NOT-2026-0020"


def _P(**kw):
    kw.setdefault("wait_ms", 1600)
    kw.setdefault("full_page", True)
    kw.setdefault("actions", [])
    kw.setdefault("audience", [])
    kw.setdefault("fields", [])
    kw.setdefault("tutorial", [])
    kw.setdefault("api", [])
    kw.setdefault("pitfalls", [])
    kw.setdefault("errors", [])
    kw.setdefault("kpis", [])
    return kw


# ═════════════════════════════════════════════════════════════════════════
# 1 · PUBLIC (unauthenticated)
# ═════════════════════════════════════════════════════════════════════════
PUBLIC = [
    _P(
        slug="01-public-landing",
        title="Public landing page",
        url="/",
        role="public",
        audience=["All"],
        purpose="First view a visitor lands on. Presents brand, service lanes, sign-in / register CTAs.",
        fields=[
            ("Top-bar brand", "Portal logo + name. Clickable — always returns to '/'."),
            ("Notices nav", "Public list of open tenders. No login required."),
            ("Register nav", "Vendor self-registration entry (Section A of the wizard)."),
            ("Sign in nav", "Unified login card — pick admin / vendor / staff."),
            ("Language switcher", "EN · RU · KK. Persists in localStorage."),
            ("Hero band", "Tenant-configured value proposition + primary CTA."),
        ],
        tutorial=[
            ("Open the portal", "Navigate to https://www.pmcmanagers.com/ in any modern browser."),
            ("Switch language", "Click the EN pill top-right → RU or KK. Text re-flows instantly."),
            ("Read a tender", "Click 'Notices' → any card opens the detail view."),
            ("Register as vendor", "Click 'Register' → land on Section A of the wizard."),
        ],
        api=[("GET", "/api/v1/notices?public=1", "Returns published notices only.")],
        pitfalls=["Draft notices never appear here — only status=published are visible."],
        errors=["If the language pill only shows English, the i18n bundle failed — hard-refresh (Ctrl+F5)."],
    ),
    _P(
        slug="02-public-notice-board",
        title="Public notice board",
        url="/notices",
        role="public",
        audience=["All"],
        purpose="Browsable directory of every published tender / RFP / RFQ across all tenants.",
        fields=[
            ("Search bar", "Full-text search over title + description."),
            ("Country filter", "ISO-2 country code."),
            ("Category filter", "Free-text tag — Construction, IT, Consulting…"),
            ("Notice card", "Title · closing date · budget · country · CTA 'View'."),
            ("Empty state", "'No open tenders match your filters' — friendly copy with a Reset button."),
        ],
        tutorial=[
            ("Filter to India", "Country → IN → list refreshes without page reload."),
            ("Open a notice", "Click any card → detail page opens with description + downloads + QA thread."),
        ],
        api=[("GET", "/api/v1/notices?public=1&country=IN", "Filters by country.")],
        pitfalls=["Closed tenders still show but with a 'CLOSED' pill — participation buttons are disabled."],
    ),
    _P(
        slug="03-public-notice-detail",
        title="Public notice detail",
        url="/notices",
        role="public",
        audience=["All"],
        purpose="Every field of a single tender, downloads, QA thread and 'Bid now' CTA.",
        actions=[("click_first", "[data-testid=public-notice-card]", None)],
        fields=[
            ("Title bar", "Notice ref (PMC-NOT-YYYY-####) + title."),
            ("Deadline banner", "Countdown timer to submission_deadline (UTC)."),
            ("Description", "Full HTML body composed via Tender Builder."),
            ("Downloads", "Primary document + attachments (PDF / DOCX / XLSX)."),
            ("QA thread", "Public question/answer log — answers appear only after admin publishes them."),
            ("Bid now CTA", "Redirects to /vendor/bid/new/:ref (requires vendor login)."),
        ],
        tutorial=[
            ("Download the tender document", "Click 'Primary document' → PDF downloads immediately."),
            ("Ask a public question", "QA thread → 'Ask a question' → type ≥ 10 chars → Submit. Admin will publish the answer."),
        ],
        api=[
            ("GET", "/api/v1/notices/{notice_ref}", "Public if is_published=true."),
            ("POST", "/api/v1/notice-qa/{notice_ref}", "Post a QA thread question."),
        ],
        pitfalls=["Corrigenda (amendments) are shown under a 'History' expander — always read them before bidding."],
    ),
    _P(
        slug="04-registration-a-identity",
        title="Vendor registration · Section A — Identity",
        url="/register",
        role="public",
        audience=["Vendor", "Ops"],
        purpose="Entry point of the 5-section KYC wizard. Section A captures identity + primary contact.",
        fields=[
            ("Company name", "Legal name as per registration certificate. Required."),
            ("Contact person", "First + last name of primary contact."),
            ("Email", "Primary email — must be unique per tenant."),
            ("Phone", "E.164 with country code (e.g. +91-98765-43210)."),
            ("Country", "ISO-2. Determines the KYC doc catalog in Section D."),
            ("Save & continue", "Creates a silent draft and emails a resume-token."),
        ],
        tutorial=[
            ("Fill Section A", "Enter all fields → Save & continue. Draft is created."),
            ("Save the resume email", "Backend mails a resume-token URL to the primary email."),
        ],
        api=[
            ("POST", "/api/v1/registrations/draft", "Creates draft + returns resume_token."),
            ("GET", "/api/v1/registrations/resume/{token}", "Loads a draft by token."),
        ],
        pitfalls=[
            "Losing the resume email = start over. Admin can re-issue via Registrations panel.",
            "Country change mid-flow re-loads the Section D doc catalog and clears prior D uploads.",
        ],
    ),
    _P(
        slug="05-registration-status",
        title="Vendor registration · Status check",
        url="/register/status",
        role="public",
        audience=["Vendor", "Ops"],
        purpose="Any vendor with the emailed resume-token can check status without logging in.",
        fields=[
            ("Token input", "Paste the 24-char URL-safe token from the email."),
            ("Check button", "Fetches current stage + reviewer notes."),
            ("Status card", "Stage · updated_at · reviewer comments (if any)."),
        ],
        tutorial=[
            ("Paste an invalid token", "Toast surfaces 'Token invalid or expired' (Bug 7 fix)."),
            ("Paste a valid token", "Result card renders stage banner + latest reviewer note."),
        ],
        api=[("GET", "/api/v1/registrations/status?token=…", "Public read.")],
    ),
    _P(
        slug="06-public-roadmap",
        title="Public product roadmap",
        url="/roadmap",
        role="public",
        audience=["Client", "Investor"],
        purpose="Client-visible feature roadmap. Fed from the admin roadmap module.",
        fields=[
            ("Column · Shipped", "Delivered features by quarter."),
            ("Column · In progress", "Active WIP."),
            ("Column · Planned", "Committed backlog."),
        ],
        api=[("GET", "/api/v1/roadmap", "Public feed.")],
    ),
    _P(
        slug="07-unified-login",
        title="Unified login card",
        url="/login",
        role="public",
        audience=["All"],
        purpose="Single entry point offering Admin / Vendor / Staff login lanes.",
        fields=[
            ("Admin card", "Redirects to /admin/login."),
            ("Vendor card", "Redirects to /vendor/login."),
            ("Staff card", "Redirects to /staff/login (auditor, escrow, certifier…)."),
        ],
        tutorial=[
            ("Pick your role", "Click the card matching the account you were issued."),
            ("Bookmark it", "Once picked, the choice is remembered in localStorage for next visit."),
        ],
    ),
    _P(
        slug="08-admin-login",
        title="Admin login page",
        url="/admin/login",
        role="public",
        audience=["Ops", "Mgmt"],
        purpose="Master admin + reviewer credential login. HTTPOnly cookie + CSRF double-submit.",
        fields=[
            ("Email", "Admin or reviewer email."),
            ("Password", "Min 12 chars, 1 upper, 1 digit, 1 symbol."),
            ("Sign in", "POST /api/v1/admin/auth/login."),
            ("Forgot password", "Sends recover-token email; token TTL 30 min."),
        ],
        tutorial=[
            ("Log in", "Email + password → Sign in → redirect to /admin within ~1s."),
            ("Wrong password", "Toast shows backend error. 5 fails → 15-min lockout."),
        ],
        api=[
            ("POST", "/api/v1/admin/auth/login", "Returns {token,role}. Sets HTTPOnly cookie."),
            ("POST", "/api/v1/admin/auth/logout", "Clears cookie."),
            ("POST", "/api/v1/admin/auth/change-password", "Requires CSRF header."),
        ],
        pitfalls=["Stale cookies from another tenant — log out first (avatar → Sign out)."],
        errors=["401 Invalid credentials · 429 Too many attempts (retry in 15 min) · 403 CSRF missing."],
    ),
    _P(
        slug="09-vendor-login",
        title="Vendor login page",
        url="/vendor/login",
        role="public",
        audience=["Vendor"],
        purpose="Approved vendors sign in with email + password to reach the vendor portal.",
        fields=[
            ("Email", "Vendor primary email (must match approved registration)."),
            ("Password", "Set via activation email after Registration is approved."),
            ("Register link", "Bounces to /register for new vendors."),
            ("Back to notices", "Public notice board link."),
        ],
        tutorial=[
            ("Sign in", "Email + password → Sign in → land on /vendor within 1s."),
            ("First-time login", "If must_change_password=true, you are forced to /vendor/change-password before anything else."),
        ],
        api=[("POST", "/api/v1/vendor/auth/login", "Sets vendor session cookie + returns csrf_token.")],
        errors=["401 Invalid email or password · 403 Vendor account disabled (contact admin)."],
    ),
    _P(
        slug="10-staff-login",
        title="Staff login page",
        url="/staff/login",
        role="public",
        audience=["Staff"],
        purpose="Escrow · Certifier · Legal · Accounting · Committee · Support · Auditor login lane.",
        fields=[
            ("Email", "Staff email seeded in Masters → Staff."),
            ("Password", "Provided by admin at seeding."),
            ("Role picker", "Select the role you are signing in as (multi-role staff)."),
            ("OTP (MFA)", "6-digit TOTP if MFA is enabled for that account."),
        ],
        api=[("POST", "/api/v1/staff/auth/login", "Body {email, password, active_role, mfa_code?}.")],
        errors=["422 active_role invalid — must be one of: admin, reviewer, escrow_agent, certifier, legal_counsel, accounting, committee_member, auditor, support."],
    ),
    _P(
        slug="11-mobile-login",
        title="Mobile login",
        url="/m/login",
        role="public",
        audience=["Mobile"],
        purpose="Compact login card sized for narrow (<420 px) viewports. Same auth endpoints as desktop.",
    ),
    # ---- Token-gated public routes (seeded) --------------------------------
    _P(
        slug="12-registration-resume",
        title="Vendor registration · Resume with token",
        url=f"/register/resume?token={REG_RESUME_TOKEN}",
        role="public", audience=["Vendor", "Ops"],
        purpose="Any vendor can resume a draft by pasting the resume-token from the email. This capture uses a seeded draft that has sections A/B/C/D/E prefilled.",
        fields=[
            ("Section stepper", "A · Identity → B · Structure → C · Financials → D · Documents → E · References."),
            ("Section panels", "Each panel shows the fields you filled last time — you can edit any."),
            ("Submit for review", "Once all sections pass validation, submit for admin review."),
        ],
        api=[("GET", "/api/v1/registrations/resume/{token}", "Loads the draft.")],
    ),
    _P(
        slug="13-escrow-officer-magic",
        title="Escrow officer · Magic-link signature",
        url=f"/escrow/officer/{ESCROW_TOKEN}",
        role="public", audience=["Escrow"],
        purpose="Escrow institution officer signs a release/refund without logging into the portal — a magic-link token authorises exactly one signature.",
        fields=[
            ("Amount", "The amount being signed for."),
            ("Sign as officer", "Records the officer's signature. Token becomes single-use."),
            ("Reason", "Free text for the ledger."),
        ],
        api=[("GET", "/api/v1/escrow/magic/{token}", "Load."), ("POST", "/api/v1/escrow/magic/{token}/sign", "Sign.")],
    ),
    _P(
        slug="14-meeting-room",
        title="Meeting room · Join by token",
        url=f"/meet/{MEETING_TOKEN}",
        role="public", audience=["Attendee"],
        purpose="Public join page for a scheduled meeting. Displays attendee list, Zoom link, and the Accept/Decline CTA.",
        fields=[
            ("Meeting title", "As set by the organiser."),
            ("Zoom URL", "One-click join."),
            ("Attendees", "Current RSVP status per invitee."),
            ("Accept / Decline", "Updates your RSVP."),
        ],
        api=[("GET", "/api/v1/meetings/join/{token}", "Loads meeting.")],
    ),
]


# ═════════════════════════════════════════════════════════════════════════
# 2 · ADMIN CONSOLE — every tab + every sub-tab
#     Each entry is a full _P dict rendered as a chapter.
# ═════════════════════════════════════════════════════════════════════════
def _admin(slug, title, tab_key, purpose, sub_actions=None, **rest):
    return _P(
        slug=slug, title=title, tab=tab_key, role="admin",
        url=f"/admin?tab={tab_key}", purpose=purpose,
        actions=[("click", f"[data-testid=admin-tab-{tab_key}]", None)] + (sub_actions or []),
        **rest,
    )


ADMIN = [
    _admin(
        "21-admin-analytics", "Admin console · Analytics dashboard", "analytics",
        "The operations overview — KPI tiles, pipeline funnel, top-priced bids, AI anomaly copilot, drill-through cards.",
        audience=["Ops", "Mgmt"],
        fields=[
            ("KPI band", "Published notices · Vendors · Bids · Awarded · Pending EMD · EMD collected · Active contracts."),
            ("AI Anomaly card", "Count of bids flagged by GPT anomaly scoring. Click to drill."),
            ("Pipeline Funnel card", "Bids across every stage. Click to drill."),
            ("Top-Priced Bids card", "Top-10 by price. Click to drill."),
            ("Pipeline funnel table", "Per-stage counts: emd_pending → emd_paid → escrow_accepted → admin_flagged → certifier_cleared → legal_cleared → accounting_cleared → awarded."),
            ("Top-priced bids table", "Bid ref · vendor · price · status."),
            ("AI bid anomaly check", "Pick a bid → 'Run AI check' → GPT flags outliers."),
        ],
        tutorial=[
            ("Read the KPI band", "Every tile is clickable → drills into the underlying list."),
            ("Run an AI anomaly check", "Scroll to the AI bid anomaly check widget → pick a bid → 'Run AI check'. Result appears inline in ~4s."),
            ("Drill through a KPI", "Click any card in the top row (Anomaly / Pipeline / Top-Priced) → drill card table appears with each source record."),
        ],
        api=[
            ("GET", "/api/v1/analytics/summary", "Powers the KPI band."),
            ("GET", "/api/v1/dashboard-drill/anomalies", "AI-flagged bids."),
            ("GET", "/api/v1/dashboard-drill/pipeline", "Bids grouped by stage."),
            ("GET", "/api/v1/dashboard-drill/top-priced", "Top-10 by price."),
            ("POST", "/api/v1/bids/{id}/ai-anomaly-check", "Runs GPT anomaly check on a single bid."),
        ],
        pitfalls=[
            "The KPI numbers are tenant-scoped — if you switch tenant, refresh.",
            "AI check requires an EMERGENT_LLM_KEY server-side; missing key returns 503.",
        ],
        kpis=[
            "notices_published_per_month",
            "median_time_notice_creation_to_publish",
            "bids_per_notice_avg",
            "emd_collected_per_month",
        ],
    ),
    _admin(
        "21a-admin-drill-anomalies", "Analytics · Drill · AI anomalies", "analytics",
        "Drill card of AI-flagged anomalous bids with reason strings.",
        sub_actions=[("click", "[data-testid=drill-tab-anom]", None)],
        fields=[
            ("Bid ref", "PMC-BID-YYYY-#### — click to open the bid drawer."),
            ("Vendor", "Vendor name + ref."),
            ("Reason", "GPT-generated one-liner e.g. 'price 60% below cluster median'."),
        ],
    ),
    _admin(
        "21b-admin-drill-pipeline", "Analytics · Drill · Pipeline aging", "analytics",
        "Drill card of every bid grouped by pipeline stage, sorted by dwell time.",
        sub_actions=[("click", "[data-testid=drill-tab-pipe]", None)],
        fields=[
            ("Stage", "One of the 8 pipeline stages."),
            ("Bid ref", "Click to open drawer."),
            ("Dwell time", "Days since last state change."),
        ],
    ),
    _admin(
        "21c-admin-drill-top", "Analytics · Drill · Top vendors", "analytics",
        "Top-performing vendors by award count in the current period.",
        sub_actions=[("click", "[data-testid=drill-tab-top]", None)],
        fields=[
            ("Vendor", "Vendor name + ref."),
            ("Awards", "Count in the last 90d."),
            ("Value", "Sum awarded value (tenant currency)."),
        ],
    ),

    _admin(
        "22-admin-registrations", "Admin console · Registrations pipeline", "registrations",
        "Every vendor registration in every stage — Draft / Submitted / Approved / Rejected / Clarification.",
        audience=["Ops"],
        fields=[
            ("Stage tabs", "Draft · Submitted · Approved · Rejected · Clarification-requested."),
            ("Registration row", "Company · country · draft-age · reviewer note."),
            ("Approve", "Marks status=approved. Vendor gets activation email + must_change_password=true."),
            ("Reject", "Requires a reason ≥ 5 chars. Vendor gets a rejection email."),
            ("Request clarification", "Emails the vendor a note ≥ 5 chars. Vendor uses the resume token to re-enter."),
        ],
        tutorial=[
            ("Approve a registration", "Click Submitted tab → pick a row → 'Approve' → confirm."),
            ("Reject a registration", "Click Submitted tab → pick a row → 'Reject' → type reason ≥ 5 chars → Confirm."),
            ("Request clarification", "'Request clarification' → type note ≥ 5 chars → Send."),
        ],
        api=[
            ("GET", "/api/v1/registrations?status=submitted", "List by status."),
            ("POST", "/api/v1/registrations/{id}/approve", "Approve."),
            ("POST", "/api/v1/registrations/{id}/reject", "Body {reason}. reason ≥ 5 chars."),
            ("POST", "/api/v1/registrations/{id}/request-clarification", "Body {note}."),
        ],
        pitfalls=[
            "Approve sends the activation email via Resend; missing EMAIL_KEY = no email + no error.",
            "Rejected drafts are purged after 90 days by a nightly job.",
        ],
    ),

    _admin(
        "23-admin-vendors", "Admin console · Vendors master", "vendors",
        "Approved vendors master table with Bulk Invite CSV + Add & Fill Full Form + Invite Vendor + Replace Registration Template.",
        audience=["Ops"],
        fields=[
            ("Replace registration template", "Upload a new PDF template used for all future registrations."),
            ("Download current template", "Fetches the current PDF."),
            ("Bulk invite (CSV)", "Upload a CSV of primary emails; duplicate rows return per-row 409 without aborting."),
            ("Add & fill full form", "Admin-side create — for onboarding an existing partner in one shot."),
            ("Invite vendor", "Send a magic-link invitation email to a single vendor."),
            ("Search box", "Substring match on name + ref + email."),
            ("Vendor row", "Company · vendor_ref · email · country · verify status pill."),
            ("KPI drawer", "Right pane — pick a vendor to see award counts + on-time delivery %."),
        ],
        tutorial=[
            ("Bulk-invite 20 suppliers", "Prepare a CSV: primary_email,company_name,country. Click 'Bulk invite (CSV)' → drop file → confirm. Backend returns per-row 200/409."),
            ("View KPI for a vendor", "Click any row → right pane populates with awards + fulfilment + blacklist status."),
            ("Redact a vendor (GDPR)", "Row → drawer → GDPR Forget. Data is anonymised in-place, PII masked."),
        ],
        api=[
            ("GET", "/api/v1/vendors?limit=50", "Paginated list."),
            ("GET", "/api/v1/vendors/{vendor_ref}/kpi", "KPI dashboard."),
            ("POST", "/api/v1/vendors/bulk-invite", "CSV bulk invite."),
            ("POST", "/api/v1/vendor/gdpr-forget", "GDPR redaction (vendor-initiated) or admin route."),
        ],
        pitfalls=[
            "GDPR forget is IRREVERSIBLE — no undo. Always confirm the vendor_ref twice.",
            "Bulk invite dedupes by primary email per tenant — a vendor already registered under a different tenant is NOT a duplicate.",
        ],
    ),

    _admin(
        "23a-admin-vendors-bulk-invite", "Vendors · Bulk invite modal", "vendors",
        "Modal that accepts a CSV of vendor invites and returns a per-row 200/409 report.",
        sub_actions=[("click", "[data-testid=vendors-bulk-invite-open]", None)],
        fields=[
            ("CSV picker", "Accepts .csv up to 5 MB."),
            ("Preview table", "First 20 rows shown; every row gets a green tick / red cross after Submit."),
            ("Submit button", "Fires the invites in the background — you can leave the modal open."),
        ],
        api=[("POST", "/api/v1/vendors/bulk-invite", "Multipart form. Returns [{row, status, error?}].")],
        pitfalls=["A single malformed row does NOT abort the batch — but the row is skipped and returned with status=422."],
    ),

    _admin(
        "24-admin-notices", "Admin console · Notices", "notices",
        "Notices master + filter bar. Every tender / RFP / RFQ starts and ends here.",
        audience=["Ops", "Mgmt"],
        fields=[
            ("+ New notice", "Slides down the create-form. Only visible if you have 'notices.create'."),
            ("Filter bar", "Search text · status pill · document-type pill · budget currency filter · template-linked toggle."),
            ("Notice row", "notice_ref · title · status pill · deadline · budget · country."),
            ("Bulk publish", "Multi-select rows → 'Publish selected' (Master Admin only)."),
        ],
        tutorial=[
            ("Search a notice", "Type 3+ chars in the search box → list filters live."),
            ("Filter to drafts older than 5 days", "Status → draft. Look at 'Days since created' — anything > 5d is review-worthy."),
            ("Open a notice for editing", "Click the row → drawer opens with Corrigenda tab + attachments + committee refs."),
        ],
        api=[
            ("GET", "/api/v1/notices?status=draft", "Filter by status."),
            ("POST", "/api/v1/notices", "Create draft."),
            ("PUT", "/api/v1/notices/{id}", "Update draft."),
            ("POST", "/api/v1/notices/{id}/publish", "Master Admin only."),
        ],
        pitfalls=[
            "You cannot edit a published notice — issue a Corrigendum instead.",
            "budget_amount validates ge=0. Negative returns 400 (Bug 4 fix).",
            "notice_ref is auto-generated per tenant per year — never edit it.",
        ],
    ),

    _admin(
        "24a-admin-notices-new", "Notices · Create notice form", "notices",
        "The + New notice form. Every field on it, with validation rules.",
        sub_actions=[("click", "[data-testid=notice-new-toggle]", None)],
        fields=[
            ("Title", "String ≥ 5 chars."),
            ("Description", "≥ 10 chars. Supports Markdown."),
            ("Category", "Free text — used for search filters."),
            ("Document type", "tender / rfp / rfq."),
            ("Country", "ISO-2."),
            ("Submission deadline", "datetime-local — stored as UTC."),
            ("Budget currency", "ISO-4217, e.g. USD, INR, KZT."),
            ("Budget amount", "Number ≥ 0 (Bug 4 fix)."),
            ("EMD fixed / percentage", "Two mutually exclusive inputs. If percentage, base is budget_amount."),
            ("Approval matrix", "Pick from Masters → Matrix. Required to publish."),
            ("Tender template", "Pick from Tender Builder. Required for tender / rfp."),
            ("Publish immediately", "Master Admin only. If checked, status becomes 'published' on save."),
            ("Primary document", "PDF ≤ 10 MB. Required for tender / rfp."),
            ("Attachments", "Up to 10 files ≤ 10 MB each."),
            ("Create button", "POST /api/v1/notices → returns the created ref."),
        ],
        tutorial=[
            ("Create a draft tender", "Fill every required field → leave Publish unchecked → 'Create'."),
            ("Publish immediately", "Same form → tick 'Publish immediately' (visible only to Master Admin) → Create."),
        ],
        errors=["400 budget_amount < 0 · 400 description too short · 403 role can't publish · 409 duplicate template link."],
    ),

    _admin(
        "25-admin-corrigenda", "Admin console · Corrigenda", "corrigenda",
        "Formal amendments to published notices. Every change is auditable, capped at 3 withdrawals per notice.",
        audience=["Ops", "Mgmt"],
        fields=[
            ("+ New corrigendum", "Requires an already-published parent notice."),
            ("Description", "≥ 20 chars. Written as if a lawyer will read it."),
            ("New deadline (optional)", "Extends submission_deadline."),
            ("Publish", "Sends notification to all subscribed bidders + updates public notice history."),
            ("Withdraw", "Reversal action; withdrawal reason ≥ 5 chars is mandatory."),
        ],
        api=[
            ("POST", "/api/v1/corrigenda", "Body {notice_ref, description, new_deadline?}."),
            ("POST", "/api/v1/corrigenda/{id}/publish", "Publishes + notifies."),
            ("POST", "/api/v1/corrigenda/{id}/withdraw", "Body {reason}. reason ≥ 5 chars."),
        ],
        pitfalls=["4th corrigendum on the same notice returns 400 'withdrawal capped at 3' — pattern encourages issuing one comprehensive amendment."],
    ),

    _admin(
        "26-admin-tender-builder", "Admin console · Tender Builder", "tender-builder",
        "Template builder. Compose reusable tender / RFP / RFQ templates: sections + annexures + header form + AI drafter + version history.",
        audience=["Ops", "Mgmt"],
        fields=[
            ("Kind toggle", "Tender / RFP / RFQ. Determines the section catalog."),
            ("Master Library", "Read-only reference templates (e.g. 'Standard PSU e-Tender (GFR 2017, QCBS 70/30)'). 'Clone as draft' to seed."),
            ("Your drafts", "Editable drafts owned by the tenant."),
            ("Name", "Human-readable template name."),
            ("Save", "Persists the draft."),
            ("History", "Every save is versioned; you can restore any prior version."),
            ("Export PDF", "Renders the composed template to PDF for offline review."),
            ("Language toggle", "EN / RU / KK for PDF export."),
            ("Delete", "Only allowed on drafts you own."),
            ("Bulk upload", "Import a .zip of section .docx files."),
        ],
        tutorial=[
            ("Clone a master template", "Pick 'Standard PSU e-Tender' → 'Clone as draft' → new draft appears in 'Your drafts'."),
            ("Add a section", "Right pane → '+ Add' → pick section type (Instructions / Eligibility / Scope / Evaluation / GCC / SCC / Annexure)."),
            ("AI draft a clause", "Focus a section → 'AI draft' menu → pick a preset. GPT drafts the clause; you review and Save."),
            ("Restore an old version", "History → pick a timestamp → 'Restore'."),
        ],
        api=[
            ("GET", "/api/v1/tender-templates?kind=tender", "List templates."),
            ("POST", "/api/v1/tender-templates", "Create."),
            ("PUT", "/api/v1/tender-templates/{id}", "Update (creates a new version)."),
            ("POST", "/api/v1/tender-templates/{id}/export?lang=en", "Export PDF."),
            ("POST", "/api/v1/tender-templates/{id}/ai-draft", "GPT-5 drafting."),
        ],
        pitfalls=[
            "Deleting a draft that is linked to a notice returns 409 — unlink first.",
            "Bulk upload accepts .docx only; unsupported files are skipped with per-file 415.",
        ],
    ),

    _admin(
        "27-admin-bidding", "Admin console · Bidding operations", "bidding",
        "Bid pipeline + Committee UX (checkbox grid, dissolve, resend invite, assign certifier).",
        audience=["Ops", "Committee"],
        fields=[
            ("Bid filter", "By status pill or by notice_ref."),
            ("Bid table", "Bid ref · vendor · notice · price · pipeline stage · action buttons."),
            ("+ New committee", "Opens the CommitteeForm — see 27a."),
            ("Committee list", "Every existing committee for the current notice — expand to see members + status."),
            ("Assign certifier", "Modal — pick a certifier user + notes."),
            ("AI bid compare", "Runs GPT compare of top bids."),
        ],
        tutorial=[
            ("Filter bids to escrow_accepted", "Change filter → only escrow_accepted bids remain visible."),
            ("Trigger AI compare", "Pick two bids → 'AI compare' → drawer with side-by-side matrix."),
            ("Assign certifier for a bid", "Row → 'Assign certifier' → pick user → notes → Confirm. Certifier gets an email."),
        ],
        api=[
            ("GET", "/api/v1/bids?status=escrow_accepted", "Filter by stage."),
            ("POST", "/api/v1/bids/{id}/assign-certifier", "Body {certifier_id, note}."),
            ("POST", "/api/v1/bids/ai-compare", "Body {bid_ids:[...]}. GPT-5 compare."),
        ],
    ),

    _admin(
        "27a-admin-bidding-new-committee", "Bidding · New committee form", "bidding",
        "Committee create form — the checkbox grid across all roles, quorum picker, chair.",
        sub_actions=[("click", "[data-testid=committee-new-toggle]", None)],
        fields=[
            ("Notice_ref", "Which notice this committee is for."),
            ("Name", "Human-readable committee name."),
            ("Members checkbox grid", "Every staff user × every role. Tick each cell that applies."),
            ("Chair", "One member marked as chair. Chair casts the tie-breaker vote."),
            ("Quorum", "Number of members required for a valid decision. Default = 3."),
            ("Save", "Persists + sends invite emails to every member."),
        ],
        tutorial=[
            ("Create a 5-member committee", "Fill name → tick 5 members → pick a chair → quorum=3 → Save."),
            ("Resend an invite", "Members list → pick a member → 'Resend invite'. Idempotent."),
            ("Dissolve a committee", "Committee → 'Dissolve' → mandatory reason → Confirm."),
        ],
        api=[
            ("POST", "/api/v1/committee", "Create."),
            ("POST", "/api/v1/committee/{id}/dissolve", "Body {reason}."),
            ("POST", "/api/v1/committee/{id}/resend-invite/{member_id}", "Idempotent."),
        ],
        pitfalls=[
            "You cannot dissolve a committee that has already voted — archive it instead.",
            "Committee invite emails expire after 7 days; 'Resend' generates a new token.",
        ],
    ),

    _admin(
        "28-admin-escrow", "Admin console · Escrow (EMD)", "escrow",
        "Joint-signature Earnest Money Deposit escrow — accounts + transactions with dual-officer approval.",
        audience=["Ops", "Escrow", "Accounting"],
        fields=[
            ("Accounts section", "One row per notice — balance, currency, joint officers, status."),
            ("Create account", "Assigns two officers (must be different people) + currency."),
            ("Transactions section", "Every deposit / release / refund with dual-signature status."),
            ("Officer A / Officer B sign", "Each officer clicks 'Sign' via their own login. Money only moves when both signed."),
            ("Refund", "Auto-triggered on bid rejection / notice cancellation."),
        ],
        tutorial=[
            ("Create an escrow account", "Escrow → Accounts → '+ New' → pick notice + Officer A + Officer B + currency → Save."),
            ("Approve a release", "Transactions → pick pending row → Officer A signs → Officer B signs → funds move."),
        ],
        api=[
            ("POST", "/api/v1/escrow/accounts", "Create joint account."),
            ("POST", "/api/v1/escrow/transactions", "Deposit / release / refund."),
            ("POST", "/api/v1/escrow/transactions/{id}/sign", "Each officer signs via own session."),
        ],
        pitfalls=[
            "Officer A and Officer B cannot be the same person — 400 enforced.",
            "SLA threshold on pending transactions is exposed on the Stakeholder → Escrow report.",
        ],
    ),

    _admin(
        "29-admin-evaluation", "Admin console · Evaluation & scoring", "evaluation",
        "Rubric editor + technical/commercial lock + COI declaration + award report.",
        audience=["Evaluators", "Committee"],
        fields=[
            ("Notice ref input", "Which notice to evaluate."),
            ("Lock technical", "Freezes technical scores — no further edits."),
            ("Lock commercial", "Freezes commercial scores."),
            ("Award report", "Generates the QCBS award report PDF."),
            ("COI declaration", "Evaluator ticks 'has conflict?' + optional note → captured to audit."),
            ("Rubric editor", "Criteria + weights per section (technical rubric)."),
            ("Bid score list", "Every bid × every criterion score."),
        ],
        tutorial=[
            ("Set up a rubric", "Evaluation → Rubric editor → add criteria + weights (must sum to 100)."),
            ("Score every bid", "Bid score list → pick bid → enter score per criterion → Save."),
            ("Lock scores", "'Lock technical' → confirm. Once locked no evaluator can edit."),
            ("Generate the award report", "'Award report' → generates PDF at /api/v1/evaluations/{ref}/award."),
        ],
        api=[
            ("GET", "/api/v1/evaluations/{notice_ref}", "Rubric + scores."),
            ("POST", "/api/v1/evaluations/{notice_ref}/lock/technical", "Freeze."),
            ("POST", "/api/v1/evaluations/{notice_ref}/lock/commercial", "Freeze."),
            ("POST", "/api/v1/evaluations/coi", "Body {notice_ref, has_conflict, note?}."),
            ("GET", "/api/v1/evaluations/{notice_ref}/award", "PDF."),
        ],
        pitfalls=["Locking is one-way — only Master Admin can unlock via an audit-logged override."],
    ),

    _admin(
        "30-admin-awards", "Admin console · Awards & POs", "awards",
        "Awarded bids + Purchase Order generation. Regenerate is guarded by a confirmation modal + versions all previous POs.",
        audience=["Ops", "Accounting"],
        fields=[
            ("Awards list", "Bid ref · vendor · award amount · PO ref · pdf link."),
            ("Regenerate PO", "Reruns the PDF generator with a new version. Old PDFs are preserved."),
            ("Version log", "Every generated PO version with timestamp + actor."),
            ("Download PO", "Serves the latest PO PDF."),
        ],
        api=[
            ("GET", "/api/v1/awards", "List."),
            ("POST", "/api/v1/awards/{bid_ref}/generate-po", "Generates new PO version."),
            ("GET", "/api/v1/awards/{bid_ref}/po?version=N", "Fetches specific PO version."),
        ],
    ),

    _admin(
        "31-admin-docusign", "Admin console · DocuSign · Envelope log", "docusign",
        "Every DocuSign envelope, its status, and the authoritative flag marking the legally-binding version.",
        audience=["Ops", "Legal"],
        fields=[
            ("Envelope list", "envelope_id · recipient · subject · status · is_authoritative."),
            ("Authoritative flag", "Only ONE envelope per contract can be authoritative — enforced with a 409 on second set."),
            ("Download signed PDF", "Fetches DocuSign combined-signed PDF."),
        ],
        api=[
            ("GET", "/api/v1/docusign/envelopes", "List."),
            ("POST", "/api/v1/envelopes/{id}/mark-authoritative", "409 if already set on another envelope."),
        ],
        pitfalls=["Marking authoritative twice is intentional 409 — the second call must first unmark the first."],
    ),

    _admin(
        "32-admin-auctions", "Admin console · Reverse auctions", "auctions",
        "Live reverse auctions — draft link hidden from public, participant validation, real-time price ticker.",
        audience=["Ops", "Committee"],
        fields=[
            ("Auction list", "notice_ref · start · duration · status · participants."),
            ("+ New auction", "notice_ref + start_at + duration_min + participants list."),
            ("Participants", "Only bidders whose bid is escrow_accepted can be added — validated."),
            ("Draft link", "Not publicly visible until status=live."),
        ],
        api=[
            ("POST", "/api/v1/auctions", "Create draft."),
            ("POST", "/api/v1/auctions/{id}/start", "Flip to live."),
            ("POST", "/api/v1/auctions/{id}/bid", "Vendor-side lower-bid submission."),
        ],
    ),

    _admin(
        "33-admin-meetings", "Admin console · Meetings", "meetings",
        "Zoom / internal meeting scheduling. notice_ref required unless 'Internal meeting' toggle is on.",
        audience=["Ops", "Committee"],
        fields=[
            ("+ New meeting", "Title · date · attendees · Zoom URL (optional) · notice_ref."),
            ("Internal meeting toggle", "If ticked, notice_ref becomes optional. Used for internal ops."),
            ("Attendees", "Multi-select from staff master."),
            ("Zoom link", "Optional. If present, appears on the invite email."),
        ],
        api=[("POST", "/api/v1/meetings", "Create."), ("GET", "/api/v1/meetings", "List.")],
    ),

    _admin(
        "34-admin-l1", "Admin console · L1 comparison", "l1",
        "Lowest-compliant winner across bids. Empty-state includes 'why L1 could not be picked' reasons.",
        audience=["Evaluators", "Mgmt"],
        fields=[
            ("Notice ref input", "Pick a notice."),
            ("Comparison table", "Every bid · compliance · price · rank."),
            ("Winner banner", "PMC-BID-…-#### is L1."),
            ("Empty-state reasons", "e.g. 'No commercial envelope locked' or 'All bidders non-compliant on eligibility'."),
        ],
        api=[("GET", "/api/v1/comparison/l1/{notice_ref}", "Returns comparison + winner or empty-state reason.")],
    ),

    _admin(
        "35-admin-boq", "Admin console · BOQ & contracts", "boq",
        "BOQ templates + Contract templates with exports + versions.",
        audience=["Ops", "Accounting"],
        fields=[
            ("Sub-tabs", "BOQ templates · Contracts."),
            ("Template list", "name · version · updated_at."),
            ("Import CSV", "Import a BOQ from a spreadsheet."),
            ("Export", "PDF + XLSX export of a template."),
        ],
        api=[
            ("GET", "/api/v1/boqs/templates", "List."),
            ("POST", "/api/v1/boqs/templates", "Create."),
            ("GET", "/api/v1/boqs/templates/{id}/export?fmt=xlsx", "Export."),
        ],
    ),

    _admin(
        "35a-admin-boq-contracts", "BOQ · Contracts sub-tab", "boq",
        "Contract templates — the boilerplate clauses linked to award PO generation.",
        sub_actions=[("click", "[data-testid=boq-tab-contracts]", None)],
        fields=[
            ("Contracts table", "Template name · version · category."),
            ("+ New contract", "Free-text draft; export as .docx."),
            ("Export DOCX", "Downloads the Word doc."),
        ],
        api=[("GET", "/api/v1/contracts/templates", "List."), ("POST", "/api/v1/contracts/templates", "Create.")],
    ),

    _admin(
        "36-admin-vintel", "Admin console · Vendor Intelligence", "vintel",
        "Blacklist / whitelist / grey-list registry with a KPI decorator per vendor.",
        audience=["Ops", "Mgmt"],
        fields=[
            ("List tab", "BL · WL · Grey."),
            ("+ Add entry", "Vendor + reason + evidence link."),
            ("Legend", "BL red · WL green · Grey amber."),
            ("Vendor KPI decorator", "On the vendors master, a coloured pill from Vendor Intel."),
        ],
        api=[("GET", "/api/v1/vendor-intel", "List."), ("POST", "/api/v1/vendor-intel", "Create entry.")],
    ),

    # ─────────── Bug-fix showcases (v4) ───────────
    _admin(
        "23b-admin-vendors-status-filter", "Vendors · Status filter (V-02 fix)", "vendors",
        "Status filter dropdown lets ops jump straight to Pending-verify / Active / Inactive vendor cohorts.",
        sub_actions=[("click", "[data-testid=vendor-status-filter-pending]", None)],
        fields=[
            ("All", "Every vendor."),
            ("Pending verify", "email_verified=false — the onboarding gap."),
            ("Active", "email_verified=true AND is_active=true."),
            ("Inactive", "is_active=false — GDPR-redacted or deactivated."),
        ],
    ),
    _admin(
        "26a-admin-tender-builder-all", "Tender Builder · ALL KINDS view (T-01 fix)", "tender-builder",
        "Combined view showing tenders + RFPs + RFQs together. Useful for the master library operator.",
        sub_actions=[("click", "[data-testid=tb-kind-all]", None)],
        fields=[("ALL KINDS pill", "Toggles the sidebar to show every template regardless of kind.")],
    ),
    _admin(
        "28a-admin-escrow-reconciliation", "Escrow · Reconciliation ledger vs bank (E-03 fix)", "escrow",
        "Compares internal ledger balances against last-reported bank statements per joint account. Highlights deltas so operators can chase the escrow institution.",
        sub_actions=[("sleep", "600", None)],
        fields=[
            ("Row", "Account · currency · ledger balance · bank balance · delta · status pill."),
            ("Reconciled pill", "Green — ledger and bank match to the cent."),
            ("Delta pill", "Amber — a leg was not confirmed by the escrow institution yet."),
            ("Pending bank feed", "Grey — no bank_balance received; reconcile manually."),
        ],
    ),
    _admin(
        "32a-admin-auction-summary", "Reverse auctions · Post-auction summary (RA-01 fix)", "auctions",
        "'View summary' button on any closed auction expands a summary panel: starting/floor/winning prices + savings percentage + winner + timing.",
        sub_actions=[("click_first", "[data-testid^=ra-summary-]", None)],
        fields=[
            ("Starting / Floor", "Configured at draft time."),
            ("Winning bid", "The final downward-bid price the auction closed at."),
            ("Savings vs start", "(starting − winning) / starting × 100."),
            ("Timing", "Duration, anti-snipe, closed timestamp."),
        ],
    ),
    _admin(
        "40a-admin-audit-filter", "Audit · Filter by actor / type / date (AU-01 fix)", "audit",
        "Filter bar over the audit ledger — narrow to a single actor, event type, or date range.",
        sub_actions=[("fill", "[data-testid=audit-filter-actor]", "adminsupport"), ("sleep", "600", None)],
        fields=[
            ("Actor email", "Substring match on actor_email."),
            ("Event type", "Substring match on event_type (e.g. 'notice.publish')."),
            ("From / To (UTC)", "Date range filter."),
            ("Clear", "Resets all four filters."),
        ],
    ),
    _admin(
        "42a-admin-engagement-buyer-jump", "Engagements · Buyer jump-link (EN-03 fix)", "engagements",
        "Every buyer email in the engagement table is a jump-link that opens the Vendors tab pre-filtered by that email.",
        fields=[("Buyer email", "Dotted-underline link → /admin?tab=vendors&search=<email>.")],
    ),

    _admin(
        "37-admin-masters-staff", "Admin console · Masters · Staff", "masters",
        "Staff master — seed reviewers, escrow agents, certifiers, legal, accounting, committee, auditor.",
        audience=["Mgmt"],
        fields=[
            ("Sub-tabs", "Staff master · Companies · Tenants · Approval matrix · Hierarchy."),
            ("Staff row", "Name · email · role(s) · designation · active toggle."),
            ("+ New staff", "email + role + designation + temp password."),
            ("Reset password", "Sends a recover-token email to the staff member."),
        ],
        api=[
            ("GET", "/api/v1/masters/staff", "List."),
            ("POST", "/api/v1/masters/staff", "Create."),
            ("POST", "/api/v1/masters/staff/{id}/reset-password", "Email a reset link."),
        ],
    ),

    _admin(
        "37a-admin-masters-companies", "Masters · Companies", "masters",
        "Tenant-scoped company catalog — internal companies (departments, subsidiaries) that own contracts.",
        sub_actions=[("click", "[data-testid=masters-tab-companies]", None)],
        fields=[("Company name", "Legal name."), ("Company code", "Short code, e.g. PMC-INF."), ("+ Create", "Adds a row.")],
    ),

    _admin(
        "37b-admin-masters-matrix", "Masters · Approval matrix", "masters",
        "The dynamic approval matrix editor. Each row is a step (role + action + SLA hours).",
        sub_actions=[("click", "[data-testid=masters-tab-matrix]", None)],
        fields=[
            ("Matrix name", "Pipeline name (e.g. Standard, Fast-track)."),
            ("Row", "# · Role picker · Action text · SLA hours · move up/down · delete."),
            ("+ Add step", "Appends a new row."),
            ("Save matrix", "Persists ordering + steps."),
            ("Saved matrices", "List of all matrices with steps × applies-to."),
        ],
        tutorial=[
            ("Build a 6-step pipeline", "Escrow accept EMD → Admin flag → Certifier site inspection → Legal KYC → Accounting sign-off → Committee award. SLAs typically 24 / 24 / 72 / 48 / 24 / 168 h."),
            ("Reorder steps", "Use the up/down arrows in the Move column."),
            ("Apply to a notice", "In Notice → 'Approval matrix' → pick the matrix from this list."),
        ],
        api=[("GET", "/api/v1/masters/matrices", "List."), ("PUT", "/api/v1/masters/matrices/{id}", "Save.")],
    ),

    _admin(
        "37c-admin-masters-hierarchy", "Masters · Hierarchy", "masters",
        "Level 0..3 hierarchy — the enforcement backbone of G2 access control.",
        sub_actions=[("click", "[data-testid=masters-tab-hierarchy]", None)],
        fields=[
            ("Level 0 · Admin", "Full access — publish, approve, override."),
            ("Level 1 · Reviewer", "Draft + approve up to threshold; cannot publish."),
            ("Level 2 · Committee / Staff", "Scoped action (certify, escrow-sign, evaluate)."),
            ("Level 3 · Support / Auditor", "Read-only — no writes ever."),
        ],
    ),

    _admin(
        "37d-admin-masters-tenants", "Masters · Tenants", "masters",
        "Multi-tenant registry. Every tenant has a code + name + kind + theme.",
        sub_actions=[("click", "[data-testid=masters-tab-tenants]", None)],
        fields=[
            ("Code", "Short code (e.g. PMC, GOV-KZ, BUYR-01)."),
            ("Name", "Portal display name."),
            ("Kind", "buyer · agency · government · council."),
            ("+ Create", "Provisions a new tenant. Also seeds a default admin."),
        ],
    ),

    _admin(
        "37e-admin-masters-staff-clone", "Masters · Staff · Clone role (MP-01 fix)", "masters",
        "Every staff row has a 'Clone role' button that copies the roles + hierarchy level into the New-staff form.",
        sub_actions=[("click", "[data-testid=masters-tab-staff]", None), ("sleep", "600", None)],
        fields=[
            ("Clone role button", "Copies roles + hierarchy_level of the source row into the new-staff form (email + name + password blank for the operator to fill)."),
        ],
    ),

    _admin(
        "38-admin-permissions", "Admin console · Permissions matrix (G2)", "permissions",
        "Effective role permissions — the merged view of Permissions Matrix + Hierarchy Level.",
        audience=["Mgmt", "Ops"],
        fields=[
            ("Role picker", "Pick a role to inspect its effective permissions."),
            ("Tab × Action grid", "Every tab × every action (view / create / edit / publish / approve / delete)."),
            ("Green tick", "Allowed."),
            ("Grey cross", "Not allowed."),
            ("Hierarchy chip", "Displays the current Level for the picked role."),
        ],
        api=[
            ("GET", "/api/v1/permissions/tabs/{role}", "Tabs allowed."),
            ("GET", "/api/v1/permissions/effective/{role}", "G2 merged view."),
            ("PUT", "/api/v1/permissions/tabs/{role}", "Save grid."),
        ],
        pitfalls=["Editing this grid affects live sessions — users see the new permissions on next request (no re-login needed)."],
    ),

    _admin(
        "39-admin-packages", "Admin console · Package tracker", "packages",
        "Kanban of packages by stage. Drag a card between columns to move it forward.",
        audience=["Ops"],
        fields=[
            ("Columns", "Backlog · In progress · Review · Blocked · Done."),
            ("Card", "Package title · owner · SLA countdown · linked notice_ref."),
            ("+ New package", "Modal — title, owner, notice_ref, target date."),
            ("Card drawer", "Click any card → drawer with sub-tasks + timeline + audit log."),
        ],
        api=[("GET", "/api/v1/packages", "List."), ("POST", "/api/v1/packages/{id}/move", "Drag-drop persistence.")],
    ),

    _admin(
        "40-admin-audit", "Admin console · Audit log", "audit",
        "Every substantive action across the portal — actor · tenant · IP · user-agent · timestamp.",
        audience=["Auditor", "Mgmt"],
        fields=[
            ("Filter bar", "By actor · action type · entity · date range."),
            ("Row", "Timestamp · actor · action · entity_ref · detail JSON."),
            ("Export CSV", "Full range export."),
        ],
        api=[("GET", "/api/v1/audit?limit=100", "Paginated audit trail."), ("GET", "/api/v1/audit/export?fmt=csv", "CSV.")],
    ),

    _admin(
        "41-admin-catalog", "Admin console · Product catalog", "catalog",
        "Product / service SKU master used by the Engagements pipeline.",
        audience=["Ops", "Sales"],
        fields=[
            ("SKU row", "code · name · price · currency · active toggle."),
            ("+ New SKU", "code + name + price + currency."),
            ("Price-change history", "Every price update audit-logged with actor."),
        ],
        api=[("GET", "/api/v1/products", "List."), ("POST", "/api/v1/products", "Create.")],
    ),

    _admin(
        "42-admin-engagements", "Admin console · Engagements (quotes pipeline)", "engagements",
        "Quote requests → engagements. Aging buckets + cancel-with-reason.",
        audience=["Sales", "Ops"],
        fields=[
            ("Stage tabs", "Quote requested · Sent · Accepted · Cancelled."),
            ("Aging bucket", "0-7d · 8-14d · 15-30d · 30+d."),
            ("Cancel", "Requires reason ≥ 5 chars."),
            ("Buyer row", "Buyer name — click to jump to Vendors (Bug EN-03)."),
        ],
        api=[("GET", "/api/v1/engagements", "List."), ("POST", "/api/v1/engagements/{id}/cancel", "Body {reason}.")],
    ),

    _admin(
        "43-admin-reports", "Admin console · Reports · Asked-vs-delivered", "reports",
        "Asked-vs-delivered dashboard + printable flowcharts.",
        audience=["Mgmt"],
        fields=[
            ("Report picker", "Asked-vs-delivered · Flowcharts · Timesheet."),
            ("Chart", "Bar/line with a legend + tooltip."),
            ("Print", "Renders a print-optimised layout."),
        ],
        api=[("GET", "/api/v1/reports/asked-vs-delivered", "JSON.")],
    ),

    _admin(
        "44-admin-stakeholder", "Admin console · Stakeholder reports (G4)", "stakeholder",
        "Stakeholder-facing reports — Tenders / Awards / Escrow / SLA. Downloadable CSV per tab.",
        audience=["Mgmt", "Investor"],
        fields=[
            ("Report tabs", "Tenders · Awards · Escrow · SLA."),
            ("Table", "Report-specific columns."),
            ("Download CSV", "Full export of the current tab."),
            ("Escrow SLA banner", "Only on Escrow tab — shows the threshold config."),
        ],
        api=[
            ("GET", "/api/v1/stakeholder-reports/tenders", "JSON."),
            ("GET", "/api/v1/stakeholder-reports/awards", "JSON."),
            ("GET", "/api/v1/stakeholder-reports/escrow", "JSON + sla_threshold_days."),
            ("GET", "/api/v1/stakeholder-reports/sla", "JSON."),
        ],
    ),

    _admin(
        "45-admin-help", "Admin console · Help requests triage", "help",
        "Inbound help-form triage. Assign / resolve / close.",
        audience=["Support"],
        fields=[
            ("Request row", "Requester · subject · category · status pill."),
            ("Assign", "Pick a support user."),
            ("Resolve", "Mark resolved + attach note."),
        ],
        api=[("GET", "/api/v1/help-requests", "List."), ("POST", "/api/v1/help-requests/{id}/assign", "Body {assignee_id}.")],
    ),

    _admin(
        "46-admin-branding", "Admin console · Portal branding", "branding",
        "Per-tenant logo history + primary/secondary theme colours. Live-preview panel.",
        audience=["Mgmt"],
        fields=[
            ("Logo history", "Every uploaded logo — click to restore an old one."),
            ("Primary colour", "Hex — brand navy."),
            ("Secondary colour", "Hex — accent."),
            ("Preview panel", "Shows the top-bar + a sample button using the new theme."),
            ("Save", "Applies theme instantly to all tenant users."),
        ],
        api=[
            ("GET", "/api/v1/branding", "Current theme."),
            ("PUT", "/api/v1/branding", "Update primary/secondary + upload logo."),
        ],
    ),
]


# ═════════════════════════════════════════════════════════════════════════
# 3 · VENDOR PORTAL
# ═════════════════════════════════════════════════════════════════════════
VENDOR = [
    _P(
        slug="60-vendor-dashboard",
        title="Vendor portal · Dashboard",
        url="/vendor",
        role="vendor",
        audience=["Vendor"],
        purpose="Vendor home — Open tenders (browse + bid) · My bids · Signatures.",
        fields=[
            ("Top-bar chip", "Your vendor_ref + avatar."),
            ("Open tenders tab", "Every published notice with a 'Submit bid' CTA."),
            ("My bids tab", "Every bid you've submitted with its stage + AI compare status."),
            ("Signatures tab", "Every DocuSign envelope you need to counter-sign."),
            ("Delete my data", "GDPR forget — anonymises your account in-place."),
            ("Sign out", "Clears the vendor cookie."),
        ],
        tutorial=[
            ("Browse open tenders", "Open tenders tab → click 'Submit bid' on any card → land on /vendor/bid/new/:ref."),
            ("See a bid's stage", "My bids tab → each row shows the pipeline stage (emd_pending, escrow_accepted, admin_flagged, awarded…)."),
            ("Counter-sign an envelope", "Signatures tab → click a pending row → land on the DocuSign hosted page."),
        ],
        api=[
            ("GET", "/api/v1/vendor/auth/me", "Current vendor identity."),
            ("GET", "/api/v1/notices?public=1", "Open tenders list."),
            ("GET", "/api/v1/bids/mine", "Vendor's own bids."),
        ],
    ),
    _P(
        slug="61-vendor-change-password",
        title="Vendor · Change password",
        url="/vendor/change-password",
        role="vendor",
        audience=["Vendor"],
        purpose="Rotate the vendor password. Same rules as admin (12 / 1U / 1D / 1S).",
        fields=[
            ("Current password", "Required."),
            ("New password", "≥ 12 chars, 1 upper, 1 digit, 1 symbol."),
            ("Save", "POST /api/v1/vendor/auth/change-password."),
        ],
        api=[("POST", "/api/v1/vendor/auth/change-password", "Body {current_password, new_password}.")],
        pitfalls=["If must_change_password is true, no other route works until this succeeds."],
    ),
    _P(
        slug="62-vendor-services",
        title="Vendor · Purchase services",
        url="/vendor/services",
        role="vendor",
        audience=["Vendor"],
        purpose="Buy add-on services (KYC upgrade, priority support). Stripe checkout.",
        fields=[
            ("Service cards", "Each add-on — name · price · benefits."),
            ("Buy button", "Fires Stripe checkout session."),
            ("Currency selector", "USD · INR · KZT."),
        ],
        api=[("POST", "/api/v1/billing/checkout", "Creates Stripe session, returns URL.")],
    ),
    _P(
        slug="63-vendor-sandbox-checkout",
        title="Vendor · Sandbox checkout",
        url="/vendor/payment/sandbox",
        role="vendor",
        audience=["Vendor", "QA"],
        purpose="Test payment page (sandbox mode) — used when Stripe is not configured.",
        fields=[("Simulate success", "Redirects to /vendor/payment/success."), ("Simulate cancel", "Redirects to /vendor/payment/cancel.")],
    ),
    _P(
        slug="64-vendor-payment-success",
        title="Vendor · Payment success",
        url="/vendor/payment/success",
        role="vendor",
        audience=["Vendor"],
        purpose="Post-payment confirmation and receipt link.",
        fields=[("Receipt link", "Fetches the Stripe/sandbox receipt PDF."), ("Back to dashboard", "Return to /vendor.")],
    ),
    _P(
        slug="65-vendor-payment-cancel",
        title="Vendor · Payment cancelled",
        url="/vendor/payment/cancel",
        role="vendor",
        audience=["Vendor"],
        purpose="Cancellation notice with a retry CTA.",
        fields=[("Retry payment", "Bounces to /vendor/services."), ("Contact support", "Opens the help form.")],
    ),
    _P(
        slug="66-vendor-bid-submit",
        title="Vendor · Submit a bid",
        url=f"/vendor/bid/new/{BID_NOTICE_REF}",
        role="vendor", audience=["Vendor"],
        purpose="Bid submission form scoped to a single published notice. Captures technical + commercial envelopes and triggers Stripe checkout for the EMD.",
        fields=[
            ("Notice header", "notice_ref · title · deadline countdown."),
            ("Technical envelope", "Upload each required document (from the linked Tender Builder template)."),
            ("Commercial envelope", "BOQ line-items or a lump-sum price + currency."),
            ("EMD payment", "Fires Stripe checkout with the EMD amount configured on the notice."),
            ("Submit bid", "Persists the bid + starts the pipeline at emd_pending."),
        ],
        api=[
            ("POST", "/api/v1/bids", "Body {notice_ref, price, currency, docs:[…]}."),
            ("POST", "/api/v1/payments/emd-checkout", "Creates Stripe session for the EMD."),
        ],
        pitfalls=["Bid cannot be submitted after the notice submission_deadline — deadline is enforced server-side."],
    ),
    _P(
        slug="67-vendor-auction-room",
        title="Vendor · Reverse auction room",
        url=f"/vendor/auction/{AUCTION_AID}",
        role="vendor", audience=["Vendor"],
        purpose="Live bidding room for a reverse auction. Real-time price ticker + downward-bid + anti-snipe extensions.",
        fields=[
            ("Current lowest", "Live lowest bid from any participant, updated via WebSocket."),
            ("Time remaining", "Countdown to close. Anti-snipe extends by N seconds on last-second bid."),
            ("Bid input", "Enter next price ≤ current − min_decrement."),
            ("Autobid", "Set a floor + step to auto-bid until floor is reached."),
        ],
        api=[
            ("GET", "/api/v1/reverse-auctions/{aid}/state", "Current state (public)."),
            ("POST", "/api/v1/reverse-auctions/{aid}/bid", "Submit a manual bid."),
            ("POST", "/api/v1/reverse-auctions/{aid}/autobid", "Configure autobid."),
        ],
    ),
]


# ═════════════════════════════════════════════════════════════════════════
# 4 · STAFF PORTAL
# ═════════════════════════════════════════════════════════════════════════
STAFF = [
    _P(
        slug="70-staff-dashboard",
        title="Staff portal · Dashboard",
        url="/staff",
        role="staff",
        audience=["Staff"],
        purpose="Role-scoped task inbox. Escrow agents see pending signatures; certifiers see site-inspection tasks; legal sees KYC reviews; accounting sees sign-offs.",
        fields=[
            ("Task list", "Task type · notice_ref · SLA countdown · CTA."),
            ("Filters", "By role (if multi-role) + by status."),
        ],
        api=[("GET", "/api/v1/tasks?assignee=me", "Assigned tasks for the current staff user.")],
    ),
]


# ═════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════
async def apply_actions(page: Page, actions):
    for verb, sel, val in actions:
        try:
            if verb == "click":
                await page.click(sel, timeout=6000)
            elif verb == "click_first":
                loc = page.locator(sel).first
                await loc.click(timeout=6000)
            elif verb == "fill":
                await page.fill(sel, val, timeout=6000)
            elif verb == "select":
                await page.select_option(sel, val, timeout=6000)
            elif verb == "wait_for":
                await page.wait_for_selector(sel, timeout=6000)
            elif verb == "sleep":
                await page.wait_for_timeout(int(sel))
            await page.wait_for_timeout(900)
        except Exception as e:
            print(f"    ! action {verb} {sel} skipped: {e}")


async def shot(page: Page, slug: str, full_page: bool = True):
    p = OUT / f"{slug}.png"
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    await page.screenshot(path=str(p), full_page=full_page)
    kb = p.stat().st_size // 1024
    print(f"  ✓ {slug}.png ({kb} KB)")
    return p


async def login_admin(page: Page):
    print("[auth] logging in as admin")
    await page.goto(f"{BASE}/admin/login", wait_until="domcontentloaded", timeout=25000)
    await page.wait_for_timeout(1800)
    await page.fill('[data-testid=admin-login-email]', ADMIN_EMAIL, timeout=8000)
    await page.fill('[data-testid=admin-login-password]', ADMIN_PASS, timeout=8000)
    await page.click('[data-testid=admin-login-submit]', timeout=8000)
    await page.wait_for_url(lambda u: "/admin" in u, timeout=15000)
    await page.wait_for_timeout(2500)
    print("  ✓ admin logged in")


async def logout(page: Page):
    try:
        await page.click('[data-testid=admin-logout]', timeout=6000)
        await page.wait_for_timeout(2000)
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════════════════
# MAIN CAPTURE
# ═════════════════════════════════════════════════════════════════════════
async def capture_group(page: Page, group: list[dict], manifest: list[dict], tag: str):
    for spec in group:
        url = spec["url"] if spec["url"].startswith("http") else f"{BASE}{spec['url']}"
        print(f"[{tag}] {spec['slug']}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(spec.get("wait_ms", 1600))
            await apply_actions(page, spec["actions"])
            await shot(page, spec["slug"], spec["full_page"])
            manifest.append({**spec, "image": f"{spec['slug']}.png"})
        except Exception as e:
            print(f"  ✗ {spec['slug']} failed: {e}")


async def capture():
    manifest: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport=VIEWPORT)
        page = await ctx.new_page()

        # Public
        await capture_group(page, PUBLIC, manifest, "public")

        # Admin
        await login_admin(page)
        # Land on the admin console once
        await page.goto(f"{BASE}/admin", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2500)

        for spec in ADMIN:
            print(f"[admin] {spec['slug']}")
            try:
                # Ensure we're on /admin so tab clicks work
                if "/admin" not in page.url:
                    await page.goto(f"{BASE}/admin", wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(1500)
                await apply_actions(page, spec["actions"])
                await shot(page, spec["slug"], spec["full_page"])
                manifest.append({**spec, "image": f"{spec['slug']}.png"})
            except Exception as e:
                print(f"  ✗ {spec['slug']} failed: {e}")

        # Stakeholder sub-tabs
        for sub in ["tenders", "awards", "escrow", "sla"]:
            slug = f"44-{sub}-stakeholder"
            print(f"[admin] {slug}")
            try:
                try:
                    await page.click('[data-testid=admin-tab-stakeholder]', timeout=5000)
                    await page.wait_for_timeout(1800)
                except Exception:
                    pass
                try:
                    await page.click(f'[data-testid=stakeholder-tab-{sub}]', timeout=5000)
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass
                await shot(page, slug, True)
                manifest.append({
                    "slug": slug,
                    "title": f"Stakeholder reports · {sub.title()}",
                    "url": f"{BASE}/admin?tab=stakeholder&sub={sub}",
                    "role": "admin", "tab": "stakeholder",
                    "purpose": f"Stakeholder-facing {sub} report table.",
                    "image": f"{slug}.png",
                    "fields": [], "tutorial": [], "api": [], "pitfalls": [], "errors": [],
                })
            except Exception as e:
                print(f"  ✗ {slug} failed: {e}")

        await logout(page)

        # Vendor
        print("[auth] vendor login")
        vendor_ok = False
        try:
            await page.goto(f"{BASE}/vendor/login", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(1500)
            await page.fill('[data-testid=vendor-login-email]', VENDOR_EMAIL, timeout=6000)
            await page.fill('[data-testid=vendor-login-password]', VENDOR_PASS, timeout=6000)
            await page.click('[data-testid=vendor-login-submit]', timeout=6000)
            await page.wait_for_timeout(3000)
            if "/vendor" in page.url and "login" not in page.url:
                vendor_ok = True
                print("  ✓ vendor logged in")
        except Exception as e:
            print(f"  ! vendor login skipped: {e}")

        await capture_group(page, VENDOR, manifest, "vendor")

        # Staff
        print("[auth] staff login")
        try:
            await page.goto(f"{BASE}/staff/login", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(1500)
            await page.fill('[data-testid=staff-login-email]', STAFF_EMAIL, timeout=6000)
            await page.fill('[data-testid=staff-login-password]', STAFF_PASS, timeout=6000)
            try:
                await page.select_option('[data-testid=staff-login-role]', STAFF_ROLE, timeout=4000)
            except Exception:
                pass
            await page.click('[data-testid=staff-login-submit]', timeout=6000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  ! staff login skipped: {e}")

        await capture_group(page, STAFF, manifest, "staff")

        await browser.close()

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    print(f"\n=== CAPTURED {len(manifest)} screens → {OUT} ===")
    return manifest


if __name__ == "__main__":
    asyncio.run(capture())
