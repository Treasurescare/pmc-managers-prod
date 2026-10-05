"""Master Training Manual v2 — deep-dive edition.

Core modules (16 chapters) each expand into six subsections:
  · Screens & fields
  · Step-by-step tutorial
  · API reference
  · Common pitfalls
  · QA test cases (expanded)
  · Governance & KPIs

Non-core modules keep the compact v1 layout.

Outputs:
  /app/deliverables/PMC_Master_Training_Manual_v2.docx
  /app/deliverables/PMC_Master_Training_Manual_v2.pdf   (LibreOffice CLI)
"""
import subprocess
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

SCREENSHOT_DIR = Path("/app/deliverables/manual_screenshots")
OUT_DOCX = Path("/app/deliverables/PMC_Master_Training_Manual_v2.docx")
OUT_PDF = Path("/app/deliverables/PMC_Master_Training_Manual_v2.pdf")

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
NAVY_SOFT = RGBColor(0x5B, 0x7B, 0xA1)
GREY = RGBColor(0x64, 0x74, 0x8B)

TITLE = "PMC Managers v2 — Master Training Manual"
SUBTITLE = "Deep-dive edition · v2 · Operations · QA · Management"
GENERATED = datetime.utcnow().strftime("%B %d, %Y")


# ============================================================
# DEEP-DIVE CORE CHAPTERS
# ============================================================
CORE = [
    # ---------- 1 · Access, Roles & Login ----------------------
    {
        "title": "Access, Roles & Login",
        "purpose": "Every user, every login path, every access rule.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "05_admin-login-page.png",
        "overview": (
            "PMC Managers v2 is a multi-tenant global tender platform. Every user "
            "authenticates through the same URL and lands on the console that matches "
            "their role. Admin uses HTTPOnly cookie + CSRF double-submit; vendor and "
            "public flows use short-lived resume tokens sent by email."
        ),
        "screens": [
            ("/admin/login — admin card", "Email + password + a two-line brand kicker. Failed attempts show inline error under the password field. Cookie set on success is Secure + SameSite=Lax + HTTPOnly."),
            ("/login — unified", "Two-card selector: 'I'm an admin' (opens /admin/login) or 'I'm a vendor' (opens /register or resume flow). The card the user clicks is remembered in localStorage for their next visit."),
            ("Top-right avatar menu", "Shows the logged-in email, role badge, tenant name, and a Sign-out button. Clicking the avatar reveals 'Profile' + 'Change password'."),
        ],
        "tutorial": [
            ("Log in as Master Admin", "Open https://www.pmcmanagers.com/admin/login → email adminsupport@pmcmanagers.com → password Admin@12345 → Sign in. You land at /admin?tab=analytics within 1s."),
            ("Log in as Reviewer / Sub-admin", "Same URL, but with a reviewer role account (e.g. madhavi@pmcmanagers.com). Publish checkbox on Notices is grayed out — reviewers save drafts only."),
            ("Log in as Vendor", "Public site → 'Sign in' → vendor card → email + password → land on /vendor. Vendors only see their own bids and profile."),
            ("Change password", "Avatar menu → Change password → enter old + new (min 12 chars, 1 upper, 1 digit, 1 symbol) → Save. Session cookie is rotated."),
            ("Recover forgotten password", "Login card → 'Forgot password' → email address → recover-token email → click link → set new password. Token TTL 30 min."),
        ],
        "api": [
            ("POST", "/api/v1/auth/login", "Body {email, password}. 200 sets HTTPOnly cookie 'pmc_admin' + returns {role, email, tenant_id}. 401 on wrong creds. 429 after 5 failed attempts (15 min lockout)."),
            ("POST", "/api/v1/auth/logout", "Clears cookie. Always 204."),
            ("GET", "/api/v1/me", "Returns the current admin's identity + role + tenant. Used by every panel to gate UI."),
            ("POST", "/api/v1/auth/forgot", "Body {email}. Always 204 (no email-enumeration leak). If email exists, a recover-token is sent."),
            ("POST", "/api/v1/auth/reset", "Body {token, new_password}. 200 on success + auto-login."),
        ],
        "pitfalls": [
            "Do NOT store credentials in the URL — session tokens are cookie-only.",
            "If you see 401 on a specific tab, first hit /api/v1/me to confirm the cookie is still valid before assuming a permission bug.",
            "Password reset emails only work if the tenant has a Resend key configured. Absence of the email usually means EMAIL_KEY isn't propagated to the Docker container.",
        ],
        "qa": [
            {"step": "Login with wrong password 5 times", "expected": "6th attempt returns HTTP 429 with a Retry-After header", "testid": "admin-login-submit"},
            {"step": "Login with correct credentials", "expected": "Redirects to /admin within 1s; /api/v1/me returns 200 with role", "testid": "admin-login-submit"},
            {"step": "Reload after login", "expected": "Session persists via HTTPOnly cookie; no re-auth needed", "testid": "admin-topbar"},
            {"step": "Sign out then hit /admin directly", "expected": "Bounce back to /login; /api/v1/me returns 401", "testid": "admin-logout"},
            {"step": "Password reset with expired token", "expected": "HTTP 400 'token expired or invalid'", "testid": "auth-reset"},
        ],
        "mgmt": [
            "Nine role types: Admin, Reviewer, Escrow, Certifier, Legal, Accounting, Committee, Support, Auditor.",
            "Access-control merges Permissions Matrix + Hierarchy Level via GET /api/v1/permissions/effective/{role}.",
            "Level 0 = Admin → Level 3 = Support/Auditor (read-only).",
            "Every login is audit-logged: actor, IP, user-agent, timestamp.",
            "Session TTL 12h with sliding renewal on activity; hard-limit 30 days regardless of activity.",
        ],
    },

    # ---------- 2 · Vendor Registration & KYC ------------------
    {
        "title": "Vendor Registration & KYC",
        "purpose": "5-section wizard that captures identity, structure, financials, docs, references.",
        "users": ["Ops", "QA"],
        "image": "03_vendor-registration-—-start.png",
        "overview": (
            "Vendors self-register through a 5-section wizard (A Identity, B Structure, "
            "C Financials, D Documents, E References). As soon as any field is filled a "
            "silent draft is created + a resume link is emailed. Vendors can pause and come "
            "back via /register/status with the resume token."
        ),
        "screens": [
            ("Section A · Identity", "Company legal name (≥3 chars), primary contact name, primary contact email (RFC-5322), primary contact phone (E.164), country (ISO-3166 alpha-2). Country drives the KYC document catalog in Section D."),
            ("Section B · Structure", "Legal form (LLC/Pvt Ltd/Public Ltd/Partnership/Sole Prop), incorporation date, number of employees, main office address, subsidiaries table."),
            ("Section C · Financials", "Last 3 years of revenue (yearly rows), currency, net-profit margin, audited-accounts uploads. Aggregation feeds L1 Comparison technical scoring."),
            ("Section D · Documents", "Country-specific KYC pack. India: PAN, GST cert, MSME (optional), CIN. UK: Companies House number, VAT cert. Every slot is an optional/required tag."),
            ("Section E · References", "Up to 3 client references. Each reference is a mini-form: name, company, email, phone, project value. On approval, a reachback email is sent to each reference."),
        ],
        "tutorial": [
            ("Start a draft", "Open /register → Section A → fill company name, contact, email, country → click Save & continue. A resume link email is sent to the primary contact within 30s. The URL bar now shows /register/section-b."),
            ("Pause + resume", "Close the tab. Email arrives with a 24-char URL-safe resume token. Click it → land on /register/section-b with all fields prefilled."),
            ("Upload a KYC doc", "Section D → click the PAN slot → pick a PDF ≤10MB → progress bar → 'Uploaded' green tick. File is stored server-side with a UUID reference; the vendor never sees the raw file URL."),
            ("Submit for review", "Section E → 'Submit for review'. Backend validates every required field; missing fields open a red banner with a jump link. On success, status becomes 'submitted' and admin is notified."),
            ("Handle a clarification request", "If admin sends a Request-Clarification, vendor receives an email with a note (≥5 chars). Vendor uses the same resume token; the previous submission is retained and augmented."),
        ],
        "api": [
            ("POST", "/api/v1/registrations/start", "Body {section_a fields}. Returns {registration_id, resume_token}. Idempotent by primary email."),
            ("PATCH", "/api/v1/registrations/{id}", "Partial update with token in header 'X-Resume-Token'. Merges into the draft."),
            ("POST", "/api/v1/registrations/{id}/uploads", "Multipart file upload. Returns {slot, uuid}. Slot is one of: pan, gst, msme, cin, vat, incorporation, audit_yN, other."),
            ("POST", "/api/v1/registrations/{id}/submit", "Freezes the draft and moves status → 'submitted'."),
            ("GET", "/api/v1/registrations/status?token=…", "Public — returns current stage + reviewer notes."),
        ],
        "pitfalls": [
            "The resume token in the email is the ONLY way for a vendor to come back. Losing the email means starting over; admin can re-issue via 'Nudge Stale Drafts'.",
            "KYC docs are country-scoped. A vendor whose country changes mid-registration will see a new document catalog; existing uploads are preserved but tagged 'legacy'.",
            "Bulk Invite CSV uses primary email as the dedupe key. Duplicate rows return per-row 409 in the response array without aborting the whole import.",
        ],
        "qa": [
            {"step": "Section A missing country", "expected": "HTTP 400 'country required'; frontend highlights field", "testid": "reg-section-a-submit"},
            {"step": "Upload 15 MB PDF to KYC slot", "expected": "HTTP 413 'file too large — max 10 MB'", "testid": "reg-upload-kyc"},
            {"step": "Paste invalid token at /register/status", "expected": "Toast 'Token invalid or expired' (Bug 7)", "testid": "status-token"},
            {"step": "Submit with Section D empty", "expected": "HTTP 400 with per-slot error array pointing to missing required KYC docs", "testid": "reg-submit"},
            {"step": "Malformed Bulk Invite CSV row 5 of 20", "expected": "19 rows succeed, row 5 returns 409 in response array", "testid": "vendors-bulk-invite-csv"},
        ],
        "mgmt": [
            "GDPR-compliant: KYC docs stored server-side with tenant-scoped ACL.",
            "Draft-to-submitted conversion KPI is on the Vendors card in Stakeholder Reports.",
            "Rejected registrations require a reason ≥5 chars; the reason is surfaced to the vendor in the outbound email.",
            "Retention: submitted+approved records retained indefinitely; rejected drafts purged after 90 days.",
        ],
    },

    # ---------- 3 · Notices Admin ------------------------------
    {
        "title": "Notices Admin",
        "purpose": "Create, publish, filter and manage every tender / RFP / RFQ.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "09_notices.png",
        "overview": (
            "The single source of truth for a live tender. Notices link to a Tender Builder "
            "template, drive the public notice board, and gate every downstream flow (bids, "
            "escrow, awards). Reviewers save drafts; only Master Admin publishes."
        ),
        "screens": [
            ("New Notice wizard", "Title (≥3 chars), Description (≥10 chars), Category, Delivery Country, Submission Deadline, Budget Amount (ge=0), Budget Currency (ISO-4217), Document type (tender/RFP/RFQ), Tender Template link."),
            ("Filter bar", "Search box (matches title/notice_ref, case-insensitive), Status dropdown (any/published/draft/expired), Template-linked-only toggle, Clear button."),
            ("Notice row", "Title + notice_ref + budget pill + deadline date on right + template-linked badge. Click opens the detail drawer with bidders, corrigenda, and audit slice."),
        ],
        "tutorial": [
            ("Create a draft notice", "Notices → '+ New notice'. Fill Title 'North-East Highway BOT'. Description ≥10 chars. Category = Construction. Country = IN. Submission deadline = today + 30 days. Budget 500000000 INR. Document type = tender. Save without ticking Publish → status='draft'."),
            ("Attach a Tender Builder template", "Open the draft → 'Pick template' → search 'GFR 2017 QCBS 70/30' → Attach. tender_template_id now set; badge appears on the row."),
            ("Publish (Master Admin only)", "Toggle 'Publish immediately' → Save. Status → published, published_at stamped, all subscribed bidders receive notification, public notice board updates within 60s."),
            ("Filter to overdue drafts", "Status = draft, Search empty. Look at 'Days since created' column — anything >5 days is a candidate for review."),
            ("Amend after publish (use Corrigenda)", "You cannot edit a published notice. Instead → Corrigenda tab → '+ New' → describe the amendment → optional new deadline → Publish. Notifications go out."),
        ],
        "api": [
            ("POST", "/api/v1/notices", "Create draft. reviewer.create=True (Bug 5 fix), so sub-admins can save drafts without 403."),
            ("PATCH", "/api/v1/notices/{ref}", "Partial update. Locked once is_published=true (use corrigenda instead)."),
            ("POST", "/api/v1/notices/{ref}/publish", "Requires admin role + publish permission on Notices."),
            ("GET", "/api/v1/notices?status=&country=&limit=", "Public list; admin sees drafts too."),
        ],
        "pitfalls": [
            "Budget_amount validates ge=0 — negative values return 400 (Bug 4 fix).",
            "You cannot delete a published notice; only issue corrigenda.",
            "notice_ref format is `PMC-NOT-YYYY-####`; the sequence is per-tenant per-year.",
        ],
        "qa": [
            {"step": "Publish with budget_amount = -1", "expected": "HTTP 400 (NoticeIn validates ge=0)", "testid": "notices-form-submit"},
            {"step": "Reviewer saves draft", "expected": "HTTP 200; reviewer.create=True (Bug #5 fix); no 'undefined' toast", "testid": "notices-form-submit"},
            {"step": "Filter Template-linked only", "expected": "List narrows to notices with tender_template_id set", "testid": "notices-filter-template-only"},
            {"step": "Filter status=expired", "expected": "List narrows to notices where submission_deadline < now()", "testid": "notices-filter-status"},
            {"step": "Non-admin tries to publish", "expected": "HTTP 403 'insufficient permissions to publish'", "testid": "notices-publish-checkbox"},
        ],
        "mgmt": [
            "Every publish is audited: actor + tenant + notice_ref + timestamp.",
            "KPI: notices-published-per-month per tenant; median time from creation to publish.",
            "Currency defaults to tenant primary but supports any ISO 4217 code.",
        ],
    },

    # ---------- 4 · Corrigenda ---------------------------------
    {
        "title": "Corrigenda",
        "purpose": "Formal amendments to published tenders — every change is auditable.",
        "users": ["Ops", "Mgmt"],
        "image": None,
        "overview": (
            "Corrigenda re-open the bidder window after a tender is public. Every "
            "corrigendum has an auto-number (`PMC-COR-YYYY-####`), a mandatory reason "
            "≥8 chars, and can reset the submission deadline. Withdrawal is capped at 3 "
            "per notice."
        ),
        "screens": [
            ("New Corrigendum modal", "Parent notice (auto-linked from the Notice detail), Amendment description (≥8 chars), New deadline (optional, must be > now)."),
            ("Corrigenda list", "Per-notice list showing: number, reason snippet, published_at, deadline change, actions (Withdraw, View)."),
            ("Withdraw dialog", "Requires a reason (≥8 chars) captured to audit log."),
        ],
        "tutorial": [
            ("Issue a corrigendum", "Open a published notice → Corrigenda tab → '+ New'. Description: 'Extended submission window from Nov 30 to Dec 14 due to holiday season' (54 chars). New deadline: 2026-12-14. Publish. Bidders receive email + banner on public notice."),
            ("Withdraw a corrigendum", "Corrigenda row → '✕ Withdraw'. Reason: 'issued in error, correct clause was updated elsewhere' (55 chars). Backend logs to audit. Public list hides the corrigendum but admin can still see it (is_active=false)."),
            ("Reach the limit", "By the 4th corrigendum on the same notice, '+ New' returns HTTP 400 'withdrawal capped at 3 per notice' — pattern is designed to force cleanup + re-publish rather than corrigendum-spam."),
        ],
        "api": [
            ("POST", "/api/v1/corrigenda", "Body {notice_ref, description, new_deadline}. Backend validates reason≥8, new_deadline > now."),
            ("POST", "/api/v1/corrigenda/{id}/withdraw", "Body {reason}. reason ≥8 chars enforced."),
            ("GET", "/api/v1/corrigenda?notice_ref=…", "Public sees is_active=true; admin sees all."),
        ],
        "pitfalls": [
            "Withdrawal reason is captured to audit log AND surfaced in the public 'History' expander on the notice page — write it as if a lawyer will read it.",
            "The 3-corrigenda cap is a hard limit. If you need more amendments, close the notice and re-publish with a new notice_ref.",
        ],
        "qa": [
            {"step": "Withdraw with 3-char reason", "expected": "HTTP 400 'reason must be at least 8 characters'", "testid": "corrigenda-withdraw"},
            {"step": "4th corrigendum on a notice with 3", "expected": "HTTP 400 'withdrawal capped at 3 per notice'", "testid": "corrigenda-create"},
            {"step": "New deadline in the past", "expected": "HTTP 400 'new_deadline must be in the future'", "testid": "corrigenda-form-submit"},
            {"step": "Publish corrigendum", "expected": "audit_log entry with reason + all subscribed bidders receive email", "testid": "corrigenda-publish"},
        ],
        "mgmt": [
            "Legal-grade audit: reason text is preserved on the notice record + audit log forever.",
            "Corrigenda count is a red-flag KPI — high count per notice indicates poor initial drafting; surfaced on Stakeholder Reports / Tenders.",
        ],
    },

    # ---------- 5 · Tender Builder (DEEP DIVE) -----------------
    {
        "title": "Tender Builder",
        "purpose": "Compose 30+ page tenders from orderable sections + annexures.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "11_tender-builder.png",
        "overview": (
            "Master templates ship for GFR 2017 QCBS 70/30 (India), FIDIC Red Book "
            "(international), and a blank template. Clone a master into a draft, fill "
            "each section with the rich editor, attach annexures via drag-drop, preview "
            "+ export via WeasyPrint. Every save writes a rolling snapshot (max 20) so "
            "you can revert. Restore is itself snapshotted (undoable)."
        ),
        "screens": [
            ("Left sidebar — Kind tabs + template list",
             "Three tabs: Tender / RFP / RFQ. Each shows the master templates (locked) at the top and drafts below (sortable). Sidebar shows Kind badge, updated_at timestamp, and current version number. Bug 31c fix: switching Kind clears the right pane so you don't accidentally edit a different draft."),
            ("Header pane — Basic details",
             "Title, Reference number (auto), Issuing authority, Estimated value + currency, EMD amount, EMD form (bank guarantee / DD / online), Critical dates (issue / pre-bid / submission / opening)."),
            ("Section editor",
             "Rich editor (bold, italic, lists, block-quote, tables). Each section has an ordering handle, ✨ AI Draft menu, and a lock toggle. Word count in bottom-right."),
            ("Annexure uploader",
             "Drag many files at once — filenames auto-match to the numbered annexure slots (annex-VIII_bank.pdf → Annexure VIII, longest-code wins). Preview inline. Right-click → 'Replace' or 'Detach'."),
            ("Version history drawer (⟲)",
             "Chronological list of up to 20 snapshots per draft. Each row shows: version #, saved_by, saved_at, section-count. Preview or Restore. Restore creates snapshot v+1 (undoable)."),
            ("Preview / Export",
             "Preview opens a WeasyPrint HTML render in a modal. Export gives PDF (with DRAFT watermark until published) + DOCX + language-pack switch EN/RU/KK."),
        ],
        "tutorial": [
            ("Clone a master into a draft",
             "Left column → Kind tab 'Tender' → find 'GFR 2017 QCBS 70/30' master → click Clone. A 'Draft 2026-09-04' appears below the masters. Click to open."),
            ("Fill the header",
             "Header pane → Title 'North-East Highway BOT — QCBS 70/30'. Reference: leave auto. Authority: 'NHAI'. Estimated value: 5 000 000 000 INR. EMD: 25 000 000 INR. Bank guarantee. Critical dates: fill the four ISO dates."),
            ("Draft Section 1 · Scope of work",
             "Click Section 1 → paste your scope text or click ✨ AI Draft → tone=formal, length=medium → preview → Insert. The AI shows a word-diff so you know exactly what would change if the section already had content."),
            ("Bulk-attach annexures",
             "Annexure pane → drag 12 PDFs at once (annex-I_boq.pdf, annex-II_form.pdf, …). System auto-matches based on filename; unmatched files go to an 'unassigned' tray for manual placement. Longest code wins, so 'annex-VIII' beats 'annex-V'."),
            ("Reorder sections",
             "Hold the ⋮ handle and drag Section 6 above Section 5. The order number auto-updates. Every section knows its position — Table of Contents regenerates on save."),
            ("Snapshot + restore",
             "Save the draft (Cmd+S). Version count → 1. Save again after changing Section 3 — version 2. Open ⟲ drawer → Preview v1 → confirm → Restore. Version 3 appears (restore is itself a snapshot). Original v1 + v2 remain."),
            ("Export & watermark",
             "Export → PDF. If the tender is still a draft (or its associated notice is not is_published), a diagonal 'DRAFT — CONFIDENTIAL' watermark is embedded on every page. Watermark disappears when the notice publishes."),
            ("Language switch",
             "Export → Language pack: Russian → the labels ('SECTION 1 · SCOPE OF WORK', page footer, ToC) render in Russian. Section body text is NOT translated — that's a copy-writing task."),
        ],
        "api": [
            ("POST",  "/api/v1/tender-templates/{master_id}/clone", "Returns {draft_id}. Draft inherits the master's sections + annexures + header defaults."),
            ("PATCH", "/api/v1/tender-templates/{draft_id}", "Partial update. Backend snapshots the pre-change state to versions[] with a max of 20 rolling entries."),
            ("GET",   "/api/v1/tender-templates/{draft_id}/versions", "Returns the versions[] list oldest→newest."),
            ("POST",  "/api/v1/tender-templates/{draft_id}/restore/{version}", "Restore a snapshot. Backend writes a NEW snapshot before the restore so the operation is undoable."),
            ("POST",  "/api/v1/tender-templates/{draft_id}/annexures/bulk", "Multipart file batch. Body includes filename-array; backend runs the longest-code auto-match."),
            ("POST",  "/api/v1/tender-templates/{draft_id}/ai-draft", "Body {section_id, tone, length}. Returns generated text + a HTML word-diff string the frontend renders."),
            ("GET",   "/api/v1/tender-templates/{draft_id}/export?format=pdf|docx&lang=en|ru|kk", "Streams the rendered file with Content-Disposition: attachment."),
        ],
        "pitfalls": [
            "Snapshots are per-draft. Cloning a master into a new draft resets the version counter to 1.",
            "AI Draft respects the tenant's PMC AI key budget. If the key runs out mid-generation, the response is truncated and the frontend shows an 'AI budget low' banner — top up under Profile → AI Key.",
            "Bulk annexure upload dedupes by (annexure_slot, filename). Uploading annex-I.pdf twice replaces the previous file silently — check the History drawer to recover.",
            "Kind tab switching resets the right pane (Bug 31c). If you had unsaved changes, they are LOST — the sidebar's 'unsaved' dot serves as the reminder.",
            "Section locking is per-section (not per-user). A locked section can be unlocked by any admin — this is a soft warning, not a hard permission gate.",
            "PDF export uses WeasyPrint. Very long tables (>1000 rows) may hit the memory limit — split into multiple annexures.",
        ],
        "qa": [
            {"step": "Clone a master and immediately save without edits", "expected": "Version 1 stamped; snapshot preserves the master's original content", "testid": "tender-clone"},
            {"step": "Save section body 3 times", "expected": "Version count = 3; History drawer shows 3 rows with distinct updated_at", "testid": "tender-section-save"},
            {"step": "Switch Kind tab with unsaved changes", "expected": "Right pane resets; selectedId cleared; toast warns of unsaved loss (Bug 31c)", "testid": "tender-kind-tab"},
            {"step": "Bulk upload 5 files matching Annexures I-V", "expected": "All 5 auto-attach to correct slots; unassigned tray empty", "testid": "tender-annex-bulk"},
            {"step": "Bulk upload file named 'annex-VIII_stub.pdf' alongside 'annex-V_full.pdf'", "expected": "annex-VIII goes to slot VIII (longest code wins); annex-V goes to slot V", "testid": "tender-annex-bulk"},
            {"step": "Restore version 1 after making 5 changes", "expected": "Content reverts; version 6 is created with 'restored from v1' note", "testid": "tender-restore"},
            {"step": "Export PDF while linked notice is draft", "expected": "PDF has diagonal DRAFT watermark on every page", "testid": "tender-export-pdf"},
            {"step": "Publish the linked notice; re-export PDF", "expected": "Watermark absent; PDF is 'production' grade", "testid": "tender-export-pdf"},
            {"step": "AI Draft on a locked section", "expected": "HTTP 409 'section is locked'; frontend shows red banner", "testid": "tender-ai-draft"},
            {"step": "Save on the 21st edit", "expected": "Version 21 replaces version 1 (rolling cap of 20 preserved)", "testid": "tender-section-save"},
        ],
        "mgmt": [
            "Language pack ships EN / RU / KK labels through WeasyPrint templates.",
            "Section-level auditor role can veto a section without unlocking the entire draft — writes to audit + notifies drafter.",
            "KPI: average edit-cycle length per template; teams with > 40 edits per template may need training.",
            "AI usage per tenant is tracked and charged against the Universal Key budget — Profile → Universal Key → 'View usage' shows a per-day chart.",
            "Master templates are versioned separately — updating a master does NOT retroactively touch existing drafts.",
        ],
    },

    # ---------- 6 · Bidding Ops · Pipeline ---------------------
    {
        "title": "Bidding Ops · Pipeline",
        "purpose": "Track every bid through the multi-role approval pipeline.",
        "users": ["Ops", "QA"],
        "image": "12_bidding.png",
        "overview": (
            "The pipeline: EMD → Escrow → Admin flag → Certifier → Legal → Accounting → "
            "Committee. Each role clears their stage. Stuck bids surface in the daily "
            "audit digest. Rejection at any stage requires a note ≥10 chars."
        ),
        "screens": [
            ("Status filter chips", "Chips across the top: submitted / emd_paid / admin_flagged / certified / legal_cleared / accounting_ok / committee_approved / awarded / rejected. Multi-select allowed."),
            ("Bid row", "Vendor + notice_ref + current status pill + price + submitted_at. Click opens the timeline drawer with every stage transition."),
            ("Assign Certifier modal", "Certifier dropdown (users with role=certifier), date + location, notes ≥5 chars. Creates an inspection record + dispatches an email with signed accept-link."),
            ("Reject dialog", "Note ≥10 chars; captured to bid.reject_reason + audit log."),
        ],
        "tutorial": [
            ("Assign a certifier", "Bid row (status=admin_flagged) → Assign → pick certifier → set date + location → note ≥5 chars → Save. Certifier receives an email; bid status advances to 'certifier_assigned'."),
            ("Advance a bid to Committee", "Sequential clears: certifier → Legal (checkbox 'Legal clearance done') → Accounting ('EMD reconciled') → Committee ('Formation complete'). Each is a distinct role."),
            ("Reject at accounting stage", "Bid → Reject → note '10-char reason for rejection at accounting stage'. Vendor is emailed with the note. Downstream stages disabled."),
            ("Handle a stuck bid", "Any bid stuck > 7 days at one stage triggers a daily digest email to admin. Open the audit slice via the bid detail drawer to see who to nudge."),
        ],
        "api": [
            ("POST", "/api/v1/bids/{ref}/advance", "Body {to_stage, notes}. Requires the role that gates that stage; role gate is defined in Permissions Matrix."),
            ("POST", "/api/v1/bids/{ref}/reject", "Body {reason}. reason ≥10 chars."),
            ("POST", "/api/v1/bids/{ref}/assign-certifier", "Body {certifier_id, date, location, notes}."),
            ("GET",  "/api/v1/bids?status=&notice_ref=", "Filter + list."),
        ],
        "pitfalls": [
            "The stage sequence is strict — you cannot skip from admin_flagged straight to committee_approved. The advance API returns HTTP 400 'invalid stage transition' otherwise.",
            "Committee stage requires a formed + open committee for the notice (see Committee chapter).",
            "Reject reason is surfaced verbatim to the vendor — keep it professional.",
        ],
        "qa": [
            {"step": "Reject with 5-char note", "expected": "HTTP 400 'note must be at least 10 characters'", "testid": "bid-reject"},
            {"step": "Skip legal_cleared → committee_approved", "expected": "HTTP 400 'invalid stage transition'", "testid": "bid-advance"},
            {"step": "Assign certifier without notes", "expected": "HTTP 400 'notes required'", "testid": "assign-certifier"},
            {"step": "Advance to committee without a committee", "expected": "HTTP 400 'form a committee first for this notice'", "testid": "bid-advance"},
        ],
        "mgmt": [
            "Every stage transition is audited (actor + prev + next + notes).",
            "KPI: median bid cycle-time (submitted → awarded), per tenant, per category.",
            "SLA: > 7 days at any single stage triggers daily nudges.",
        ],
    },

    # ---------- 7 · Bidding Ops · Committee --------------------
    {
        "title": "Bidding Ops · Committee",
        "purpose": "Form evaluation committees with chair + members + quorum + external invitees.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "12_bidding.png",
        "overview": (
            "One open committee per notice. Members are picked via checkbox grid. Chair "
            "dropdown auto-filters to selected members. Quorum caps at ≤ member count. "
            "External invitees receive email invites with signed accept-tokens. Committee "
            "can be dissolved with a reason ≥8 chars, and per-invitee 'Resend' buttons "
            "regenerate the accept-token (voiding the old one)."
        ),
        "screens": [
            ("Committee form", "Notice ref (auto from tab), Chair dropdown, Quorum input (max = ticked members), Member checkbox grid (staff + email + role/designation), External invitee sub-form."),
            ("Active committees card", "Grid of open committees for the current notice. Shows: notice_ref, internal count, quorum, status, external accept/decline/pending counts, action buttons (Dissolve, per-external Resend)."),
            ("External invitee row", "Name + email + designation, status pill (invited/accepted/declined), 'Resend' button if not accepted."),
        ],
        "tutorial": [
            ("Form a committee", "Bidding Ops → Committee tab → New form. Tick 4 members → chair dropdown auto-narrows to those 4 → pick chair. Quorum caps at 4; type 3. Save → committee status='open'."),
            ("Add an external invitee", "External sub-form → name/email/designation → Add. Multiple invitees can be added before saving the committee. Each gets a URL-safe accept-token."),
            ("Dissolve committee", "Active committees card → Dissolve button → reason ≥8 chars → OK. Committee status='dissolved' + reason logged to audit. Bids on this notice cannot be scored until a new committee is formed."),
            ("Resend a pending invite", "External invitee row → Resend. New accept-token generated; old link now returns 404. Email dispatched. Audit entry logged."),
        ],
        "api": [
            ("POST", "/api/v1/committees", "Body {notice_ref, chair, member_ids[], quorum, external_invitees[]}. Validates chair ∈ member_ids; quorum ≤ len(member_ids)."),
            ("POST", "/api/v1/committees/close", "Body {committee_id, decision, remarks}. decision='dissolved' requires remarks ≥8 chars (v17)."),
            ("POST", "/api/v1/committees/{id}/external/{idx}/resend", "Regenerates accept-token; old link invalidated (v17)."),
            ("GET",  "/api/v1/committees?notice_ref=&status=open", "List filter."),
        ],
        "pitfalls": [
            "Only ONE open committee per notice at a time. Attempting to form a second returns HTTP 409.",
            "Dissolving does NOT delete the committee — the record is preserved with status='dissolved' for audit + downstream.",
            "Resend voids the old accept-token permanently. If the external invitee was mid-clicking the old link, they'll get 404 — coordinate before resending.",
        ],
        "qa": [
            {"step": "Tick 3 members, pick chair from a 4th unpicked staff", "expected": "Chair dropdown does not offer the 4th; server also enforces chair ∈ members", "testid": "committee-chair"},
            {"step": "Enter quorum = 10 with 4 members ticked", "expected": "Input caps at 4 with live hint 'Quorum ≤ 4'", "testid": "committee-quorum"},
            {"step": "Uncheck a member who is currently chair", "expected": "chair field auto-clears; save disabled until new chair picked", "testid": "committee-member-check"},
            {"step": "Dissolve with 6-char reason", "expected": "HTTP 400 'dissolve reason must be at least 8 characters'", "testid": "committee-dissolve"},
            {"step": "Resend invite to pending external", "expected": "New accept-token; old link returns 404; email sent", "testid": "committee-resend"},
            {"step": "Form 2nd committee on same notice with existing open one", "expected": "HTTP 409 'a committee already exists for this notice'", "testid": "committee-create-submit"},
        ],
        "mgmt": [
            "COI check (G2): evaluations.submit_score returns HTTP 400 unless the scorer has recorded a COI declaration for that notice.",
            "Chair change post-formation is a governance event — audit logs a distinct action.",
            "KPI: median committee formation → first score < 3 business days.",
        ],
    },

    # ---------- 8 · Reverse Auctions ---------------------------
    {
        "title": "Reverse Auctions",
        "purpose": "Live reverse-auction rooms with masked bidder identities + anti-manipulation.",
        "users": ["Ops", "QA"],
        "image": "13_auctions.png",
        "overview": (
            "Masked-identity auction (Bidder A/B/C…) with min-decrement, hard price floor, "
            "and anti-snipe extension. Draft auctions never expose the public bidder link "
            "(G5). Participant validation blocks duplicates + non-registered vendor emails."
        ),
        "screens": [
            ("Auction form", "Notice ref, Start time, Duration, Min decrement (currency), Hard price floor, Anti-snipe seconds (extends deadline if bid lands in the final N seconds), Participants (registered vendor emails only)."),
            ("Live room", "Masked leaderboard, bid input, decrement hint, time-remaining timer with red pulse in the last 30s, host controls (Pause/Close)."),
            ("Post-auction view", "Winner, winning price, bid history table, participant reveal (only admin sees real identities)."),
        ],
        "tutorial": [
            ("Draft an auction", "Auctions → '+ New' → notice + participants + min_decrement 10 000 + floor 200 000 000 + anti_snipe 30 s. Save → status='draft'. Bidder URL is HIDDEN in the panel; explanatory hint shown."),
            ("Go live", "Draft row → 'Go live'. status='live'; bidder URL now visible + copy-to-clipboard. Bidders can join the /vendor/auction/:aid room."),
            ("Handle a snipe", "If a bidder lands a valid bid in the final 30s, deadline extends by 30s. Repeat until 30s elapse with no bid — then auction closes."),
            ("Close manually", "Host → 'Close' → confirm. Last valid bid becomes winning_price on the linked bid record."),
        ],
        "api": [
            ("POST", "/api/v1/auctions", "Create draft."),
            ("POST", "/api/v1/auctions/{aid}/publish", "Draft → live. Backend re-validates participants + generates a signed public URL."),
            ("POST", "/api/v1/auctions/{aid}/bid", "Body {bidder_token, amount}. Backend enforces decrement + floor + not-outside-window."),
            ("POST", "/api/v1/auctions/{aid}/close", "Manual close. Winner + winning_price written to the linked bid."),
            ("GET",  "/api/v1/auctions/{aid}/state", "Poll endpoint (frontend polls every 2s)."),
        ],
        "pitfalls": [
            "Draft auctions do NOT show the public link (Bug G5 fix). If you don't see it, check the status pill.",
            "Participants must be pre-registered vendors — non-registered emails return HTTP 400 at auction creation.",
            "Anti-snipe extension is per-event: 5 snipe bids in the final 30s extend the deadline 5× (each 30s).",
        ],
        "qa": [
            {"step": "Add duplicate email to participants", "expected": "HTTP 400 'duplicate participant email'", "testid": "auction-participants"},
            {"step": "Open draft auction detail", "expected": "Bidder URL not shown; explanatory text present (G5)", "testid": "auction-bidder-link"},
            {"step": "Submit bid below floor", "expected": "HTTP 400 'bid below hard floor'", "testid": "auction-bid-submit"},
            {"step": "Submit bid decrement < min", "expected": "HTTP 400 'decrement must be ≥ min_decrement'", "testid": "auction-bid-submit"},
            {"step": "Close a live auction", "expected": "status='closed'; winning_price stamped on bid; participants revealed to admin only", "testid": "auction-close"},
        ],
        "mgmt": [
            "Anti-snipe extends by N seconds if a bid lands in the final N seconds — pure anti-manipulation.",
            "Winning price is written to the linked bid record for downstream award.",
        ],
    },

    # ---------- 9 · Escrow (EMD) -------------------------------
    {
        "title": "Escrow (EMD)",
        "purpose": "Joint escrow accounts with dual-signature EMD releases.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "14_escrow.png",
        "overview": (
            "Every EMD instrument flows through a joint account operated by one PMC "
            "officer + one escrow-institution officer. Both must sign before release "
            "(G1). Aging days per transaction; SLA breach flag when > 7 days pending. "
            "Reconciliation summary in Stakeholder Reports."
        ),
        "screens": [
            ("Account form", "Name, PMC officer (email), Vendor / escrow-institution officer (email), Bank details, Currency. Backend rejects create when pmc_officer.email == vendor_officer.email (G1)."),
            ("Transactions ledger", "Every EMD instrument as a row: bid_ref, amount, state (pending/signed_pmc/signed_vendor/released/refunded/forfeited), aging_days, sla_breach flag."),
            ("Sign action", "Two signatures required — each side clicks 'Sign my side' and the state advances. Release fires only after BOTH sign."),
        ],
        "tutorial": [
            ("Create a joint account", "Escrow → '+ Account' → PMC officer: alice@pmcmanagers.com; Escrow officer: bob@axisbank.in; Bank: Axis · A/C 1234 · IFSC UTIB0001234; Currency INR. Save. Status='pending'."),
            ("Sign the PMC side", "Log in as alice → account detail → 'Sign my side' → confirm. Transaction state advances to 'signed_pmc'. Vendor officer receives an email nudge."),
            ("Sign the escrow side + release", "Log in as bob → same tx → 'Sign my side' → Release. state='released'; escrow account balance updates; audit entry captures both signatures."),
            ("Read the aging report", "Stakeholder Reports → Escrow tab → header shows total accounts + total tx + SLA breach count. Table shows aging_days per pending tx + sla_breach=true when > 7d."),
        ],
        "api": [
            ("POST", "/api/v1/escrow/accounts", "Rejects with HTTP 400 'PMC officer and escrow officer must be different people' when emails match (G1)."),
            ("POST", "/api/v1/escrow/accounts/{id}/transactions", "Add a transaction. Body {bid_ref, amount}."),
            ("POST", "/api/v1/escrow/accounts/{id}/transactions/{txid}/sign", "Called by each signer. Backend checks the caller's email matches one of the two officers + which side is being signed."),
            ("POST", "/api/v1/escrow/accounts/{id}/transactions/{txid}/release", "HTTP 409 unless both signatures present."),
            ("GET",  "/api/v1/stakeholder-reports/escrow?format=json|csv", "Aging + SLA breach report."),
        ],
        "pitfalls": [
            "G1 is architecturally enforced — you cannot create an account where both emails match, even by mistake.",
            "Once released, a transaction cannot be un-released. Refund is a separate transaction that requires both signatures again.",
            "SLA threshold defaults to 7 days but is tenant-configurable via env var ESCROW_SLA_DAYS.",
        ],
        "qa": [
            {"step": "Create account with same email on both sides", "expected": "HTTP 400 'PMC officer and escrow officer must be different people' (G1)", "testid": "escrow-account-create"},
            {"step": "Sign PMC side then click Release without vendor sign", "expected": "HTTP 409 'awaiting escrow-officer signature'", "testid": "escrow-release"},
            {"step": "Sign vendor side as PMC officer login", "expected": "HTTP 403 'you can only sign your own side'", "testid": "escrow-sign"},
            {"step": "Open Stakeholder Reports / Escrow after 8 days pending", "expected": "sla_breach=true; header count increments", "testid": "stakeholder-escrow-sla"},
            {"step": "Release a released transaction again", "expected": "HTTP 409 'transaction already released'", "testid": "escrow-release"},
        ],
        "mgmt": [
            "G1 governance: same-login-both-sides is architecturally blocked at account create.",
            "SLA threshold configurable per tenant (default 7 days).",
            "KPI: median release cycle-time; SLA breach count per week.",
        ],
    },

    # ---------- 10 · Evaluation & Scoring ----------------------
    {
        "title": "Evaluation & Scoring",
        "purpose": "Committee scoring against per-criterion weighted rubric + COI cross-check.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "15_evaluation.png",
        "overview": (
            "Committee members score each bid against the rubric set on the notice. "
            "Weighted totals compute live. Every score requires an outstanding COI "
            "declaration for that (scorer, notice) tuple — enforcement is HTTP 400 at "
            "submit_score (G2)."
        ),
        "screens": [
            ("Rubric editor", "Criteria list (name, weight 0-100). Weights must sum to 100. Locked at first score."),
            ("Score entry form", "Bid selector, criteria rows (0-100 each), COI checkbox 'I have no conflict of interest with this bidder on this notice', comments field."),
            ("Committee dashboard", "Grid of bids × members; each cell shows submitted status or the score. Median → technical score."),
        ],
        "tutorial": [
            ("Set the rubric", "Notice → Evaluation → 'Set rubric'. Criteria: Technical=40, Financial=30, Timeline=20, Prior work=10. Weights sum to 100. Save. Locked at first score."),
            ("Declare COI", "Committee member → COI tab → 'I have no COI on notice X' → tick + submit. This creates a COI record for (member, notice)."),
            ("Score a bid", "Evaluation panel → pick bid → 4 scores 0-100 → tick COI → Submit. Weighted total computes live. Median across committee members becomes the technical score."),
            ("Change your score", "Same panel → same bid → edit → resubmit. Old score preserved in audit; only latest per (scorer, bid) counts toward median."),
        ],
        "api": [
            ("POST", "/api/v1/evaluations/rubric", "Body {notice_ref, criteria}. Locked after first submitted score."),
            ("POST", "/api/v1/evaluations/coi", "Body {notice_ref, declared:true}. Creates the COI record needed for submit_score to succeed."),
            ("POST", "/api/v1/evaluations/score", "Body {bid_ref, scores{}, comments}. Returns HTTP 400 'COI declaration required' if no COI record (G2)."),
            ("GET",  "/api/v1/evaluations/{notice_ref}", "Full committee grid + median technical score."),
        ],
        "pitfalls": [
            "Rubric weights MUST sum to exactly 100. HTTP 400 otherwise.",
            "Score must be between 0 and 100 per criterion. HTTP 400 outside range.",
            "COI is per (scorer, notice) — not per (scorer, bid). One declaration per notice is enough.",
        ],
        "qa": [
            {"step": "Score without ticking COI", "expected": "HTTP 400 'COI declaration required' (G2)", "testid": "eval-submit"},
            {"step": "Score = 105", "expected": "HTTP 400 'score must be between 0 and 100'", "testid": "eval-score-input"},
            {"step": "Rubric weights sum to 105", "expected": "HTTP 400 at rubric save (Bug 56)", "testid": "eval-rubric-save"},
            {"step": "Edit rubric after first score", "expected": "HTTP 409 'rubric locked after first score'", "testid": "eval-rubric-save"},
            {"step": "Non-committee member tries to score", "expected": "HTTP 403 'not a committee member for this notice'", "testid": "eval-submit"},
        ],
        "mgmt": [
            "G2 governance: no committee score can be submitted without an existing COI record.",
            "Rubric is set once per notice and locked at first score.",
            "KPI: score-dispersion per bid (high dispersion → deliberation needed).",
        ],
    },

    # ---------- 11 · L1 Comparison -----------------------------
    {
        "title": "L1 Comparison",
        "purpose": "Rule-based lowest-compliant winner selection (separate from Evaluation scoring).",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "19_l1.png",
        "overview": (
            "Distinct from Evaluation scoring: L1 filters technically-compliant bids and "
            "picks the lowest total price. Empty state lists exclusion reasons "
            "(technical-not-scored / non-compliant / withdrawn / notice-status)."
        ),
        "screens": [
            ("L1 panel", "Notice selector → run → ranked list with active-rule badge ('lowest-compliant price wins'). Empty state shows exclusion-reason counts."),
            ("Row detail", "Vendor, price, technical score, rank, compliance flags."),
        ],
        "tutorial": [
            ("Run L1 on a closed notice", "L1 tab → pick notice → Run. Bids with technical_score ≥ cutoff sort ASC by total_price. Winner is L1."),
            ("Diagnose empty state", "If empty, panel lists per-reason counts: '3 bids: technical not scored', '2 bids: non-compliant', '1 bid: withdrawn'. Tackle each in the source panel."),
        ],
        "api": [
            ("POST", "/api/v1/l1/run", "Body {notice_ref}. Returns {ranked[], excluded_by_reason{}}."),
            ("GET",  "/api/v1/l1/{notice_ref}", "Latest run snapshot."),
        ],
        "pitfalls": [
            "L1 does NOT use committee scoring — it uses the notice's technical cutoff + compliance flags.",
            "Withdrawn bids are always excluded; there's no override.",
        ],
        "qa": [
            {"step": "Run L1 on notice with all bids under cutoff", "expected": "Empty state with reason 'non-compliant' count = n", "testid": "l1-empty-state"},
            {"step": "Run L1 on a not-yet-closed notice", "expected": "Empty state with reason 'notice status' (bids can still change)", "testid": "l1-panel"},
            {"step": "Winning row exists", "expected": "'RANK 1' badge on the lowest-compliant-price row", "testid": "l1-row-rank"},
        ],
        "mgmt": [
            "Ranking rule badge shows 'lowest-compliant price wins' — transparency requirement.",
            "CSV export via /api/v1/stakeholder-reports/awards.csv.",
        ],
    },

    # ---------- 12 · Awards & POs ------------------------------
    {
        "title": "Awards & POs",
        "purpose": "Draft PO, SLA, Contract PDFs on award; regenerate with confirmation + versioning.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "16_awards.png",
        "overview": (
            "Awarding a bid drafts three PDFs (`PMC-PO-YYYY-#####`, SLA, Contract) all "
            "with a diagonal DRAFT watermark until countersigned in DocuSign. Regenerate "
            "requires confirmation and pushes {regenerated_at, regenerated_by} into "
            "bid.award_regenerations[]."
        ),
        "screens": [
            ("Awards panel", "Awarded bids table. Columns: bid_ref, PO#, contract value, awarded_at, awarded_by, regen count. Actions: Download PO/SLA/Contract, Regenerate, Send to DocuSign."),
            ("Regenerate dialog", "Explanation ('this rebuilds the three PDFs in place; the previous copies are lost'), OK/Cancel. Toast on success with timestamp + admin email."),
        ],
        "tutorial": [
            ("Award a bid", "Bidding Ops → bid (status=committee_approved) → 'Award'. Confirmation → OK. status='awarded'; PO/SLA/Contract PDFs drafted; award_ref stamped."),
            ("Regenerate", "Awards → row → 'Regenerate'. Confirmation dialog explaining the overwrite → OK. Timestamp toast; award_regenerations[] gains an entry."),
            ("Send to DocuSign", "Row → 'Send to DocuSign' → pick delivery mode (Embedded / Email) → envelope created. Track in DocuSign panel."),
        ],
        "api": [
            ("POST", "/api/v1/bids/{ref}/award", "Draft the three PDFs + assign award_ref."),
            ("POST", "/api/v1/bids/{ref}/award/regenerate", "Rebuild in place; append to award_regenerations[]."),
            ("GET",  "/api/v1/bids/{ref}/award/{kind}", "kind ∈ po|sla|contract. Streams the PDF."),
        ],
        "pitfalls": [
            "Regenerate is destructive to the previous PDF versions on disk. If you need the old copy, download it first.",
            "> 3 regenerations on the same bid triggers a governance flag in the audit dashboard.",
        ],
        "qa": [
            {"step": "Award an already-awarded bid", "expected": "HTTP 409 'bid already awarded'", "testid": "awards-award"},
            {"step": "Regenerate documents", "expected": "Confirmation dialog; on OK, toast shows timestamp + admin email; award_regenerations[] gains 1 entry", "testid": "awards-regenerate"},
            {"step": "Download PO before award", "expected": "HTTP 404 'award not yet issued'", "testid": "awards-download-po"},
        ],
        "mgmt": [
            "Every regeneration is a governance event; audit flags > 3 regenerations as suspicious.",
            "KPI: median time-to-award (committee approval → award).",
        ],
    },

    # ---------- 13 · DocuSign · Envelope Log ------------------
    {
        "title": "DocuSign · Envelope Log",
        "purpose": "JWT-Grant DocuSign integration + authoritative-envelope flag.",
        "users": ["Ops", "QA"],
        "image": "20_docusign.png",
        "overview": (
            "PO / SLA / Contract PDFs go out via DocuSign either as Embedded (in-app "
            "iframe with one-time signing URL) or Email (hosted signing). Envelope Log "
            "per (bid_id, sub_kind) flags the authoritative envelope: status=completed "
            "wins, break ties by most recent created_at."
        ),
        "screens": [
            ("Consent card", "Shown on first run — 'Grant DocuSign consent' button. One-time browser hop."),
            ("Envelope Log table", "Columns: bid_ref, kind (award/bid_ack), sub_kind (po/sla/contract), delivery (embedded/email), status, is_authoritative badge, created_at, signer_email."),
        ],
        "tutorial": [
            ("Grant consent", "DocuSign panel → 'Grant DocuSign consent' → sign on DocuSign → return. Consent is stored server-side (1-year TTL)."),
            ("Send an envelope", "Awards → 'Send to DocuSign' → Embedded → confirm. Envelope created; if Embedded, an iframe opens with the signing URL."),
            ("Track authoritativeness", "Envelope Log → filter bid_id + sub_kind = po. The row with the latest completed status has is_authoritative=true badge."),
        ],
        "api": [
            ("POST", "/api/v1/docusign/consent", "One-time consent flow start."),
            ("POST", "/api/v1/docusign/envelopes", "Body {bid_ref, kind, sub_kind, delivery, signer_email}."),
            ("GET",  "/api/v1/envelope-log?bid_id=&kind=&sub_kind=", "Returns items with is_authoritative flagged."),
            ("POST", "/api/v1/docusign/envelopes/{id}/resend", "Resend the signing invite."),
        ],
        "pitfalls": [
            "Consent expires per DocuSign policy (usually 1 year) — Dashboard warns 30 days out.",
            "Embedded delivery expires the signing URL after 5 minutes — refresh the row if the signer waits too long.",
        ],
        "qa": [
            {"step": "Filter Envelope Log by bid_id + sub_kind", "expected": "Only relevant envelopes; exactly one has is_authoritative=true", "testid": "envelope-log-filter"},
            {"step": "Two envelopes both status=completed", "expected": "The one with later created_at wins is_authoritative", "testid": "envelope-log-row"},
            {"step": "Send before granting consent", "expected": "HTTP 400 'DocuSign consent required'", "testid": "docusign-send"},
        ],
        "mgmt": [
            "Authoritative envelope is the single source of truth for legal downstream — audit ties to that envelope_id.",
        ],
    },

    # ---------- 14 · BOQ & Contracts --------------------------
    {
        "title": "BOQ & Contracts",
        "purpose": "Bill-of-Quantities templates + Contract lifecycle with export & versioning.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "17_boq.png",
        "overview": (
            "BOQ templates are imported via Excel (Sl.No | Description | Unit | Quantity "
            "| Unit Rate | Remarks). Vendors quote against the template. Only awarded "
            "bids can spawn a contract (`PMC-CON-YYYY-####`). Contracts export to CSV + "
            "per-contract version timeline (creation, milestone completions, variation "
            "orders)."
        ),
        "screens": [
            ("BOQ template import", "Drag Excel file → column validation → preview → Confirm import. Duplicate detection by (project, description)."),
            ("Contracts sub-tab", "Columns: contract_ref, bid_id, vendor_id, title, value, currency, start/end dates, milestones count, VO count, status. Filter by status/vendor/query."),
            ("Version timeline drawer", "Events sorted by 'at' ASC: created, milestone_N_completed, variation_order (with reason, amount_delta)."),
        ],
        "tutorial": [
            ("Import a BOQ Excel", "BOQ tab → 'Import Excel' → pick file → validation → Confirm. Rows appear as line items on subsequent bids for the linked notice."),
            ("Spawn a contract from an awarded bid", "Awards → awarded bid → 'Create contract'. Fills defaults from bid; edit title + start/end dates. contract_ref auto-generated."),
            ("Add a milestone", "Contract detail → Milestones → '+ Milestone'. Order, name, amount, due_date. On completion, mark completed → version event stamped."),
            ("Log a variation order", "Contract detail → Variation orders → '+ VO'. Reason, amount_delta. Timestamp + by stamped. Value on contract auto-adjusts."),
            ("Export CSV", "Contracts sub-tab → Filters → Download → CSV downloads with Content-Disposition: attachment."),
        ],
        "api": [
            ("POST", "/api/v1/boqs/import", "Multipart Excel."),
            ("POST", "/api/v1/contracts", "Create from awarded bid."),
            ("POST", "/api/v1/contracts/{id}/milestones", "Add / update milestone."),
            ("POST", "/api/v1/contracts/{id}/variation-orders", "Add VO with reason + amount_delta."),
            ("GET",  "/api/v1/contracts-export/list?status=&vendor_id=&q=", "Filter + list."),
            ("GET",  "/api/v1/contracts-export/list.csv", "CSV dump with same filter params."),
            ("GET",  "/api/v1/contracts-export/{id}/versions", "Timeline of events sorted by 'at'."),
        ],
        "pitfalls": [
            "BOQ Excel column headers must match exactly — case + spacing sensitive.",
            "Milestone completion is irreversible — treat it as a legal event.",
            "Variation orders CAN reduce contract value — amount_delta is signed.",
        ],
        "qa": [
            {"step": "Import Excel with missing 'Unit Rate' column", "expected": "HTTP 400 'missing required column: Unit Rate'", "testid": "boq-import"},
            {"step": "Export contracts.csv with status=active filter", "expected": "CSV downloads with matching row count; Content-Disposition header", "testid": "contracts-export-csv"},
            {"step": "Open version timeline for contract with 2 milestones + 1 VO", "expected": "3 events sorted by 'at' ASC", "testid": "contract-versions"},
            {"step": "Create contract from non-awarded bid", "expected": "HTTP 400 'bid must be in awarded status'", "testid": "contract-create"},
        ],
        "mgmt": [
            "Every VO is auditable {at, by, amount_delta, reason}.",
            "Milestone hit-rate feeds Stakeholder Reports / SLA.",
        ],
    },

    # ---------- 15 · Masters · Roles & Permissions -------------
    {
        "title": "Masters · Roles & Permissions",
        "purpose": "Single source of truth for who can do what (G3 unified).",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "25_permissions.png",
        "overview": (
            "Permissions Matrix + hierarchy Level are now unified via "
            "GET /api/v1/permissions/effective/{role} (Wave G2). One call returns "
            "{role, level, level_label, tabs, actions} — drives menu visibility + "
            "button disabled-state everywhere in the console."
        ),
        "screens": [
            ("Permissions matrix", "Rows = roles, columns = document types. Each cell has 5 checkboxes: view / create / modify / delete / publish. Save writes updated_at + updated_by."),
            ("Effective view drawer", "For a picked role, shows: level 0-3, level_label (master/deputy/operator/viewer), tabs[], actions{}, source (matrix_override vs default_tabs)."),
            ("Staff Master screen", "User → Role tags + numeric Level (0-3). Level maps to LEVEL_BY_ROLE fallback if not overridden per user."),
        ],
        "tutorial": [
            ("Grant Reviewer create-on-notices", "Permissions matrix → row 'reviewer' → column 'notices' → tick 'Create' → Save. audit_log entry; updated_at header refreshes."),
            ("Inspect effective permissions", "GET /api/v1/permissions/effective/reviewer → {level:1, level_label:'deputy', tabs:[…], actions:{view:true, create:true, modify:true, delete:false, publish:false}}."),
            ("Add a new staff", "Masters → Staff → '+ Staff'. Email + role tags + level. Save."),
        ],
        "api": [
            ("GET",  "/api/v1/permissions", "Full matrix."),
            ("PUT",  "/api/v1/permissions", "Bulk upsert of matrix rows. Body {rows:[{role, doc_type, view, create, modify, delete, publish}]}."),
            ("GET",  "/api/v1/permissions/effective/{role}", "Wave G2 · merged view — this is the endpoint every UI panel uses."),
            ("GET",  "/api/v1/permissions/tabs/{role}", "Just the tabs[] slice."),
        ],
        "pitfalls": [
            "Modifying the matrix is real-time — logged-in users see their new permissions on next page-refresh, no re-auth needed.",
            "Level and matrix are complementary, not conflicting — G2 effective endpoint returns both.",
        ],
        "qa": [
            {"step": "GET /api/v1/permissions/effective/reviewer", "expected": "Returns level=1, level_label=deputy, tabs and actions", "testid": "permissions-effective"},
            {"step": "Reviewer tries to publish", "expected": "HTTP 403 'insufficient permissions to publish'", "testid": "notices-publish-checkbox"},
            {"step": "Untick Reviewer.create then save", "expected": "audit_log entry; Reviewer's next Notices create attempt returns 403", "testid": "permissions-save"},
        ],
        "mgmt": [
            "G3 governance: closed — single access-control endpoint replaces two parallel systems.",
            "Full audit on matrix mutations.",
        ],
    },

    # ---------- 16 · Governance Guardrails --------------------
    {
        "title": "Governance Guardrails",
        "purpose": "Five architectural controls audited by QA + investor teams.",
        "users": ["Mgmt", "QA"],
        "image": None,
        "overview": (
            "G1..G5 are the guardrails that turn 'compliance theatre' into real controls. "
            "Every one is either an HTTP 400/409 at the API layer OR a UI element that "
            "cannot leak sensitive state."
        ),
        "screens": [
            ("G1 · Escrow dual-sig", "escrow.create_account rejects same-email-both-sides."),
            ("G2 · COI cross-check", "evaluations.submit_score requires an existing COI record."),
            ("G3 · Access-control unified", "/api/v1/permissions/effective/{role} merges tabs + actions + level."),
            ("G4 · Stakeholder Reports", "Four real reports: tenders / awards / escrow / sla with JSON + CSV."),
            ("G5 · Draft auction bidder link", "Frontend hides link when status='draft'; server also refuses public GET."),
        ],
        "tutorial": [
            ("Reproduce G1", "curl -XPOST /api/v1/escrow/accounts with pmc_officer.email = vendor_officer.email → expect HTTP 400 'must be different people'."),
            ("Reproduce G2", "Curl submit_score without a prior COI record → expect HTTP 400 'COI declaration required'."),
            ("Reproduce G3", "GET /api/v1/permissions/effective/reviewer → verify single payload merges tabs + actions + level."),
            ("Reproduce G4", "GET /api/v1/stakeholder-reports/{tenders,awards,escrow,sla} → each returns JSON; add ?format=csv for CSV."),
            ("Reproduce G5", "Create a draft auction → GET the public bidder URL → expect 404 or hidden UI element."),
        ],
        "api": [
            ("POST", "/api/v1/escrow/accounts", "G1 — HTTP 400 if same email both sides."),
            ("POST", "/api/v1/evaluations/score", "G2 — HTTP 400 if no COI."),
            ("GET",  "/api/v1/permissions/effective/{role}", "G3 — single unified payload."),
            ("GET",  "/api/v1/stakeholder-reports/{name}", "G4 — 4 real reports."),
            ("GET",  "/api/v1/auctions/{aid}/public", "G5 — 404 when status='draft'."),
        ],
        "pitfalls": [
            "Guardrails are the pass/fail for investor code review — do NOT weaken them for a UX shortcut.",
        ],
        "qa": [
            {"step": "G1", "expected": "HTTP 400 'must be different people'", "testid": "escrow-account-create"},
            {"step": "G2", "expected": "HTTP 400 'COI declaration required'", "testid": "eval-submit"},
            {"step": "G3", "expected": "Single payload with tabs + actions + level", "testid": "permissions-effective"},
            {"step": "G4", "expected": "4 real reports available JSON + CSV", "testid": "stakeholder-reports-panel"},
            {"step": "G5", "expected": "Draft auction bidder link not rendered", "testid": "auction-bidder-link"},
        ],
        "mgmt": [
            "Bug tracker v5 · 44 of 52 observations FIXED (85 %).",
            "Guardrails are the pass/fail for investor code review.",
        ],
    },
]

# ============================================================
# SLIM CHAPTERS (non-core — kept compact)
# ============================================================
SLIM = [
    {
        "title": "Public Notice Board",
        "purpose": "External entry-point where bidders discover open tenders.",
        "users": ["Ops", "Mgmt"],
        "image": "02_public-tender-board.png",
        "overview": "Public list of every published notice across every tenant. Filters by type, country, category.",
        "ops": ["Vendors browse without login.", "Card click → notice detail.", "'Register interest' → /register."],
        "qa": [
            {"step": "Load /notices", "expected": "Only is_published=true render", "testid": "public-notice-card"},
            {"step": "Filter by country", "expected": "List narrows in <300ms", "testid": "public-notice-filter-country"},
        ],
        "mgmt": ["Draft notices never public.", "KPI: median time-to-first-bid per notice."],
    },
    {
        "title": "Registrations Admin",
        "purpose": "Review incoming vendors, approve / reject / clarify with reason.",
        "users": ["Ops", "Mgmt"],
        "image": "07_registrations.png",
        "overview": "Admin-side triage of every submitted vendor registration; sorted oldest-first.",
        "ops": [
            "Sort by 'Submitted date' (default oldest first).",
            "Click row → review sections → Approve / Reject / Clarify (reason ≥5 chars).",
            "Bulk Invite CSV supports pre-loading known vendors.",
        ],
        "qa": [
            {"step": "Approve valid PAN doc", "expected": "vendor doc + welcome email sent", "testid": "reg-row-approve"},
            {"step": "Nudge Stale Drafts", "expected": "3-branch toast", "testid": "reg-nudge-stale"},
        ],
        "mgmt": ["Aging report; daily digest for > 30-day drafts.", "KPI: median approval turnaround per tenant."],
    },
    {
        "title": "Meetings",
        "purpose": "Schedule Jitsi/Zoom tied to a notice OR marked internal.",
        "users": ["Ops", "QA"],
        "image": "18_meetings.png",
        "overview": "Every meeting either references a notice_ref OR is flagged 'Internal meeting'.",
        "ops": ["'+ Schedule' → provider + subject + time + invitees.", "Tick 'Internal meeting' to skip notice.", "Otherwise pick notice."],
        "qa": [
            {"step": "Create without notice_ref and is_internal=false", "expected": "HTTP 400 (Bug 48b)", "testid": "mtg-create"},
            {"step": "Tick 'Internal meeting'", "expected": "Notice dropdown disables + clears", "testid": "mtg-is-internal"},
        ],
        "mgmt": ["Every meeting join is logged with invitee token + timestamp."],
    },
    {
        "title": "Vendor Intel",
        "purpose": "Bulk vendor risk register with BL / WL flags.",
        "users": ["Ops", "Mgmt"],
        "image": "21_vendor-intel.png",
        "overview": "Imported watch-lists + blacklists; alerts committee scorers when a bidder is listed.",
        "ops": ["Legend: BL=Blacklisted · WL=Watch-list · — = anonymised.", "Add manually or bulk-import CSV."],
        "qa": [{"step": "Score a bid where vendor is on BL", "expected": "Red BL badge on the bidder card", "testid": "eval-vendor-badge"}],
        "mgmt": ["BL entries block auto-award; committee must override with a reason."],
    },
    {
        "title": "Product Catalog",
        "purpose": "SKU catalog feeding Stripe checkout + price-history log.",
        "users": ["Ops", "Mgmt"],
        "image": "22_products.png",
        "overview": "Products drive the public checkout page. Every price change is logged.",
        "ops": ["'+ Product' → name, price, currency.", "Edit → save → history entry auto-created."],
        "qa": [{"step": "Change price 3 times", "expected": "price_history[] has 3 entries", "testid": "product-edit-save"}],
        "mgmt": ["KPI: gross checkout revenue per SKU per month."],
    },
    {
        "title": "Engagements (Quotes)",
        "purpose": "Public quote-requests through to invoicing + aging report.",
        "users": ["Ops", "QA", "Mgmt"],
        "image": "23_engagements.png",
        "overview": "State machine: quote_requested → quoted → invoiced → paid (or cancelled with reason ≥5).",
        "ops": ["Public quote lands here.", "Set quoted amount → 'Invoice' generates Stripe checkout link.", "Cancel requires reason ≥5 chars."],
        "qa": [
            {"step": "Cancel with 3-char reason", "expected": "HTTP 400 (Bug 35)", "testid": "eng-cancel"},
            {"step": "GET /engagements/aging/summary", "expected": "Buckets 0-7/8-30/31-60/61+", "testid": "eng-aging"},
        ],
        "mgmt": ["Aging report drives receivables collection.", "KPI: quote → paid conversion rate."],
    },
    {
        "title": "Portal Branding",
        "purpose": "Tenant-level logo + theme + rolling logo history.",
        "users": ["Ops", "Mgmt"],
        "image": "30_branding.png",
        "overview": "Every tenant gets primary_color + accent_color + favicon + logo (rolling history max 10).",
        "ops": ["Upload new logo → history entry auto-created.", "PATCH /api/v1/branding/{tid}/theme with primary/accent colours."],
        "qa": [
            {"step": "Upload 11 logos sequentially", "expected": "history[] contains only last 10", "testid": "branding-logo-upload"},
            {"step": "PATCH primary_color='red'", "expected": "HTTP 422 'must match #RRGGBB'", "testid": "branding-theme-save"},
        ],
        "mgmt": ["Branding changes audited — no silent tenant re-brand."],
    },
    {
        "title": "Reports · Asked-vs-Delivered",
        "purpose": "Development / scope-completion snapshot for engineering handoff.",
        "users": ["Mgmt"],
        "image": "27_reports.png",
        "overview": "'Asked vs delivered' statement + three swim-lane flowcharts (platform/user guide/testing).",
        "ops": ["'Snapshot to disk' → 9 files land in /docs/reports/.", "Bug 38 fix: each artefact wrapped in try/except."],
        "qa": [{"step": "POST /reports/snapshot", "expected": "{ok:true, files:[…9], errors:[]}", "testid": "reports-snapshot"}],
        "mgmt": ["Deliverable for investor code review + eng handoff."],
    },
    {
        "title": "Stakeholder Reports · G4",
        "purpose": "Four operational reports for procurement stakeholders.",
        "users": ["Mgmt", "Ops"],
        "image": "28_stakeholder.png",
        "overview": "G4 rebuild · Tenders (pipeline) · Awards (PO + value) · Escrow (aging + SLA) · SLA (contracts + milestones).",
        "ops": ["Tab through 4 reports; each has CSV download.", "Escrow report highlights SLA breach count."],
        "qa": [
            {"step": "Open Stakeholder Reports / Escrow", "expected": "aging_days per tx; sla_breach=true > 7d", "testid": "stakeholder-escrow-sla"},
            {"step": "Download tenders.csv", "expected": "CSV Content-Disposition: attachment", "testid": "stakeholder-download-csv"},
        ],
        "mgmt": ["Circulate CSV to stakeholders without portal access."],
    },
    {
        "title": "Help Requests",
        "purpose": "Triage inbound support tickets from the public site.",
        "users": ["Ops", "Mgmt"],
        "image": "29_help.png",
        "overview": "Public help form drops a ticket with kind + identity + phone + company. Panel shows aging + resolution history.",
        "ops": ["Sort by aging.", "Update kind, mark resolved, add resolution note."],
        "qa": [
            {"step": "Public submit with no email", "expected": "HTTP 400 'email required'", "testid": "help-public-submit"},
            {"step": "Mark resolved", "expected": "Row moves to Resolved tab; resolution_at stamped", "testid": "help-resolve"},
        ],
        "mgmt": ["SLA planned: 24h first response (Sales), 72h (Technical)."],
    },
    {
        "title": "Audit Log",
        "purpose": "Chronological ledger of every substantive action.",
        "users": ["Ops", "Mgmt"],
        "image": "26_audit.png",
        "overview": "Every mutation writes to audit_log with {at, actor, action, resource_type, resource_id, payload}.",
        "ops": ["Sort by 'at' DESC (default).", "Copy row payload to inspect raw event."],
        "qa": [{"step": "Render audit with 10 000 rows", "expected": "Scrollable; ErrorBoundary NOT triggered", "testid": "admin-audit-panel"}],
        "mgmt": ["Legal-grade: audit log is append-only.", "Filters (actor/type/date) planned for Bucket B."],
    },
    {
        "title": "Dashboard · Analytics & Drill-through",
        "purpose": "Real-time KPIs + click-through to filtered lists.",
        "users": ["Ops", "Mgmt"],
        "image": "06_analytics.png",
        "overview": "AI Anomaly, Pipeline Funnel, Top-Priced Bids — clickable via /dashboard-drill/*.",
        "ops": ["Click any card to expand a filtered mini-table.", "Click again to collapse."],
        "qa": [
            {"step": "Click AI Anomaly card", "expected": "Drill panel with ≤200 rows; empty state 'No AI-flagged bids' if none", "testid": "drill-card-anom"},
            {"step": "Click Pipeline Funnel", "expected": "/dashboard-drill/pipeline?status= returns ≤500 rows", "testid": "drill-card-pipe"},
        ],
        "mgmt": ["KPI dashboard is the daily standup screen.", "AI Copilot is advisory — no state change without human sign-off."],
    },
    {
        "title": "Sign-out & Exit",
        "purpose": "Cookie-clear + redirect to public login.",
        "users": ["Ops", "QA"],
        "image": "31_sign-out-return.png",
        "overview": "Sign-out clears the HTTPOnly admin cookie and redirects to /login.",
        "ops": ["Top-right → 'Sign out'."],
        "qa": [
            {"step": "Click Sign out", "expected": "Redirect to /login within 1s; cookie no longer present", "testid": "admin-logout"},
            {"step": "Direct /admin after sign-out", "expected": "Bounce to /login; /api/v1/me returns 401", "testid": "admin-logout"},
        ],
        "mgmt": ["Session TTL 12h max; sliding renewal on activity."],
    },
]

# Global chapter order = core first, then slim (they're independent modules).
CHAPTERS = CORE + SLIM


# ============================================================
# DOCX Rendering helpers
# ============================================================
def _shading(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def _run(para, text, *, size=10, bold=False, italic=False, color=None, font="Calibri"):
    r = para.add_run(text)
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r


def _kicker(doc, label, hex_fill="0B1F3A"):
    t = doc.add_table(rows=1, cols=1)
    cell = t.rows[0].cells[0]
    _shading(cell, hex_fill)
    para = cell.paragraphs[0]
    _run(para, label.upper(), size=9, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    return t


def _bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        _run(p, it, size=10, color=NAVY)


def _screens_table(doc, screens):
    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = "Light Grid Accent 1"
    hdr = tbl.rows[0].cells
    hdr[0].text = "Screen / Field"; hdr[1].text = "What it captures / does"
    for cell in hdr:
        _shading(cell, "0B1F3A")
        for para in cell.paragraphs:
            for r in para.runs:
                r.font.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for name, body in screens:
        cells = tbl.add_row().cells
        cells[0].text = name
        cells[1].text = body
        for c in cells:
            for para in c.paragraphs:
                for r in para.runs:
                    r.font.size = Pt(9)
                    r.font.color.rgb = NAVY
    tbl.columns[0].width = Inches(2.2)
    tbl.columns[1].width = Inches(4.9)


def _tutorial_list(doc, steps):
    for i, (title, body) in enumerate(steps, start=1):
        p = doc.add_paragraph()
        _run(p, f"Step {i} · {title}", size=11, bold=True, color=NAVY)
        p = doc.add_paragraph()
        _run(p, body, size=10, color=NAVY)


def _api_table(doc, endpoints):
    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = "Light Grid Accent 1"
    hdr = tbl.rows[0].cells
    hdr[0].text = "Method"; hdr[1].text = "Path"; hdr[2].text = "Notes"
    for cell in hdr:
        _shading(cell, "0B1F3A")
        for para in cell.paragraphs:
            for r in para.runs:
                r.font.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for method, path, notes in endpoints:
        cells = tbl.add_row().cells
        cells[0].text = method
        cells[1].text = path
        cells[2].text = notes
        for para in cells[0].paragraphs + cells[1].paragraphs:
            for r in para.runs:
                r.font.name = "Consolas"
                r.font.size = Pt(9)
                r.font.color.rgb = NAVY_SOFT
        for para in cells[2].paragraphs:
            for r in para.runs:
                r.font.size = Pt(9)
                r.font.color.rgb = NAVY
    tbl.columns[0].width = Inches(0.7)
    tbl.columns[1].width = Inches(2.5)
    tbl.columns[2].width = Inches(3.9)


def _test_table(doc, rows):
    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = "Light Grid Accent 1"
    hdr = tbl.rows[0].cells
    hdr[0].text = "#"; hdr[1].text = "Test step"; hdr[2].text = "Expected outcome"
    for cell in hdr:
        _shading(cell, "0B1F3A")
        for para in cell.paragraphs:
            for r in para.runs:
                r.font.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for i, row in enumerate(rows, start=1):
        cells = tbl.add_row().cells
        cells[0].text = str(i)
        cells[1].text = row["step"]
        cells[2].text = row["expected"]
        if row.get("testid"):
            p = cells[2].add_paragraph()
            _run(p, f"data-testid: {row['testid']}", size=8, color=NAVY_SOFT, font="Consolas")
        for c in cells:
            for para in c.paragraphs:
                for r in para.runs:
                    if not r.font.size:
                        r.font.size = Pt(9)
                    if r.font.color.rgb is None:
                        r.font.color.rgb = NAVY
    tbl.columns[0].width = Inches(0.35)
    tbl.columns[1].width = Inches(3.3)
    tbl.columns[2].width = Inches(3.5)


def _footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    _run(p, "PMC Managers v2 · Master Training Manual · v2 · Confidential", size=8, color=GREY)
    p.add_run("\t\t")
    fld_begin = OxmlElement("w:fldChar"); fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = "PAGE"
    fld_sep = OxmlElement("w:fldChar"); fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar"); fld_end.set(qn("w:fldCharType"), "end")
    r = p.add_run("").element
    for el in (fld_begin, instr, fld_sep, fld_end):
        r.append(el)


def build():
    doc = Document()

    section = doc.sections[0]
    section.page_height = Inches(11.69)
    section.page_width = Inches(8.27)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, attr, Inches(0.6))
    _footer(section)

    # Cover
    for _ in range(3):
        doc.add_paragraph()
    _run(doc.add_paragraph(), TITLE, size=30, bold=True, color=NAVY)
    _run(doc.add_paragraph(), SUBTITLE, size=15, italic=True, color=NAVY_SOFT)
    doc.add_paragraph()
    _run(doc.add_paragraph(), f"Generated {GENERATED}", size=9, color=GREY)
    doc.add_paragraph()
    _run(doc.add_paragraph(),
          "This document supersedes every earlier PMC training manual "
          "(v1 → v3.2 handbook · Screenshot Manual v1 · v1 master manual · "
          "every Observation-Response iteration).", size=11, bold=True, color=NAVY)
    doc.add_paragraph()
    _run(doc.add_paragraph(),
          "Core modules (16) get a deep-dive structure: Screens & fields → "
          "Step-by-step tutorial → API reference → Common pitfalls → Expanded "
          "QA cases → Governance & KPIs. Non-core modules use the compact layout.",
          size=10.5, color=NAVY)
    doc.add_page_break()

    # TOC
    _run(doc.add_paragraph(), "Contents", size=22, bold=True, color=NAVY)
    doc.add_paragraph()
    toc = doc.add_table(rows=1, cols=4)
    toc.style = "Light Grid Accent 1"
    hdr = toc.rows[0].cells
    hdr[0].text = "#"; hdr[1].text = "Module"; hdr[2].text = "Depth"; hdr[3].text = "Audience"
    for cell in hdr:
        _shading(cell, "0B1F3A")
        for para in cell.paragraphs:
            for r in para.runs:
                r.font.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for i, ch in enumerate(CHAPTERS, start=1):
        row = toc.add_row().cells
        row[0].text = str(i)
        row[1].text = ch["title"]
        row[2].text = "Deep-dive" if ch in CORE else "Compact"
        row[3].text = " · ".join(ch["users"])
        for cell in row:
            for para in cell.paragraphs:
                for r in para.runs:
                    r.font.size = Pt(9)
                    r.font.color.rgb = NAVY
    toc.columns[0].width = Inches(0.35)
    toc.columns[1].width = Inches(3.5)
    toc.columns[2].width = Inches(1.0)
    toc.columns[3].width = Inches(2.3)
    doc.add_page_break()

    # Chapters
    for i, ch in enumerate(CHAPTERS, start=1):
        _run(doc.add_paragraph(), f"Chapter {i} · {ch['title']}",
              size=20, bold=True, color=NAVY)
        _run(doc.add_paragraph(), ch["purpose"], size=11, italic=True, color=NAVY_SOFT)
        _run(doc.add_paragraph(), "Audience: " + " · ".join(ch["users"]),
              size=9, color=GREY)

        _kicker(doc, "Overview")
        _run(doc.add_paragraph(), ch["overview"], size=10.5, color=NAVY)

        if ch.get("image"):
            img = SCREENSHOT_DIR / ch["image"]
            if img.exists():
                doc.add_paragraph()
                doc.add_picture(str(img), width=Inches(7.0))

        if ch.get("screens"):
            _kicker(doc, "Screens & fields")
            _screens_table(doc, ch["screens"])

        if ch.get("tutorial"):
            _kicker(doc, "Step-by-step tutorial", hex_fill="0B4F6C")
            _tutorial_list(doc, ch["tutorial"])
        elif ch.get("ops"):
            _kicker(doc, "OPERATIONS TEAM · HOW TO USE", hex_fill="0B4F6C")
            _bullets(doc, ch["ops"])

        if ch.get("api"):
            _kicker(doc, "API reference")
            _api_table(doc, ch["api"])

        if ch.get("pitfalls"):
            _kicker(doc, "Common pitfalls", hex_fill="78350F")
            _bullets(doc, ch["pitfalls"])

        if ch.get("qa"):
            _kicker(doc, "QA TEAM · TEST CASES", hex_fill="7F1D1D")
            _test_table(doc, ch["qa"])

        if ch.get("mgmt"):
            _kicker(doc, "MANAGEMENT · GOVERNANCE · KPIs", hex_fill="065F46")
            _bullets(doc, ch["mgmt"])

        doc.add_page_break()

    # Appendix A · Change-log
    _run(doc.add_paragraph(), "Appendix A · Change-log", size=20, bold=True, color=NAVY)
    doc.add_paragraph()
    for entry in [
        ("v2 · Sep 2026", "Deep-dive edition · 16 core modules × 6 subsections (Screens / Tutorial / API / Pitfalls / QA / Mgmt) + 13 slim modules. Supersedes v1."),
        ("v1 · Sep 2026", "Definitive master manual · every module × 4 tracks · supersedes v1..v3.2 handbook + Screenshot Manual v1 + Observation-Response docs."),
        ("Backend v17", "Committee UX overhaul · Wave-E2 polish · G2 access-control consolidation."),
        ("Frontend v20", "Committee checkboxes + dissolve + resend · Tender kind-tab reset · status-token toast · Dashboard drill cards."),
    ]:
        _run(doc.add_paragraph(), entry[0], size=11, bold=True, color=NAVY)
        _run(doc.add_paragraph(), entry[1], size=10, color=NAVY)
    doc.add_page_break()

    # Appendix B · Guardrails
    _run(doc.add_paragraph(), "Appendix B · Guardrails (governance)",
          size=20, bold=True, color=NAVY)
    doc.add_paragraph()
    for g in [
        "G1 · Escrow dual-signature — HTTP 400 if pmc_officer.email == vendor_officer.email.",
        "G2 · COI cross-check — HTTP 400 at evaluations.submit_score without a COI declaration.",
        "G3 · Access-control unified — /api/v1/permissions/effective/{role} merges tabs + actions + Level.",
        "G4 · Stakeholder Reports — four real reports (Tenders / Awards / Escrow / SLA) JSON + CSV.",
        "G5 · Draft auction bidder link hidden when status='draft'.",
        "ErrorBoundary — every route is wrapped; blank screens architecturally impossible.",
        "Audit — every substantive action writes to audit_log with actor + IP + payload.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        _run(p, g, size=10, color=NAVY)

    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_DOCX))
    print(f"Written {OUT_DOCX} · {OUT_DOCX.stat().st_size / 1024:.1f} KB · "
          f"{len(CHAPTERS)} chapters ({len(CORE)} deep-dive / {len(SLIM)} slim)")


def convert_pdf():
    for cmd in ("libreoffice", "soffice"):
        try:
            r = subprocess.run(
                [cmd, "--headless", "--convert-to", "pdf",
                 "--outdir", str(OUT_DOCX.parent), str(OUT_DOCX)],
                capture_output=True, timeout=240,
            )
            if r.returncode == 0 and OUT_PDF.exists():
                print(f"Wrote {OUT_PDF} · {OUT_PDF.stat().st_size / 1024:.1f} KB")
                return
            print(f"[warn] {cmd} exit {r.returncode}: {(r.stderr or b'').decode()[:200]}")
        except FileNotFoundError:
            continue


if __name__ == "__main__":
    build()
    convert_pdf()
