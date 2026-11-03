"""
PMC Managers v2 — Comprehensive User Manual · complete content model
====================================================================
Every module has an exhaustive, machine-readable spec used by:
  * backend/routers/help_content.py -> /api/v1/meta/help -> frontend <HelpPanel>
  * tools/manual/build.py -> 151-page PDF/DOCX master training manual
  * tools/manual/testing_manual.py -> 33-page testing manual
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
            {
                "id": "view-funnel",
                "label": "Review the supplier funnel and KPIs",
                "when": "Weekly review, or before publishing a new tender.",
                "steps": [
                    "Log in via `/login` as an admin.",
                    "Land on `/admin` — you're on the Dashboard tab by default.",
                    "Review top drill-cards: AI Anomaly · Pipeline Funnel · Top-Priced Bids.",
                    "Review KPI tiles: Published Notices · Vendors · Bids · Awarded · Active Contracts.",
                    "Click any drill card to open the inline itemized breakdown table below.",
                ],
                "expected": "Live counts refresh on tab open. Clicking a drill card reveals itemized rows without page reload.",
                "controls": [
                    {"name": "AI Anomaly card", "desc": "Bids flagged by the AI outlier detector."},
                    {"name": "Pipeline Funnel card", "desc": "Bids categorized by workflow lifecycle stage."},
                    {"name": "Top-Priced card", "desc": "Top 10 highest-value commercial submissions."},
                ],
                "errors": [
                    {"code": "Tiles show 0", "msg": "Counts are empty",
                     "fix": "Confirm database has seeded notices/bids. Check `/api/v1/meta/public/stats`."},
                ],
            },
            {
                "id": "run-anomaly-detector",
                "label": "Run AI anomaly scan on a commercial bid",
                "when": "Scrutinizing high-value or suspect bids before committee evaluation.",
                "steps": [
                    "Scroll down to 'AI Anomaly Detector' section on the Dashboard.",
                    "Select a bid from the dropdown.",
                    "Click 'RUN AI CHECK'.",
                    "Inspect the anomaly score (0-100%), price deviation %, risk flags, and explanatory narrative.",
                ],
                "expected": "The AI engine analyzes bid vs peer distribution and outputs narrative justification.",
                "controls": [
                    {"name": "Bid selector", "desc": "List of bids with commercial envelopes."},
                    {"name": "RUN AI CHECK", "desc": "Triggers the AI copilot."},
                ],
                "errors": [
                    {"code": "HTTP 404", "msg": "Bid not found", "fix": "Select an existing commercial bid from the list."},
                ],
            },
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
            {
                "id": "new-notice",
                "label": "Draft a new tender notice",
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
                    {"name": "Title", "desc": "Public headline. Min 3 chars enforced with clear toast."},
                    {"name": "Description", "desc": "Notice body — supports Markdown. Min 10 chars."},
                    {"name": "Publish immediately", "desc": "Only enabled for Master Admin."},
                    {"name": "Type", "desc": "tender · rfp · rfq — drives which registration section is required."},
                    {"name": "Country", "desc": "ISO alpha-2 code (KZ default). Multi-country tenders — leave global."},
                    {"name": "Attachments", "desc": "PDF/DOCX up to 25 MB each. Stored server-side, downloadable from public notice detail page."},
                ],
                "errors": [
                    {"code": "HTTP 422", "msg": "Title minimum 3 characters", "fix": "Type at least 3 characters into Title."},
                    {"code": "HTTP 422", "msg": "Description minimum 10 characters", "fix": "Description body is required and must be ≥ 10 characters."},
                    {"code": "Checkbox disabled", "msg": "Publish immediately is greyed out",
                     "fix": "Your role isn't Master Admin. Save as draft and ask a Master Admin to publish."},
                ],
            },
            {
                "id": "review-draft",
                "label": "Review and publish a draft notice",
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
                    {"code": "HTTP 403", "msg": "You cannot publish this notice", "fix": "Reviewer roles cannot publish. Ask Master Admin."},
                ],
            },
            {
                "id": "corrigenda",
                "label": "Issue a corrigenda on a published notice",
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
                    {"name": "Parent notice", "desc": "Dropdown of all published notices — cannot corrigend a draft."},
                    {"name": "Amendment body", "desc": "≥ 20 chars, required — displayed verbatim to bidders."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Corrigenda cannot be issued on archived notices", "fix": "Un-archive the notice first via the Archive filter."},
                ],
            },
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
            "/ approved / rejected / draft) and can carry document attachments."
        ),
        "prerequisites": ["Admin login as `admin` or `reviewer` role"],
        "actions": [
            {
                "id": "review-submitted",
                "label": "Review a submitted registration",
                "when": "A supplier has completed all sections and clicked Submit.",
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
                    {"name": "Status filter tabs", "desc": "submitted · under_review · needs_clarification · approved · rejected · draft."},
                    {"name": "Reviewer notes", "desc": "Required for reject / clarify — audit trail entry."},
                ],
                "errors": [
                    {"code": "HTTP 400", "msg": "Notes required for this action", "fix": "Type a reason in the Reviewer notes textarea before clicking Reject or Request Clarification."},
                ],
            },
            {
                "id": "nudge-stale",
                "label": "Nudge stale draft applicants",
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
                    {"code": "HTTP 401", "msg": "Session expired mid-nudge", "fix": "Log in again and re-click."},
                ],
            },
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
            "status, and see per-vendor KPI dashboards."
        ),
        "prerequisites": ["Admin login as `admin` or `staff_admin`"],
        "actions": [
            {
                "id": "invite-single",
                "label": "Invite a single vendor",
                "when": "You know a supplier by email and want to pre-register them.",
                "steps": [
                    "Click **INVITE VENDOR** (top-right of the Vendors tab).",
                    "Fill vendor email, company name, contact name, and country (default KZ).",
                    "Click **SEND INVITATION**.",
                ],
                "expected": "Vendor receives a magic-link invite email via Resend within 60 seconds.",
                "controls": [
                    {"name": "Email", "desc": "Unique corporate email address."},
                    {"name": "Company name", "desc": "Legal entity name."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Vendor with this email already exists", "fix": "Use the search bar to locate existing vendor."},
                ],
            },
            {
                "id": "bulk-invite",
                "label": "Bulk-invite vendors from CSV",
                "when": "Onboarding an entire category or trade mission.",
                "steps": [
                    "Click **BULK INVITE (CSV)**.",
                    "Upload a UTF-8 CSV with columns `email,company_name,contact_name,country`.",
                    "Click **PROCESS CSV**.",
                ],
                "expected": "Summary dialog reports total processed, invites dispatched, and duplicate skips.",
                "controls": [
                    {"name": "CSV file upload", "desc": "UTF-8 encoded spreadsheet."},
                ],
                "errors": [
                    {"code": "HTTP 400", "msg": "Missing required header: email", "fix": "Ensure first row contains column headers."},
                ],
            },
        ],
    },

    "admin-bidding": {
        "surface": "admin",
        "title": "Bidding Ops",
        "url_path": "/admin?tab=bidding",
        "purpose": (
            "Bidding Ops monitors all submitted bids across all notices. View "
            "technical & commercial envelopes, bidder profiles, EMD posting "
            "status, and disqualifications."
        ),
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "filter-bids",
                "label": "Filter and inspect bids by notice or status",
                "when": "Checking submissions before committee evaluation.",
                "steps": [
                    "Open **Bidding Ops** tab.",
                    "Filter by Notice Ref or Status (submitted / under_review / awarded / rejected).",
                    "Click any bid row to inspect bidder details, submitted price, and attached documents.",
                ],
                "expected": "Bid summary card displays price breakdown, submission timestamp, and document links.",
                "controls": [
                    {"name": "Notice Ref Filter", "desc": "Targeted tender selection."},
                    {"name": "Status Filter", "desc": "Lifecycle stage filter."},
                ],
                "errors": [
                    {"code": "HTTP 404", "msg": "Notice not found", "fix": "Confirm notice_ref syntax."},
                ],
            },
        ],
    },

    "admin-escrow": {
        "surface": "admin",
        "title": "Escrow (EMD)",
        "url_path": "/admin?tab=escrow",
        "purpose": (
            "Escrow is the governance-first EMD ledger. Every joint account is "
            "operated by two officers (one PMC, one escrow institution) and every "
            "release requires BOTH to sign the same action."
        ),
        "prerequisites": ["Admin login as `admin` or `accounting` or `escrow_agent`"],
        "actions": [
            {
                "id": "new-joint-account",
                "label": "Create a new joint escrow account",
                "when": "A new escrow relationship is set up with a bank or trustee.",
                "steps": [
                    "Click **NEW JOINT ACCOUNT**.",
                    "Enter account display name, institution name, IBAN/SWIFT, and currency.",
                    "PMC officer: name + email.",
                    "Escrow officer: name + email (must be distinct).",
                    "Click **CREATE**.",
                ],
                "expected": "Account created with dual-custody verification rules.",
                "controls": [
                    {"name": "PMC officer email", "desc": "Internal authority."},
                    {"name": "Escrow officer email", "desc": "External bank/trustee representative."},
                ],
                "errors": [
                    {"code": "HTTP 400", "msg": "Officers must have distinct emails", "fix": "Provide two separate emails."},
                ],
            },
            {
                "id": "sign-release",
                "label": "Dual-sign an EMD release or refund",
                "when": "Tender award is sealed and non-winning EMDs are ready for refund.",
                "steps": [
                    "Locate the transaction in the ledger.",
                    "Click **SIGN · RELEASE TO VENDOR**.",
                    "Confirm action. Signature 1 recorded.",
                    "The second officer signs using their credentials or magic-link.",
                    "Click **RELEASE (UNLOCKED)** to trigger payment payout.",
                ],
                "expected": "Status flips to `released_to_vendor` and payment rail webhook fires.",
                "controls": [
                    {"name": "Sign action", "desc": "release_to_contractor · release_to_vendor · forfeit."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Both officers must sign the same action", "fix": "Ensure both officers pick identical action."},
                ],
            },
        ],
    },

    "admin-evaluation": {
        "surface": "admin",
        "title": "Evaluation",
        "url_path": "/admin?tab=evaluation",
        "purpose": (
            "Evaluation covers the technical + commercial scoring of bids by "
            "the committee: rubric setup, COI declarations, envelope locking, "
            "and final Award Report generation."
        ),
        "prerequisites": ["Admin or committee_member role"],
        "actions": [
            {
                "id": "setup-rubric",
                "label": "Configure technical & commercial scoring rubric",
                "when": "Before evaluators begin scoring.",
                "steps": [
                    "Enter notice_ref in Evaluation tab.",
                    "Set criterion weights (must sum to exactly 1.00).",
                    "Set Commercial weight (e.g. 0.40 for 40%) and Minimum technical cutoff (e.g. 60%).",
                    "Click **SAVE RUBRIC**.",
                ],
                "expected": "Rubric persists for all evaluators on this tender.",
                "controls": [
                    {"name": "Weights", "desc": "Sum must equal 1.00."},
                    {"name": "Min Tech Cutoff", "desc": "0-100% threshold."},
                ],
                "errors": [
                    {"code": "HTTP 422", "msg": "Weights must sum to 1.0", "fix": "Adjust weights so total is 1.00."},
                ],
            },
            {
                "id": "lock-envelopes",
                "label": "Lock Technical and Commercial envelopes",
                "when": "Evaluation scoring rounds complete.",
                "steps": [
                    "Click **LOCK TECHNICAL** when technical scoring is done.",
                    "Click **LOCK COMMERCIAL** when commercial review is finished.",
                    "Click **GENERATE AWARD REPORT** to produce L1 winner recommendation.",
                ],
                "expected": "Envelopes sealed irreversibly; award report auto-generates.",
                "controls": [
                    {"name": "Lock Tech / Comm", "desc": "Freezes scores and records timestamp."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Envelope already locked", "fix": "Proceed to Award Report."},
                ],
            },
        ],
    },

    "admin-corrigenda": {
        "surface": "admin",
        "title": "Corrigenda",
        "url_path": "/admin?tab=corrigenda",
        "purpose": "Issue and audit formal legal amendments to published notices with automated bidder notification.",
        "prerequisites": ["Admin login", "At least one published notice"],
        "actions": [
            {
                "id": "publish-corrigendum",
                "label": "Publish a corrigendum amendment",
                "when": "Specifications, dates, or terms change post-publication.",
                "steps": [
                    "Select the parent notice from the dropdown.",
                    "Provide a clear amendment summary (≥ 20 characters).",
                    "Upload the amended specification PDF if applicable.",
                    "Click **PUBLISH CORRIGENDA**.",
                ],
                "expected": "Notice is badged with Corrigendum version; email dispatched to all active bidders.",
                "controls": [
                    {"name": "Parent Notice", "desc": "Published tender reference."},
                    {"name": "Amendment Body", "desc": "Detailed legal change notice."},
                ],
                "errors": [
                    {"code": "HTTP 422", "msg": "Amendment text too short", "fix": "Provide at least 20 characters of detail."},
                ],
            },
        ],
    },

    "admin-tender-builder": {
        "surface": "admin",
        "title": "Tender Builder",
        "url_path": "/admin?tab=tender-builder",
        "purpose": "Modular template-driven notice composer with AI-assisted drafting, DPR document ingestion, and master libraries.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "ai-draft-section",
                "label": "Generate section draft with AI copilot",
                "when": "Composing complex technical specifications or scope of work.",
                "steps": [
                    "Select a draft template or clone a master.",
                    "Navigate to the desired section (e.g. Scope of Work).",
                    "Click **BUILD WITH AI**.",
                    "Review the generated 280-360 word draft; accept or edit.",
                ],
                "expected": "High-quality HTML specification authored by the AI engine.",
                "controls": [
                    {"name": "Build with AI", "desc": "Invokes backend `_llm_complete` proxy."},
                ],
                "errors": [
                    {"code": "HTTP 502", "msg": "LLM proxy timeout", "fix": "Retry request; proxy handles automatic retry."},
                ],
            },
            {
                "id": "async-dpr-ingest",
                "label": "Ingest 100MB+ DPR / Tender document",
                "when": "Converting raw client DPR (PDF/DOCX) into modular template sections.",
                "steps": [
                    "Click **ANALYSE DPR**.",
                    "Upload document (PDF, DOCX, or TXT up to 200MB).",
                    "Monitor real-time progress bar through chunk map-reduce phases.",
                    "Inspect auto-extracted sections and headers.",
                ],
                "expected": "Full document decomposed into structured template sections without size truncation.",
                "controls": [
                    {"name": "Analyse DPR", "desc": "Async background processing worker."},
                ],
                "errors": [
                    {"code": "HTTP 413", "msg": "File too large", "fix": "Ensure file is under 200MB."},
                ],
            },
        ],
    },

    "admin-awards": {
        "surface": "admin",
        "title": "Awards & POs",
        "url_path": "/admin?tab=awards",
        "purpose": "Finalize evaluated tenders, issue Letters of Award (LOA), generate Purchase Order numbers, and transition to contract.",
        "prerequisites": ["Admin login", "Evaluated tender with completed award report"],
        "actions": [
            {
                "id": "issue-award-loa",
                "label": "Issue Letter of Award (LOA)",
                "when": "Committee has selected the winning L1 bidder.",
                "steps": [
                    "Select the tender notice and winning bid.",
                    "Review agreed contract value, currency, and payment milestones.",
                    "Click **ISSUE LOA**.",
                    "System routes LOA to DocuSign for contractor and PMC countersignature.",
                ],
                "expected": "Bid status transitions to `awarded`, PO number generated, DocuSign envelope created.",
                "controls": [
                    {"name": "PO Number", "desc": "Auto-generated sequence e.g. PO-2026-0042."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Bid already awarded", "fix": "Select a pending evaluated bid."},
                ],
            },
        ],
    },

    "admin-docusign": {
        "surface": "admin",
        "title": "DocuSign",
        "url_path": "/admin?tab=docusign",
        "purpose": "Monitor and manage legally-binding electronic signature envelopes for Contracts, LOAs, NDAs, and Variations.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "track-envelope-status",
                "label": "Track envelope lifecycle and download signed PDF",
                "when": "Following up on pending contractor or executive signatures.",
                "steps": [
                    "Open DocuSign tab to view all envelopes.",
                    "Inspect status: `sent` · `delivered` · `completed` · `declined`.",
                    "For completed envelopes, click **DOWNLOAD COMBINED PDF**.",
                ],
                "expected": "Cryptographically signed PDF with audit trail certificate downloaded.",
                "controls": [
                    {"name": "Download PDF", "desc": "Combines signed document and DocuSign summary certificate."},
                ],
                "errors": [
                    {"code": "HTTP 404", "msg": "Envelope not found", "fix": "Refresh list to sync latest status."},
                ],
            },
        ],
    },

    "admin-auctions": {
        "surface": "admin",
        "title": "Reverse Auctions",
        "url_path": "/admin?tab=auctions",
        "purpose": "Real-time reverse-auction rooms with dynamic price decrement, floor controls, and anti-sniping clocks.",
        "prerequisites": ["Admin login", "Published notice with invited vendors"],
        "actions": [
            {
                "id": "create-auction",
                "label": "Configure and start live reverse auction",
                "when": "Conducting dynamic commercial bidding round.",
                "steps": [
                    "Click **NEW AUCTION**.",
                    "Select Notice Ref, starting ceiling price, floor price, and minimum decrement.",
                    "Set duration (minutes) and anti-sniping window (seconds).",
                    "Click **START AUCTION** when ready.",
                ],
                "expected": "Live websocket room opens; masked vendor aliases can place real-time undercuts.",
                "controls": [
                    {"name": "Anti-sniping", "desc": "Extends countdown if valid bid received in final seconds."},
                    {"name": "Floor Price", "desc": "Absolute minimum allowable bid limit."},
                ],
                "errors": [
                    {"code": "HTTP 400", "msg": "Floor price must be below starting price", "fix": "Correct price bounds."},
                ],
            },
        ],
    },

    "admin-meetings": {
        "surface": "admin",
        "title": "Meetings",
        "url_path": "/admin?tab=meetings",
        "purpose": "Schedule and conduct pre-bid conferences, technical clarification rounds, and committee sessions.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "schedule-meeting",
                "label": "Schedule pre-bid or committee meeting",
                "when": "Organizing official supplier clarification session.",
                "steps": [
                    "Click **SCHEDULE MEETING**.",
                    "Enter subject, agenda, associated Notice Ref, date/time, and duration.",
                    "Add invitee emails (vendors, evaluators, observers).",
                    "Click **CREATE & SEND INVITES**.",
                ],
                "expected": "Meeting room generated; calendar invites emailed to all participants.",
                "controls": [
                    {"name": "Meeting Provider", "desc": "Integrated secure WebRTC video room."},
                ],
                "errors": [
                    {"code": "HTTP 422", "msg": "Invalid date/time", "fix": "Select a future timestamp."},
                ],
            },
        ],
    },

    "admin-l1": {
        "surface": "admin",
        "title": "L1 Comparison",
        "url_path": "/admin?tab=l1",
        "purpose": "Automated side-by-side comparative statement engine generating L1/L2/L3 commercial rankings.",
        "prerequisites": ["Admin login", "Notice with multiple compliant commercial bids"],
        "actions": [
            {
                "id": "run-l1-engine",
                "label": "Generate L1 comparative analysis",
                "when": "Evaluating price competitiveness across suppliers.",
                "steps": [
                    "Select Notice Ref from the dropdown.",
                    "Click **RUN L1 COMPARISON**.",
                    "Review comparative table showing normalized pricing, currency conversions, and ranking.",
                ],
                "expected": "Lowest compliant bidder highlighted with savings percentage vs mean.",
                "controls": [
                    {"name": "Notice Selector", "desc": "Filter by active tender."},
                ],
                "errors": [
                    {"code": "HTTP 404", "msg": "No compliant bids found", "fix": "Ensure bids have been submitted and cleared."},
                ],
            },
        ],
    },

    "admin-boq": {
        "surface": "admin",
        "title": "BOQ & Contracts",
        "url_path": "/admin?tab=boq",
        "purpose": "Bill of Quantities (BOQ) line-item editor, CSV ingestion, unit-rate validation, and post-award milestone tie-back.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "manage-boq-items",
                "label": "Upload or edit Bill of Quantities items",
                "when": "Structuring line-item pricing for complex infrastructure or equipment supply.",
                "steps": [
                    "Select target notice or contract.",
                    "Click **UPLOAD BOQ CSV** or manually add line items.",
                    "Specify item description, quantity, unit of measurement, and estimated unit rate.",
                    "Save BOQ baseline.",
                ],
                "expected": "Itemized BOQ saved and attached to tender pack for vendor pricing.",
                "controls": [
                    {"name": "BOQ CSV Upload", "desc": "Columns: item_no, description, uom, qty, rate."},
                ],
                "errors": [
                    {"code": "HTTP 400", "msg": "Invalid CSV structure", "fix": "Check header row formatting."},
                ],
            },
        ],
    },

    "admin-vintel": {
        "surface": "admin",
        "title": "Vendor Intel",
        "url_path": "/admin?tab=vintel",
        "purpose": "Vendor risk intelligence, performance scorecards, watchlist moderation, and regulatory debarment enforcement.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "rate-vendor",
                "label": "Assign vendor performance score and tier band",
                "when": "Conducting quarterly performance review or logging contract delivery milestones.",
                "steps": [
                    "Locate vendor in the table.",
                    "Click **MANAGE INTEL**.",
                    "Set Score (0-100) and Band (excellent / good / fair / poor / blacklisted).",
                    "Click **SAVE RATING**.",
                ],
                "expected": "Rating saved and trust badge updated across vendor portal.",
                "controls": [
                    {"name": "Score", "desc": "0-100 numeric rating."},
                    {"name": "Band", "desc": "Classification tier driving automated gating."},
                ],
                "errors": [
                    {"code": "HTTP 400", "msg": "Reason required for blacklisting", "fix": "Provide mandatory audit justification."},
                ],
            },
        ],
    },

    "admin-masters": {
        "surface": "admin",
        "title": "Masters",
        "url_path": "/admin?tab=masters",
        "purpose": "Global system reference data: UNSPSC categories, KZ license codes, EMD rate slabs, and currencies.",
        "prerequisites": ["Master Admin login"],
        "actions": [
            {
                "id": "configure-emd-slabs",
                "label": "Configure EMD calculation slabs",
                "when": "Updating statutory EMD rates per country or project value band.",
                "steps": [
                    "Select country (e.g. Kazakhstan).",
                    "Define value brackets, percentage rates, floor, and ceiling amounts.",
                    "Click **SAVE SLABS**.",
                ],
                "expected": "New Notice EMD auto-compute widget immediately applies updated formula.",
                "controls": [
                    {"name": "Slab brackets", "desc": "Min value, max value, rate %."},
                ],
                "errors": [
                    {"code": "HTTP 422", "msg": "Overlapping brackets", "fix": "Ensure slab price ranges are continuous and non-overlapping."},
                ],
            },
        ],
    },

    "admin-permissions": {
        "surface": "admin",
        "title": "Permissions",
        "url_path": "/admin?tab=permissions",
        "purpose": "Role-Based Access Control (RBAC) matrix governing permissions across Tenders, RFPs, and RFQs for all staff roles.",
        "prerequisites": ["Master Admin login"],
        "actions": [
            {
                "id": "edit-permission-matrix",
                "label": "Update role capability matrix",
                "when": "Granting or revoking capabilities (view/create/modify/delete/publish) for staff roles.",
                "steps": [
                    "Review matrix grid mapping Roles to Document Types.",
                    "Toggle permission checkboxes.",
                    "Click **SAVE MATRIX**.",
                ],
                "expected": "Backend middleware immediately enforces updated policy on all protected routes.",
                "controls": [
                    {"name": "SAVE MATRIX", "desc": "Applies changes globally."},
                    {"name": "RESET DEFAULTS", "desc": "Restores baseline security policy."},
                ],
                "errors": [
                    {"code": "HTTP 403", "msg": "Only Master Admin can modify permissions", "fix": "Log in with Master Admin credentials."},
                ],
            },
        ],
    },

    "admin-packages": {
        "surface": "admin",
        "title": "Packages",
        "url_path": "/admin?tab=packages",
        "purpose": "Kazakhstan Integrated Development Programme multi-package procurement tracker and cross-notice bundling.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "track-programme-package",
                "label": "Create and track integrated work package",
                "when": "Managing umbrella capital project comprising multiple tender lots.",
                "steps": [
                    "Click **NEW PACKAGE**.",
                    "Enter package code, name, sector, budget, and target completion date.",
                    "Link published tender notices to the package.",
                    "Save package.",
                ],
                "expected": "Package progress roll-up updates as linked tenders advance to award.",
                "controls": [
                    {"name": "Package Code", "desc": "e.g. PKG-KZ-MED-01."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Package code exists", "fix": "Use unique package code."},
                ],
            },
        ],
    },

    "admin-audit": {
        "surface": "admin",
        "title": "Audit",
        "url_path": "/admin?tab=audit",
        "purpose": "Immutable, cryptographically verifiable audit log recording every actor, action, timestamp, IP, and entity mutation.",
        "prerequisites": ["Admin login with auditor or admin role"],
        "actions": [
            {
                "id": "search-audit-events",
                "label": "Query and verify immutable audit trail",
                "when": "Conducting compliance investigation or post-award review.",
                "steps": [
                    "Filter by Actor, Entity Type (notice, bid, escrow, user), or Date Range.",
                    "Inspect full event JSON payload including before/after deltas.",
                    "Click **VERIFY LOG INTEGRITY**.",
                ],
                "expected": "SHA-256 hash-chain verification confirms zero tampering or deleted records.",
                "controls": [
                    {"name": "Verify Integrity", "desc": "Validates cryptographic hash chain across audit blocks."},
                ],
                "errors": [
                    {"code": "HTTP 403", "msg": "Auditor permission required", "fix": "Ensure role includes audit inspection."},
                ],
            },
        ],
    },

    "admin-catalog": {
        "surface": "admin",
        "title": "Product Catalog",
        "url_path": "/admin?tab=catalog",
        "purpose": "Procurement platform product catalog managing advisory packages, tender fee tiers, and Stripe checkout links.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "manage-products",
                "label": "Create and configure catalog service package",
                "when": "Offering fee-based advisory, verification, or procurement support packages.",
                "steps": [
                    "Click **NEW PRODUCT**.",
                    "Set Name, Side (client / supplier / both), Pricing Model (fixed, range, percentage, monthly), Currency, and Amount.",
                    "Attach UNSPSC classification.",
                    "Click **SAVE PRODUCT**.",
                ],
                "expected": "Product appears on public purchasing grid and Stripe checkout activates.",
                "controls": [
                    {"name": "Pricing Model", "desc": "fixed · range · percentage · subscription."},
                ],
                "errors": [
                    {"code": "HTTP 422", "msg": "Amount required for fixed pricing", "fix": "Enter numeric price amount."},
                ],
            },
        ],
    },

    "admin-engagements": {
        "surface": "admin",
        "title": "Engagements",
        "url_path": "/admin?tab=engagements",
        "purpose": "Manage custom quote requests, buyer engagements, and one-click Stripe payment invoice generation.",
        "prerequisites": ["Admin login"],
        "actions": [
            {
                "id": "quote-engagement",
                "label": "Quote and invoice custom service request",
                "when": "A buyer requests a custom quote for procurement advisory services.",
                "steps": [
                    "Locate requested engagement in table.",
                    "Click **QUOTE**.",
                    "Enter quoted amount, currency, valid-until date, and scope notes.",
                    "Click **SAVE QUOTE**.",
                    "Click **INVOICE** to generate a direct Stripe checkout link for the buyer.",
                ],
                "expected": "Status flips to `quoted` then `invoiced`; buyer receives payment link.",
                "controls": [
                    {"name": "Invoice Button", "desc": "Generates Stripe Hosted Invoice URL."},
                ],
                "errors": [
                    {"code": "HTTP 400", "msg": "Quoted amount must be > 0", "fix": "Specify valid positive quote amount."},
                ],
            },
        ],
    },

    # =========================================================================
    # OTHER SURFACES
    # =========================================================================
    "vendor-portal": {
        "surface": "vendor",
        "title": "Vendor Portal",
        "url_path": "/vendor",
        "purpose": "Supplier operating dashboard for searching tenders, submitting encrypted bids, posting EMDs, and joining reverse auctions.",
        "prerequisites": ["Approved vendor credentials"],
        "actions": [
            {
                "id": "submit-tender-bid",
                "label": "Submit a bid on an open tender",
                "when": "Participating in an open procurement competition.",
                "steps": [
                    "Log in via `/login` → Registered Vendors.",
                    "Browse open tenders under Tenders tab.",
                    "Click **SUBMIT BID** on the target notice.",
                    "Upload Technical Envelope PDF and enter Commercial price proposal.",
                    "Acknowledge compliance declarations and submit.",
                ],
                "expected": "Bid reference issued (e.g. `PMC-BID-2026-0012`); confirmation email dispatched.",
                "controls": [
                    {"name": "Commercial Price", "desc": "Numeric value in tender currency."},
                    {"name": "Technical Proposal", "desc": "Encrypted technical submission."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Deadline passed", "fix": "Submissions close strictly at the deadline timestamp."},
                ],
            },
        ],
    },

    "staff-portal": {
        "surface": "staff",
        "title": "Staff Portal",
        "url_path": "/staff",
        "purpose": "Role-gated workspace for Certifiers, Legal Counsel, Accounting Officers, and Evaluation Committee members.",
        "prerequisites": ["Staff user login"],
        "actions": [
            {
                "id": "certify-compliance",
                "label": "Review and certify dossier compliance",
                "when": "Conducting legal or accounting clearance on a tender or vendor.",
                "steps": [
                    "Log in via `/staff/login` with your assigned role.",
                    "Open pending tasks queue.",
                    "Review attached evidence documents.",
                    "Click **CERTIFY & SIGN OFF**.",
                ],
                "expected": "Stage checkmark recorded in tender audit pipeline.",
                "controls": [
                    {"name": "Sign Off", "desc": "Applies role approval token."},
                ],
                "errors": [
                    {"code": "HTTP 403", "msg": "Unauthorized for this stage", "fix": "Ensure you are assigned the correct staff role."},
                ],
            },
        ],
    },

    "registration-portal": {
        "surface": "registration",
        "title": "Registration Portal",
        "url_path": "/register",
        "purpose": "Five-step self-service vendor onboarding wizard: Identity, Contacts, Financials, KZ Business Profile, and Signatures.",
        "prerequisites": ["Corporate email address"],
        "actions": [
            {
                "id": "complete-registration",
                "label": "Complete and submit supplier registration",
                "when": "Onboarding as an eligible supplier.",
                "steps": [
                    "Start at `/register` with your email.",
                    "Complete Section A (Company Identity & Reg No).",
                    "Proceed through Sections B (Contacts), C (Financials), D (KZ Profile), and Directors.",
                    "Tick all Section E declarations and click **SUBMIT FINAL**.",
                ],
                "expected": "Registration submitted to admin review queue; magic-token tracking page provided.",
                "controls": [
                    {"name": "Save Draft", "desc": "Saves progressive state to resume anytime."},
                ],
                "errors": [
                    {"code": "Section A Gaps", "msg": "Missing required fields", "fix": "Fill all Section A required fields before proceeding."},
                ],
            },
        ],
    },

    "public-board": {
        "surface": "public",
        "title": "Public Notice Board",
        "url_path": "/",
        "purpose": "Public-facing procurement showcase displaying published tenders, RFPs, RFQs, country statistics, and partner trust badges.",
        "prerequisites": ["None — open public access"],
        "actions": [
            {
                "id": "browse-tenders",
                "label": "Browse and filter published opportunities",
                "when": "Discovering live tenders across Kazakhstan and the CIS.",
                "steps": [
                    "Open `https://pmcmanagers.com`.",
                    "Filter by Document Type (Tender / RFP / RFQ) or Country.",
                    "Click any tender card to inspect full scope, deadline countdown, and download tender packs.",
                ],
                "expected": "Public detail page displays specifications, EMD requirements, and 'Register to Bid' button.",
                "controls": [
                    {"name": "Document Type Chips", "desc": "Instant client-side filter."},
                    {"name": "Country Dropdown", "desc": "Jurisdiction filter."},
                ],
                "errors": [
                    {"code": "HTTP 410", "msg": "Notice withdrawn", "fix": "Notice has been archived or cancelled by admin."},
                ],
            },
        ],
    },

    "committee-magic": {
        "surface": "magic",
        "title": "Committee Accept Portal",
        "url_path": "/committee-accept/",
        "purpose": "One-click external committee member appointment acceptance/decline via tokenized magic link without account creation.",
        "prerequisites": ["Magic link token sent via email"],
        "actions": [
            {
                "id": "accept-committee-appointment",
                "label": "Accept committee evaluation appointment",
                "when": "Invited by Master Admin to sit on an evaluation committee.",
                "steps": [
                    "Open the magic link received via email.",
                    "Review tender title, estimated value, and evaluation schedule.",
                    "Click **ACCEPT APPOINTMENT**.",
                ],
                "expected": "Appointment confirmed; committee roster updated to `accepted`.",
                "controls": [
                    {"name": "Accept / Decline", "desc": "Records response directly to tender governance ledger."},
                ],
                "errors": [
                    {"code": "HTTP 404", "msg": "Invalid or expired token", "fix": "Request a fresh invite from the Master Admin."},
                ],
            },
        ],
    },

    "escrow-magic": {
        "surface": "magic",
        "title": "Escrow Officer Portal",
        "url_path": "/escrow/officer/",
        "purpose": "Tokenized dual-custody approval portal allowing bank trustees to sign EMD releases without needing full platform accounts.",
        "prerequisites": ["Magic link token sent via email"],
        "actions": [
            {
                "id": "sign-magic-escrow",
                "label": "Sign joint escrow release action",
                "when": "Bank trustee reviewing an EMD refund or release request.",
                "steps": [
                    "Open the magic link received in trustee email.",
                    "Review pending transaction amount, currency, beneficiary, and PMC officer signature.",
                    "Click **SIGN ACTION**.",
                ],
                "expected": "Trustee signature recorded; release unlocks on joint account.",
                "controls": [
                    {"name": "Sign Action", "desc": "Dual-custody cryptographic sign-off."},
                ],
                "errors": [
                    {"code": "HTTP 409", "msg": "Already signed", "fix": "Transaction is already signed and locked."},
                ],
            },
        ],
    },
}

from pmc_lib.help_content_extra import EXTRA_MODULES  # noqa: E402

MODULES.update(EXTRA_MODULES)


def list_modules() -> list:
    return list(MODULES.keys())


def to_json_export() -> dict:
    """Compact export for the /api/v1/meta/help endpoint."""
    return {code: {
        "title": m["title"],
        "surface": m["surface"],
        "url_path": m["url_path"],
        "purpose": m["purpose"],
        "prerequisites": m.get("prerequisites", []),
        "actions": m.get("actions", []),
    } for code, m in MODULES.items()}


if __name__ == "__main__":
    print(f"Total modules: {len(MODULES)}")
    for code, m in MODULES.items():
        actions = len(m.get("actions") or [])
        marker = "✓" if actions else "…"
        print(f"  {marker} {code:24} · {m['title']:30} · {actions} actions authored")
