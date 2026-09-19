"""
PMC Managers v2 — Comprehensive User Manual · content model
================================================================
Every module has a machine-readable spec used by:
  * build_manual_docx.py    — assembles DOCX + PDF
  * capture_manual_shots.py — drives Playwright to capture screenshots
  * frontend/src/apps/admin-console/HelpPanel.jsx — reads a JSON export
    (via /api/v1/meta/help) to render the in-app Help tab

Spec shape per module:
    "module-code": {
        "surface": "admin" | "vendor" | "staff" | "registration" | "public" | "magic",
        "title":   "Display title",
        "purpose": "One paragraph — what this module does + who owns it.",
        "prerequisites": ["Admin login", "At least one …"],
        "url_path": "/admin?tab=notices",
        "actions": [
            {
                "id":          "publish-notice",
                "label":       "Publish a tender notice",
                "when":        "You have a draft ready to go live on the public board.",
                "steps":       ["Open the Notices tab.", "Click NEW NOTICE.", "..."],
                "expected":    "The notice appears on the public board within 30 seconds.",
                "controls":    [
                    {"name": "Title",              "desc": "Public-facing headline. Min 3 chars."},
                    {"name": "Publish immediately","desc": "Reserved for Master Admin."},
                ],
                "errors": [
                    {"code": "HTTP 422",
                     "msg":  "Title minimum 3 characters",
                     "fix":  "Type at least 3 letters into the Title field."},
                ],
                "screenshot": "admin-notices-publish.png",
            },
            ...
        ],
    }
"""

MODULES = {
    # =========================================================================
    # ADMIN CONSOLE
    # =========================================================================
    "admin-dashboard": {
        "surface": "admin",
        "title": "Dashboard — Analytics",
        "url_path": "/admin?tab=analytics",
        "purpose": (
            "The Dashboard tab is the Admin's operational overview. It shows the "
            "supplier funnel (Draft → Submitted → Approved), open notice counts, "
            "bidder engagement metrics, and any SLA breaches across the platform. "
            "Owned by the Master Admin; visible to all admin roles."
        ),
        "prerequisites": ["Admin login as any admin role"],
        "actions": [
            {"id": "view-funnel",  "label": "Review the supplier funnel",
             "when": "Weekly review, or before publishing a new tender.",
             "steps": [
                 "Log in via `/login` as an admin.",
                 "Land on `/admin` — you're on the Dashboard tab by default.",
                 "Look at the four KPI tiles at the top: Draft · Submitted · Approved · Rejected.",
                 "Hover any tile to see the 7-day trend arrow.",
             ],
             "expected": "Live counts refresh every 60 seconds. Green arrow = healthy.",
             "controls": [
                 {"name": "Refresh",       "desc": "Force-refresh the tiles without a full page reload."},
                 {"name": "Time window",   "desc": "7d / 30d / 90d toggle for trend arrows."},
             ],
             "errors": [
                 {"code": "0 across all tiles", "msg": "Tiles all show zero",
                  "fix":  "Check that at least one registration or notice exists. If yes and tiles are still zero, run `curl /api/v1/meta/public/stats` — a non-zero response confirms the frontend cache is stale (hard-refresh)."},
             ],
             "screenshot": "admin-dashboard-funnel.png"},
        ],
    },

    "admin-notices": {
        "surface": "admin",
        "title": "Notices",
        "url_path": "/admin?tab=notices",
        "purpose": (
            "The Notices module is where you draft, review, publish, corrigenda, "
            "and archive tender notices. Every published notice appears on the "
            "public notice board (`/`) and drives all downstream flows: "
            "registration, bidding, evaluation, and awards. The Master Admin is "
            "the only role that can toggle 'Publish immediately'."
        ),
        "prerequisites": [
            "Admin login (Master Admin required to publish immediately)",
            "At least one tender template if using Tender Builder integration",
        ],
        "actions": [
            {"id": "new-notice", "label": "Draft a new tender notice",
             "when": "You need to publish a new tender, RFP, or RFQ.",
             "steps": [
                 "Click **NEW NOTICE** (top-right of the Notices tab).",
                 "Fill in **Title** (≥ 3 chars) and **Description** (≥ 10 chars).",
                 "Pick the **Type** (tender / rfp / rfq) and **Country**.",
                 "Optionally attach documents via drag-and-drop.",
                 "Tick **Publish immediately** if you are Master Admin — otherwise Save as draft.",
                 "Click **CREATE NOTICE**. A green toast confirms creation.",
             ],
             "expected": "Draft appears in the notices list. If published, notice_ref is generated (e.g. `PMC-NOT-2026-0042`) and it appears on the public board within 30 sec.",
             "controls": [
                 {"name": "Title",                  "desc": "Public headline. Bug #20: min 3 chars enforced with clear toast."},
                 {"name": "Description",            "desc": "Notice body — supports Markdown. Min 10 chars."},
                 {"name": "Publish immediately",    "desc": "Bug #21: only enabled for Master Admin (case-insensitive role check tolerates 'master_admin', 'Master Admin', 'MASTER-ADMIN')."},
                 {"name": "Type",                   "desc": "tender · rfp · rfq — drives which registration section is required."},
                 {"name": "Country",                "desc": "ISO alpha-2 code (KZ default). Multi-country tenders — leave global."},
                 {"name": "Attachments",            "desc": "PDF/DOCX up to 25 MB each. Stored server-side, downloadable from public notice detail page."},
             ],
             "errors": [
                 {"code": "HTTP 422", "msg": "Title minimum 3 characters",         "fix": "Type at least 3 characters into Title."},
                 {"code": "HTTP 422", "msg": "Description minimum 10 characters",  "fix": "Description body is required and must be ≥ 10 characters."},
                 {"code": "Checkbox disabled", "msg": "Publish immediately is greyed out",
                  "fix":  "Your role isn't Master Admin. Save as draft and ask a Master Admin to publish."},
             ],
             "screenshot": "admin-notices-new.png"},

            {"id": "review-draft", "label": "Review and publish a draft notice",
             "when": "A reviewer/staff member has left a draft that needs Master Admin sign-off.",
             "steps": [
                 "In the Notices list, filter by status = `draft`.",
                 "Click the draft row to open the detail panel.",
                 "Review title, description, attachments.",
                 "Tick **Publish immediately** and click **UPDATE** — the notice goes live.",
             ],
             "expected": "Row status flips from `draft` → `published`. `Cache-Control: no-store` on `/admin/all` means the list refreshes immediately.",
             "controls": [
                 {"name": "Status filter", "desc": "draft / published / archived. Deep-linkable via `?tab=notices&status=draft`."},
             ],
             "errors": [
                 {"code": "HTTP 403",   "msg": "You cannot publish this notice",
                  "fix":  "Reviewer roles cannot publish. Ask Master Admin."},
             ],
             "screenshot": "admin-notices-review.png"},

            {"id": "corrigenda", "label": "Issue a corrigenda on a published notice",
             "when": "A material change is needed after publication (deadline, scope, EMD amount).",
             "steps": [
                 "Open the Corrigenda tab (adjacent to Notices).",
                 "Click **NEW CORRIGENDA** and pick the parent notice ref.",
                 "Describe the change (min 20 chars — this is a legal amendment).",
                 "Attach the amended clause PDF if any.",
                 "Click **PUBLISH CORRIGENDA**. An email is sent to every registered supplier for that notice.",
             ],
             "expected": "Parent notice detail page gets a red 'CORRIGENDA #1' ribbon that expands to the amendment text. Supplier emails go out via Resend within 60 sec.",
             "controls": [
                 {"name": "Parent notice",     "desc": "Dropdown of all published notices — cannot corrigend a draft."},
                 {"name": "Amendment body",    "desc": "≥ 20 chars, required — displayed verbatim to bidders."},
             ],
             "errors": [
                 {"code": "HTTP 409", "msg": "Corrigenda cannot be issued on archived notices",
                  "fix": "Un-archive the notice first via the Archive filter."},
             ],
             "screenshot": "admin-corrigenda-new.png"},
        ],
    },

    "admin-registrations": {
        "surface": "admin",
        "title": "Registrations",
        "url_path": "/admin?tab=registrations",
        "purpose": (
            "Registrations is where reviewers approve, reject, or ask for "
            "clarification on supplier registration submissions. Each registration "
            "is scoped to a status (submitted / under_review / needs_clarification "
            "/ approved / rejected / draft) and can carry document attachments. "
            "Filter tabs use the reviewer's session state — Bug #15 ensures the "
            "previously-selected row clears when you switch tabs."
        ),
        "prerequisites": ["Admin login as `admin` or `reviewer` role"],
        "actions": [
            {"id": "review-submitted", "label": "Review a submitted registration",
             "when": "A supplier has completed all 5 sections and clicked Submit.",
             "steps": [
                 "Open **Registrations** tab (`/admin?tab=registrations`).",
                 "The default filter is `submitted` — click any row on the left.",
                 "Right pane shows: company details, entity type, primary sector, KZ licenses, business description, and uploaded documents.",
                 "Click **View** or **Download** on each document to inspect it.",
                 "Fill **Reviewer notes** (required for reject / clarify actions).",
                 "Click **APPROVE**, **REQUEST CLARIFICATION**, or **REJECT**.",
             ],
             "expected": "Toast confirms the action ('Approval recorded' / 'Clarification recorded' / 'Rejection recorded'). Filter auto-switches to the new status tab so you see where the record went.",
             "controls": [
                 {"name": "Status filter tabs",   "desc": "submitted · under_review · needs_clarification · approved · rejected · draft. Bug #15: switching clears the selected row."},
                 {"name": "Nudge stale drafts",   "desc": "Emails everyone whose draft is > 7 days old. Bug #46: clearer 'Reminders sent to X of Y stale drafts' toast, or 'No stale drafts found' when none match."},
                 {"name": "Reviewer notes",       "desc": "Required for reject / clarify — an audit trail entry."},
             ],
             "errors": [
                 {"code": "HTTP 400", "msg": "Notes required for this action",
                  "fix": "Type a reason in the Reviewer notes textarea before clicking Reject or Request Clarification."},
                 {"code": "Uploaded document opens 404",
                  "msg": "Document URL returns Not Found",
                  "fix": "Attachment was pruned during storage cleanup. Ask the supplier to re-upload."},
             ],
             "screenshot": "admin-registrations-review.png"},

            {"id": "nudge-stale", "label": "Nudge stale draft applicants",
             "when": "Weekly hygiene, or before closing a tender that draws a specific supplier segment.",
             "steps": [
                 "Click **NUDGE STALE DRAFTS** (top-right of the Registrations tab).",
                 "The button greys out and text changes to `Sending…`.",
                 "Within ~30 sec a toast appears with the count.",
             ],
             "expected": "Info toast if 0 checked, Warning toast if all checked but none matched threshold, Success toast with count if reminders sent.",
             "controls": [
                 {"name": "NUDGE STALE DRAFTS button", "desc": "Uses `POST /api/v1/registrations/admin/send-reminders`. Threshold: 7 days since last edit."},
             ],
             "errors": [
                 {"code": "HTTP 401 / redirect to login",
                  "msg": "Session expired mid-nudge",
                  "fix": "Log in again and re-click. Reminders are idempotent — no supplier gets nudged twice."},
             ],
             "screenshot": "admin-registrations-nudge.png"},
        ],
    },

    "admin-vendors": {
        "surface": "admin",
        "title": "Vendors",
        "url_path": "/admin?tab=vendors",
        "purpose": (
            "Vendors is the approved-supplier directory. From here you invite new "
            "vendors (single email or bulk CSV), fill in the full registration "
            "form on behalf of an offline supplier, filter by verification/active "
            "status, and see per-vendor KPI dashboards (days approved, review "
            "turnaround, KZ licenses held, business categories declared)."
        ),
        "prerequisites": [
            "Admin login as `admin` or `staff_admin`",
            "For Bulk invite: a UTF-8 CSV with columns email,company_name,contact_name,country",
        ],
        "actions": [
            {"id": "invite-single", "label": "Invite a single vendor",
             "when": "You know a supplier by email and want to pre-register them.",
             "steps": [
                 "Click **INVITE VENDOR** (top-right of the Vendors tab).",
                 "Fill vendor email, company name, contact name, and country (default KZ).",
                 "Click **SEND INVITATION**.",
             ],
             "expected": "Success toast with the auto-generated vendor_ref (e.g. `PMC-VEN-2026-0189`). The vendor receives an email via Resend with a magic-link to verify their address and set a password. Row appears in the Vendors list with `pending_verify` badge.",
             "controls": [
                 {"name": "Vendor email",     "desc": "Required, RFC-valid. Also becomes the login username."},
                 {"name": "Company name",     "desc": "Legal name — shown in the KPI dashboard header."},
                 {"name": "Country",          "desc": "ISO alpha-2. KZ default; drives which licenses list applies."},
             ],
             "errors": [
                 {"code": "HTTP 409", "msg": "A vendor with this email already exists",
                  "fix": "Search for the existing vendor in the list; use Resend invite from the vendor row."},
                 {"code": "HTTP 422", "msg": "Vendor email invalid",
                  "fix": "Emailing standard: `local@domain.tld`."},
             ],
             "screenshot": "admin-vendors-invite.png"},

            {"id": "add-fill-fullform", "label": "Add and fill the full registration form",
             "when": "A supplier delivered a paper application; you're transcribing it into the system.",
             "steps": [
                 "Click **ADD & FILL FULL FORM** — you're redirected to `/admin/vendors/new`.",
                 "Fill Section A (company details), B (contacts + signatory), C (business categories), D (KZ licenses), E (bank details + declarations).",
                 "Click **CREATE**. Bug #63: you're redirected to `/admin?tab=vendors` so the new vendor is visible immediately.",
             ],
             "expected": "Toast confirms creation and mode (Active immediately / Verify required). Vendor row appears at the top of the Vendors list.",
             "controls": [
                 {"name": "Active immediately",   "desc": "Skips email verification. Use only when the supplier is physically present."},
                 {"name": "Send verify email",    "desc": "Standard flow — supplier gets a magic-link email to confirm the address."},
             ],
             "errors": [
                 {"code": "HTTP 409", "msg": "Draft with this email already exists",
                  "fix": "Bug #76: the frontend resets document_slots + draftId when you change the email. If it still fires, close and re-open the form."},
             ],
             "screenshot": "admin-vendors-fullform.png"},

            {"id": "bulk-invite", "label": "Bulk invite vendors via CSV",
             "when": "You have a list of 10-500 suppliers to onboard at once.",
             "steps": [
                 "Click **BULK INVITE (CSV)**.",
                 "Drag a UTF-8 CSV with columns `email,company_name,contact_name,country`.",
                 "Preview shows the first 5 rows + parse errors (missing columns, invalid emails).",
                 "Click **SEND ALL** — a progress bar shows N/total sent.",
             ],
             "expected": "Modal closes with a summary: `X invited · Y skipped (duplicate) · Z failed (invalid email)`. The Vendors list auto-reloads.",
             "controls": [
                 {"name": "CSV upload",       "desc": "UTF-8-BOM tolerant (Bug #8 fixed for Cyrillic company names)."},
                 {"name": "Send all button",  "desc": "Fires the invites in batches of 20 to respect Resend rate limits."},
             ],
             "errors": [
                 {"code": "HTTP 400", "msg": "CSV missing required column 'email'",
                  "fix": "Ensure the header row is exactly `email,company_name,contact_name,country`."},
             ],
             "screenshot": "admin-vendors-bulk.png"},

            {"id": "vendor-kpi", "label": "Inspect a vendor's KPI dashboard",
             "when": "Diligence check before awarding a contract, or quarterly performance review.",
             "steps": [
                 "Click any row in the Vendors list.",
                 "Right panel loads the KPI dashboard.",
                 "Four tiles: Days approved · Review turnaround (h) · KZ licenses · Categories.",
                 "Below: KZ licenses held (list), Operating regions, Business categories declared.",
             ],
             "expected": "KPI panel refreshes within 500 ms of clicking. Blank tiles for very new vendors — populate after first tender participation.",
             "controls": [
                 {"name": "Days approved",       "desc": "Days since the vendor's registration was Approved."},
                 {"name": "Review turnaround",   "desc": "Hours between Submitted and Approved decision."},
             ],
             "errors": [
                 {"code": "KPI loading forever",
                  "msg": "Spinner never resolves",
                  "fix": "Vendor might be in `pending_verify` state — KPI is only computed after verification. Check the badge on the row."},
             ],
             "screenshot": "admin-vendors-kpi.png"},
        ],
    },

    "admin-bidding": {
        "surface": "admin",
        "title": "Bidding Ops",
        "url_path": "/admin?tab=bidding",
        "purpose": (
            "Bidding Ops manages the multi-stage bid pipeline: EMD receipt → "
            "Admin flag → Certifier clearance → Legal → Accounting → Committee "
            "vote → Award. It also hosts the bid committee formation flow "
            "(internal + external invitees, chairperson, quorum) and the "
            "dissolve/re-form workflow."
        ),
        "prerequisites": [
            "Admin login as `admin` or `committee_member`",
            "At least one published notice with received EMD",
        ],
        "actions": [
            {"id": "form-committee", "label": "Form a bid committee",
             "when": "A tender has attracted the minimum number of bids and evaluation is ready to start.",
             "steps": [
                 "In the Bidding Ops tab, click **FORM COMMITTEE**.",
                 "Type the notice ref (e.g. `PMC-NOT-2026-0042`).",
                 "Tick internal member checkboxes (admin pool). Chairperson dropdown auto-filters to selected members.",
                 "Set quorum (auto-capped to selected member count).",
                 "Optionally add external invitees (name + email + designation) — they'll receive email invites with a magic-link.",
                 "Click **FORM COMMITTEE**.",
             ],
             "expected": "Success toast: 'Committee formed · N internal member(s) · M external invited by email'. Committee appears under **Active committees** at the top of the panel.",
             "controls": [
                 {"name": "Notice ref",        "desc": "Must match an existing notice. One committee per notice at a time."},
                 {"name": "Member checkboxes", "desc": "Tick to include. Chair dropdown intersects with this selection."},
                 {"name": "Chairperson",       "desc": "Must be a member. Casts the deciding vote in case of tie."},
                 {"name": "Quorum",            "desc": "Minimum votes required to close the committee. ≤ member count."},
                 {"name": "External invitee",  "desc": "Bug #9b: dissolve button now sends CSRF token — no more silent 403."},
             ],
             "errors": [
                 {"code": "HTTP 409",
                  "msg": "Open committee already exists for this tender",
                  "fix": "Dissolve the existing committee first (see Dissolve action below), then re-form."},
                 {"code": "HTTP 400",
                  "msg": "Missing required fields",
                  "fix": "Notice ref, chairperson, and at least one member must all be set. Bug #9d: toast now describes the exact missing field."},
             ],
             "screenshot": "admin-bidding-form-committee.png"},

            {"id": "dissolve-committee", "label": "Dissolve an active committee",
             "when": "Committee is deadlocked, or the tender itself was cancelled.",
             "steps": [
                 "Locate the committee row under **Active committees**.",
                 "Click **DISSOLVE COMMITTEE**.",
                 "Type a reason (≥ 8 chars) in the prompt.",
                 "Confirm.",
             ],
             "expected": "Success toast: 'Committee dissolved · notice_ref · reason: \"...\"'. Row moves to **Recently closed / dissolved** section.",
             "controls": [
                 {"name": "Dissolve reason",   "desc": "Audit trail entry, ≥ 8 chars. Shown italicised in the closed strip."},
             ],
             "errors": [
                 {"code": "HTTP 403",
                  "msg": "CSRF token missing or invalid",
                  "fix": "Bug #9b: fixed in v38. If you still see this, hard-refresh Safari to pick up main.95d55513.js."},
                 {"code": "HTTP 409",
                  "msg": "Committee already closed",
                  "fix": "Someone else dissolved it. Refresh the panel."},
             ],
             "screenshot": "admin-bidding-dissolve.png"},

            {"id": "bid-decide", "label": "Admin-flag or reject a bid",
             "when": "A bid has cleared EMD receipt and is awaiting Admin sign-off before moving to Certifier.",
             "steps": [
                 "Scroll to the **Bids** table.",
                 "Filter by status = `emd_paid` (or use the free-text search).",
                 "For each bid, click **FLAG TO CERTIFIER** or **REJECT**.",
             ],
             "expected": "Bid status transitions to `admin_flagged` or `rejected`. Row moves to the corresponding filter section.",
             "controls": [
                 {"name": "Status filter",     "desc": "9-state dropdown covering the full pipeline."},
                 {"name": "Assign certifier",  "desc": "Opens a modal to pick a certifier + schedule an inspection."},
             ],
             "errors": [
                 {"code": "HTTP 403", "msg": "You cannot decide this bid",
                  "fix": "Only `admin` and `staff_admin` roles can flag; reviewers can only view."},
             ],
             "screenshot": "admin-bidding-bids-table.png"},
        ],
    },

    "admin-escrow": {
        "surface": "admin",
        "title": "Escrow (EMD)",
        "url_path": "/admin?tab=escrow",
        "purpose": (
            "Escrow is the governance-first EMD ledger. Every joint account is "
            "jointly operated by two officers (one from PMC, one from the escrow "
            "institution) and every release requires BOTH to sign the same "
            "action. The panel shows: joint accounts, the transactions ledger, "
            "and a reconciliation (ledger vs bank) view. Bug #9c added a red "
            "governance banner and 409 backend guard when both officers share "
            "the same email — dual-signature is impossible in that state."
        ),
        "prerequisites": [
            "Admin login as `admin` or `accounting` or `escrow_agent`",
            "At least one active joint account with DISTINCT emails on each officer",
        ],
        "actions": [
            {"id": "new-joint-account", "label": "Create a new joint escrow account",
             "when": "A new escrow relationship is set up with a bank or trustee.",
             "steps": [
                 "Click **NEW JOINT ACCOUNT** (Joint Escrow Accounts section).",
                 "Enter account display name (e.g. 'PMC-KZ Tender EMD Escrow #2').",
                 "Institution name (e.g. 'Kaspi Bank').",
                 "Account number + IBAN + SWIFT + currency (USD/EUR/KZT).",
                 "PMC officer: name + email + designation.",
                 "Escrow officer: name + email + designation. **Must be a different person / different email.**",
                 "Click **CREATE**.",
             ],
             "expected": "Success toast; account card renders under Joint Escrow Accounts.",
             "controls": [
                 {"name": "PMC officer email",    "desc": "Represents PMC on the joint control. Must be different from Escrow officer email."},
                 {"name": "Escrow officer email", "desc": "Represents the bank / trustee. Bug #9c: creation refuses same email on both sides."},
                 {"name": "Currency",             "desc": "3-letter ISO. Default USD; KZT for local wires."},
             ],
             "errors": [
                 {"code": "HTTP 400",
                  "msg": "PMC officer and Escrow officer must be different people",
                  "fix": "Use a distinct email for the escrow officer (a real trustee at the bank, or issue a magic-link via `POST /api/v1/escrow/magic-tokens`)."},
             ],
             "screenshot": "admin-escrow-new-account.png"},

            {"id": "record-emd", "label": "Record an inbound EMD receipt",
             "when": "The bank confirms a bidder's EMD has landed in the joint account.",
             "steps": [
                 "Click **RECORD INBOUND EMD**.",
                 "Pick the joint account from the dropdown (only active accounts show).",
                 "Enter bid_ref, notice_ref, vendor_ref, amount, currency, bank reference (UTR).",
                 "Click **RECORD RECEIPT**.",
             ],
             "expected": "Transaction row appears in the ledger with status `received`.",
             "controls": [
                 {"name": "Bank reference",   "desc": "UTR / SWIFT MT-103 reference — audit trail."},
                 {"name": "Amount",           "desc": "> 0 required. Currency must match the account currency."},
             ],
             "errors": [
                 {"code": "HTTP 404", "msg": "Active escrow account not found",
                  "fix": "Account may have been deactivated. Re-activate it via patch endpoint or create a new one."},
             ],
             "screenshot": "admin-escrow-record-emd.png"},

            {"id": "sign-release", "label": "Sign a release action",
             "when": "The committee has awarded the contract and the winning bidder's EMD is to be released.",
             "steps": [
                 "Locate the received transaction in the ledger.",
                 "Verify the joint account has DISTINCT emails on both officers — if not, a red governance banner will block this step.",
                 "Click **SIGN · RELEASE TO CONTRACTOR** (or the appropriate action).",
                 "The signature card for your side (PMC or Escrow officer) turns green.",
                 "The other officer must also sign the same action — they use the same button while logged in as their email, or via magic-link if external.",
             ],
             "expected": "Blue info toast: 'Signed as PMC officer — awaiting the Escrow officer. Nothing has been transferred yet.' Once both sides sign, a green success toast: 'Both officers signed — Release is now unlocked.'",
             "controls": [
                 {"name": "Sign buttons",     "desc": "Three actions: release_to_contractor · release_to_vendor · forfeit. Bug #9c: disabled if governance broken (same email on both sides)."},
                 {"name": "Release button",   "desc": "Only fires after both signatures match. Bug #9c: label reads 'RELEASE (BLOCKED — FIX OFFICERS)' when governance broken."},
             ],
             "errors": [
                 {"code": "HTTP 409",
                  "msg": "This joint escrow account has the SAME email on both officers ... Nothing has been signed.",
                  "fix": "Edit the account and set the Escrow officer to a different email, or issue a magic-link for an external trustee via `POST /api/v1/escrow/magic-tokens`."},
                 {"code": "HTTP 409",
                  "msg": "Transaction already released_to_contractor",
                  "fix": "You can't re-sign a released transaction. Nothing to do."},
             ],
             "screenshot": "admin-escrow-sign-release.png"},

            {"id": "release", "label": "Fire the release once dual-signed",
             "when": "Both officers have signed the same action.",
             "steps": [
                 "Click **RELEASE (UNLOCKED)** on the transaction row.",
                 "Confirm the release amount + beneficiary in the browser prompt.",
             ],
             "expected": "Green toast: 'Release recorded — ledger closed'. Status flips to `released_to_contractor` / `released_to_vendor` / `forfeited`.",
             "controls": [
                 {"name": "Release confirmation", "desc": "Native confirm() dialog with amount and action — prevents accidental release."},
             ],
             "errors": [
                 {"code": "HTTP 409",
                  "msg": "Both officers must sign the same action before release",
                  "fix": "Bug #9d: toast now explicitly shows what each side has signed. Ensure both sides picked the same action."},
             ],
             "screenshot": "admin-escrow-release.png"},

            {"id": "magic-link", "label": "Issue a magic-link to an external escrow officer",
             "when": "The trustee at the bank does not need a full staff account.",
             "steps": [
                 "Currently API-only (no UI form yet).",
                 "```bash",
                 "curl -X POST https://www.pmcmanagers.com/api/v1/escrow/magic-tokens \\",
                 "  -b cookies.txt -H \"X-CSRF-Token: $CSRF\" \\",
                 "  -H \"Content-Type: application/json\" \\",
                 "  -d '{\"account_id\":\"<ACC_ID>\",\"officer_email\":\"trustee@bank.com\"}'",
                 "```",
                 "Response: `{\"token\": \"...\", \"portal_url\": \"/escrow/officer/<token>\"}`",
                 "Email the portal_url to the trustee.",
             ],
             "expected": "Trustee opens the URL → sees the pending transactions on their account → clicks Sign — no staff login required.",
             "controls": [
                 {"name": "officer_email",     "desc": "Must match one of the two officer emails on the account."},
             ],
             "errors": [
                 {"code": "HTTP 400",
                  "msg": "Officer email is not on this joint account",
                  "fix": "Update the account first with the trustee's email, then re-issue the token."},
             ],
             "screenshot": "admin-escrow-magic-token.png"},
        ],
    },

    "admin-evaluation": {
        "surface": "admin",
        "title": "Evaluation",
        "url_path": "/admin?tab=evaluation",
        "purpose": (
            "Evaluation covers the technical + commercial scoring of bids by "
            "the committee. It manages: rubric setup (weights + minimum "
            "technical cutoff), Conflict-of-Interest declaration per evaluator, "
            "envelope locking (Tech + Comm cannot be edited after lock), scoring "
            "entry, and the final Award Report generation. Bug #49 hardened the "
            "rubric validators (weights sum to 1.0, per-criterion 0-1, min-tech "
            "0-100). Bug #52 stops re-scoring after envelope lock."
        ),
        "prerequisites": [
            "Admin login as `admin`, `committee_member`, or `reviewer`",
            "At least one committee formed for the notice",
            "COI declaration submitted by every evaluator",
        ],
        "actions": [
            {"id": "setup-rubric", "label": "Set up the scoring rubric",
             "when": "Immediately after committee formation, before any evaluator signs in.",
             "steps": [
                 "Open the Evaluation tab and enter the notice_ref.",
                 "In the Scoring Rubric card, fill each criterion's **Weight** (0–1). Sum must be exactly 1.00.",
                 "Set the **Commercial weight** (0–1) — controls Tech/Comm split.",
                 "Set the **Minimum technical cutoff** (0–100 percent).",
                 "The **SAVE RUBRIC** button is disabled while any error is shown.",
                 "Click **SAVE RUBRIC**.",
             ],
             "expected": "Green toast. Committee members can now start scoring.",
             "controls": [
                 {"name": "Weight (per criterion)",  "desc": "0 ≤ w ≤ 1. Sum must equal 1.00. Bug #49: live validation."},
                 {"name": "Max score (per criterion)","desc": "Server enforces individual scores ≤ max. Bug #49."},
                 {"name": "Commercial weight",        "desc": "0 ≤ cw ≤ 1. Technical gets (1 - cw)."},
                 {"name": "Minimum technical cutoff", "desc": "0 ≤ m ≤ 100. Bids below this are auto-disqualified before commercial opening."},
             ],
             "errors": [
                 {"code": "HTTP 422",
                  "msg": "Technical criteria weights must sum to 1.0 (got X.XX)",
                  "fix": "Adjust rows so weights sum to 1.00 (100%)."},
                 {"code": "HTTP 422",
                  "msg": "minimum_technical must be between 0 and 100",
                  "fix": "Use percent form (60 for 60%, not 0.60)."},
             ],
             "screenshot": "admin-evaluation-rubric.png"},

            {"id": "declare-coi", "label": "Declare Conflict-of-Interest",
             "when": "Before scoring any bid on a tender you're evaluating.",
             "steps": [
                 "In the Evaluation tab, click **DECLARE COI**.",
                 "Answer 'Do you have a conflict?' — yes/no.",
                 "If yes: describe the conflict (required).",
                 "Submit.",
             ],
             "expected": "Green toast: 'COI declared'. If declared yes, scoring is blocked for you (backend 403).",
             "controls": [
                 {"name": "Has conflict",     "desc": "Boolean — required."},
                 {"name": "Details",          "desc": "Required when 'yes' — audit trail."},
             ],
             "errors": [
                 {"code": "HTTP 400",
                  "msg": "You must declare Conflict-of-Interest before scoring",
                  "fix": "Declare first, then retry scoring."},
             ],
             "screenshot": "admin-evaluation-coi.png"},

            {"id": "score-bid", "label": "Score a bid",
             "when": "After rubric + COI + envelope open.",
             "steps": [
                 "Enter bid_id (from Bidding Ops).",
                 "Pick envelope kind: technical or commercial.",
                 "For technical: enter a score per criterion (0 ≤ s ≤ max_score).",
                 "For commercial: enter a single commercial score (0–100).",
                 "Add remarks.",
                 "Click **SUBMIT SCORE**.",
             ],
             "expected": "Green toast. Scores persist and are visible in the Award Report preview.",
             "controls": [
                 {"name": "Bid id",           "desc": "Mongo ObjectId. Auto-completed from the Bidding Ops filter."},
                 {"name": "Scores per criterion","desc": "Backend validates each value is within [0, max_score]. Bug #49."},
             ],
             "errors": [
                 {"code": "HTTP 409",
                  "msg": "The technical envelope for <notice> was locked at <timestamp>. Scores can no longer be submitted or edited.",
                  "fix": "Bug #52: envelope is locked. Generate the Award Report — you can view saved scores but not edit."},
                 {"code": "HTTP 422",
                  "msg": "Score for 'X' must be between 0 and 100 (got Y)",
                  "fix": "Correct the specific row identified in the error and resubmit."},
             ],
             "screenshot": "admin-evaluation-score.png"},

            {"id": "lock-envelope", "label": "Lock Tech or Commercial envelope",
             "when": "All evaluators have scored. Lock prevents further edits.",
             "steps": [
                 "In the Evaluation tab, click **LOCK TECHNICAL** or **LOCK COMMERCIAL**.",
                 "Confirm the lock (irreversible).",
             ],
             "expected": "Green toast: 'Envelope locked'. Backend stores locked_at + locked_by. All subsequent score submissions on this envelope return HTTP 409.",
             "controls": [
                 {"name": "Lock button",       "desc": "One per envelope. Bug #52: guards score endpoint too."},
             ],
             "errors": [
                 {"code": "HTTP 409",
                  "msg": "Envelope already locked",
                  "fix": "Nothing to do — proceed to Award Report generation."},
             ],
             "screenshot": "admin-evaluation-lock.png"},

            {"id": "award-report", "label": "Generate the Award Report",
             "when": "After both envelopes are locked and all scores are in.",
             "steps": [
                 "Click **GENERATE AWARD REPORT**.",
                 "The report renders inline: bid-by-bid technical + commercial totals, weighted score, ranking.",
                 "Download as PDF via the print icon.",
             ],
             "expected": "Recommendation row: bid_ref + vendor_name + total_score + rank. Master Admin uses this to trigger the Award step in the Awards & POs panel.",
             "controls": [
                 {"name": "Print / PDF",       "desc": "WeasyPrint server-side render — includes audit trail + signatures."},
             ],
             "errors": [
                 {"code": "Missing scores warning",
                  "msg": "Not all bids have technical + commercial scores",
                  "fix": "Return to Score Bid and fill missing rows before generating the final report."},
             ],
             "screenshot": "admin-evaluation-award-report.png"},
        ],
    },

    # -------------------------------------------------------------------------
    # The remaining 16 admin tabs + 3 non-admin surfaces are STUBBED.
    # They follow the same pattern; content authoring is Phase 2.
    # -------------------------------------------------------------------------
    "admin-corrigenda":     {"surface": "admin", "title": "Corrigenda",           "url_path": "/admin?tab=corrigenda",     "purpose": "Amendments to published notices — see admin-notices Corrigenda action.", "actions": [], "prerequisites": []},
    "admin-tender-builder": {"surface": "admin", "title": "Tender Builder",       "url_path": "/admin?tab=tender-builder", "purpose": "Template-driven notice creation with clone / clauses / attachments.",     "actions": [], "prerequisites": []},
    "admin-awards":         {"surface": "admin", "title": "Awards & POs",         "url_path": "/admin?tab=awards",         "purpose": "Contract award + PO issuance from evaluated bids.",                       "actions": [], "prerequisites": []},
    "admin-docusign":       {"surface": "admin", "title": "DocuSign",             "url_path": "/admin?tab=docusign",       "purpose": "Contract e-signature envelopes (JWT Grant flow).",                        "actions": [], "prerequisites": []},
    "admin-auctions":       {"surface": "admin", "title": "Reverse Auctions",     "url_path": "/admin?tab=auctions",       "purpose": "Live reverse-auction rooms with real-time bidding.",                      "actions": [], "prerequisites": []},
    "admin-meetings":       {"surface": "admin", "title": "Meetings",             "url_path": "/admin?tab=meetings",       "purpose": "Zoom-backed pre-bid, technical, commercial meetings.",                    "actions": [], "prerequisites": []},
    "admin-l1":             {"surface": "admin", "title": "L1 Comparison",        "url_path": "/admin?tab=l1",             "purpose": "Side-by-side ranked bid comparison — L1/L2/L3 across commercial values.",  "actions": [], "prerequisites": []},
    "admin-boq":            {"surface": "admin", "title": "BOQ & Contracts",      "url_path": "/admin?tab=boq",            "purpose": "Bill of Quantities editor + contract tie-back.",                          "actions": [], "prerequisites": []},
    "admin-vintel":         {"surface": "admin", "title": "Vendor Intel",         "url_path": "/admin?tab=vintel",         "purpose": "Vendor ratings, watch-list, blacklist. Bug #84: horizontal scroll wrapper.", "actions": [], "prerequisites": []},
    "admin-masters":        {"surface": "admin", "title": "Masters",              "url_path": "/admin?tab=masters",        "purpose": "Reference data — sectors, entity types, license codes, country meta.",     "actions": [], "prerequisites": []},
    "admin-permissions":    {"surface": "admin", "title": "Permissions",          "url_path": "/admin?tab=permissions",    "purpose": "Role-to-capability matrix + admin user seat management.",                  "actions": [], "prerequisites": []},
    "admin-packages":       {"surface": "admin", "title": "Packages",             "url_path": "/admin?tab=packages",       "purpose": "Kazakhstan Integrated Development Programme work packages tracker.",       "actions": [], "prerequisites": []},
    "admin-audit":          {"surface": "admin", "title": "Audit",                "url_path": "/admin?tab=audit",          "purpose": "Immutable audit trail — filter by actor / entity / time / event.",         "actions": [], "prerequisites": []},
    "admin-catalog":        {"surface": "admin", "title": "Product Catalog",      "url_path": "/admin?tab=catalog",        "purpose": "SaaS product catalogue + Stripe checkout wiring.",                        "actions": [], "prerequisites": []},
    "admin-engagements":    {"surface": "admin", "title": "Engagements",          "url_path": "/admin?tab=engagements",    "purpose": "Consulting engagement + quote pipeline tracker.",                          "actions": [], "prerequisites": []},

    # =========================================================================
    # OTHER SURFACES (stub for Phase 2)
    # =========================================================================
    "vendor-portal":        {"surface": "vendor",       "title": "Vendor Portal",           "url_path": "/vendor",            "purpose": "Bidder-facing portal: login, dashboard, bid submission, EMD payment, e-signatures, GDPR export.", "actions": [], "prerequisites": []},
    "staff-portal":         {"surface": "staff",        "title": "Staff Portal",            "url_path": "/staff",             "purpose": "Multi-role staff surface (Escrow / Certifier / Legal / Accounting / Committee).",              "actions": [], "prerequisites": []},
    "registration-portal":  {"surface": "registration", "title": "Registration Portal",     "url_path": "/register",          "purpose": "Multi-step supplier onboarding (Section A → E) with document uploads and resume tokens.",    "actions": [], "prerequisites": []},
    "public-board":         {"surface": "public",       "title": "Public Notice Board",     "url_path": "/",                  "purpose": "Anonymous browsing of open tender notices with filters (type / country).",                     "actions": [], "prerequisites": []},
    "committee-magic":      {"surface": "magic",        "title": "Committee Accept Portal", "url_path": "/committee-accept/", "purpose": "External committee invitees accept/decline via magic-link (no login required).",              "actions": [], "prerequisites": []},
    "escrow-magic":         {"surface": "magic",        "title": "Escrow Officer Portal",   "url_path": "/escrow/officer/",   "purpose": "External escrow trustees sign releases via magic-link (Bug #9c workflow).",                    "actions": [], "prerequisites": []},
}

# --- Phase-2 authoring merged in --------------------------------------------
try:
    from manual_content_extras import EXTRAS as _EXTRAS
    for _k, _v in _EXTRAS.items():
        MODULES[_k] = _v
except Exception:
    pass


def list_modules() -> list:
    return list(MODULES.keys())


def to_json_export() -> dict:
    """Compact export for the /api/v1/meta/help endpoint."""
    return {code: {
        "title":     m["title"],
        "surface":   m["surface"],
        "url_path":  m["url_path"],
        "purpose":   m["purpose"],
        "prerequisites": m.get("prerequisites", []),
        "actions":   m.get("actions", []),
    } for code, m in MODULES.items()}


if __name__ == "__main__":
    print(f"Total modules: {len(MODULES)}")
    for code, m in MODULES.items():
        actions = len(m.get("actions") or [])
        marker = "✓" if actions else "…"
        print(f"  {marker} {code:24} · {m['title']:30} · {actions} actions authored")
