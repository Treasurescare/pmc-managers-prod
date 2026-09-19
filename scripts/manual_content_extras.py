"""Manual content — Phase 2 authoring for the remaining 22 surfaces.

Merges into MODULES in manual_content.py.
"""

EXTRAS = {
    # -------------------------------------------------------------------- ADMIN
    "admin-corrigenda": {
        "surface": "admin", "title": "Corrigenda",
        "url_path": "/admin?tab=corrigenda",
        "purpose": (
            "The Corrigenda tab lists every published amendment to any live "
            "tender notice. Each corrigenda carries an immutable version number "
            "and is emailed to every registered supplier for the parent notice. "
            "Only Master Admin can issue corrigenda on archived notices."
        ),
        "prerequisites": ["Admin login", "At least one published notice with the change scope"],
        "actions": [
            {"id": "issue-corrigenda", "label": "Issue a new corrigenda",
             "when": "A material change is required after publication (deadline, EMD, scope).",
             "steps": [
                 "Click **NEW CORRIGENDA** (top-right).",
                 "Pick the parent notice from the dropdown (only published notices listed).",
                 "Type the amendment body (≥ 20 chars). Attach the amended clause PDF if any.",
                 "Click **PUBLISH CORRIGENDA**.",
             ],
             "expected": "Corrigenda row appears in the list with version number. Suppliers receive an email within 60 sec via Resend.",
             "controls": [
                 {"name": "Parent notice", "desc": "Only published, non-archived notices."},
                 {"name": "Amendment body","desc": "Minimum 20 chars. Displayed verbatim to bidders."},
                 {"name": "Attachment",    "desc": "PDF/DOCX up to 25 MB — inline preview on public detail."},
             ],
             "errors": [
                 {"code": "HTTP 409", "msg": "Cannot corrigend an archived notice",
                  "fix": "Un-archive the notice via Notices → Archive filter → Restore."},
             ],
             "screenshot": "admin-corrigenda-new.png"},
            {"id": "history", "label": "View corrigenda history for a notice",
             "when": "Verify the amendment trail before an audit.",
             "steps": ["Click any corrigenda row to expand.", "See version, publish date, actor email, amendment body."],
             "expected": "Complete chronological history renders inline.",
             "controls": [], "errors": [], "screenshot": "admin-corrigenda-history.png"},
        ],
    },
    "admin-tender-builder": {
        "surface": "admin", "title": "Tender Builder",
        "url_path": "/admin?tab=tender-builder",
        "purpose": (
            "Tender Builder is the template-driven notice authoring surface. "
            "Templates carry standard clauses, evaluation matrices, and "
            "attachment slots. Clone existing templates to keep organisational "
            "standards; every edit is version-tracked (Bugs #69–#71 fixed the "
            "clone-attachment carryover and cascade-delete)."
        ),
        "prerequisites": ["Admin login as `admin` or `staff_admin`"],
        "actions": [
            {"id": "new-template", "label": "Create a new tender template",
             "when": "Setting up a reusable pattern for a new tender category.",
             "steps": [
                 "Click **NEW TEMPLATE**.", "Fill category, jurisdiction, default clauses.",
                 "Add attachment slots by name (e.g. 'BOQ', 'Bank guarantee').",
                 "Click **SAVE TEMPLATE**.",
             ],
             "expected": "Template appears in the list with version `v1`.",
             "controls": [
                 {"name": "Category",        "desc": "Free-form; drives Notice filter."},
                 {"name": "Default clauses", "desc": "Rich-text; appended to every notice using this template."},
             ],
             "errors": [
                 {"code": "HTTP 422", "msg": "Template name already exists in this category",
                  "fix": "Rename or edit the existing template instead of duplicating."},
             ], "screenshot": "admin-tender-builder-new.png"},
            {"id": "clone", "label": "Clone a template",
             "when": "Kick off a similar tender without redoing setup.",
             "steps": ["Locate template row.", "Click **CLONE**.",
                       "Confirm the clone name.",
                       "Bug #69: attachments are NOT carried over from the source (deliberate) — you re-attach only what's relevant."],
             "expected": "New template `v1` with cloned clauses appears at the top.",
             "controls": [], "errors": [], "screenshot": "admin-tender-builder-clone.png"},
        ],
    },
    "admin-awards": {
        "surface": "admin", "title": "Awards & POs",
        "url_path": "/admin?tab=awards",
        "purpose": (
            "Awards & POs is where the Master Admin issues a formal Contract "
            "Award to the recommended bidder and generates the Purchase Order "
            "PDF. The Award Report from Evaluation feeds into this tab; the PO "
            "PDF is DocuSign-ready (JWT Grant flow) for supplier e-signature."
        ),
        "prerequisites": ["Award Report generated for the notice", "Master Admin role"],
        "actions": [
            {"id": "issue-award", "label": "Issue a contract award",
             "when": "The Evaluation panel has produced a signed Award Report.",
             "steps": ["Pick the notice ref.", "Confirm recommended bidder.",
                       "Enter contract value, currency, start & end dates.",
                       "Click **ISSUE AWARD**."],
             "expected": "Award row created with status `awarded`; PDF generated on the server (WeasyPrint).",
             "controls": [
                 {"name": "Contract value", "desc": "Must be > 0 and match commercial bid within ± 2%."},
                 {"name": "Start / End",    "desc": "ISO dates; end > start."},
             ],
             "errors": [
                 {"code": "HTTP 409", "msg": "Award already issued for this notice",
                  "fix": "One award per notice. Cancel via Legal to re-award."},
             ], "screenshot": "admin-awards-issue.png"},
            {"id": "generate-po", "label": "Generate the PO PDF",
             "when": "After award is issued and terms are locked.",
             "steps": ["Click **GENERATE PO** on the award row.",
                       "Download the PDF or click **SEND TO DOCUSIGN** to route for e-signature."],
             "expected": "PDF opens in a new tab; DocuSign envelope ID appears when routed.",
             "controls": [], "errors": [
                 {"code": "HTTP 502", "msg": "DocuSign JWT Grant failed",
                  "fix": "Check the JWT private key in Secrets Manager hasn't expired; regenerate if needed."},
             ], "screenshot": "admin-awards-po.png"},
        ],
    },
    "admin-docusign": {
        "surface": "admin", "title": "DocuSign",
        "url_path": "/admin?tab=docusign",
        "purpose": (
            "The DocuSign panel lists every envelope routed for e-signature "
            "(Contract POs, NDAs, escrow attestations). Uses the JWT Grant "
            "OAuth flow — no per-user redirect needed. Envelope status is "
            "polled every 5 min from the DocuSign REST API."
        ),
        "prerequisites": ["DocuSign integration key + RSA private key configured", "Admin login"],
        "actions": [
            {"id": "resend-envelope", "label": "Resend a stalled envelope",
             "when": "The signer hasn't opened the email in 48 h.",
             "steps": ["Locate the envelope row (status = sent).", "Click **RESEND**.",
                       "Confirm the new expiry (default +14 d)."],
             "expected": "DocuSign reply toast; row shows updated `resent_at`.",
             "controls": [], "errors": [
                 {"code": "HTTP 400", "msg": "Envelope already completed",
                  "fix": "Cannot resend a completed envelope. Look under Archive."},
             ], "screenshot": "admin-docusign-resend.png"},
            {"id": "download-signed", "label": "Download the signed PDF",
             "when": "After envelope status = completed.",
             "steps": ["Click **DOWNLOAD SIGNED**.", "PDF streams to your browser."],
             "expected": "Signed PDF with all signature stamps + audit trail included.",
             "controls": [], "errors": [], "screenshot": "admin-docusign-download.png"},
        ],
    },
    "admin-auctions": {
        "surface": "admin", "title": "Reverse Auctions",
        "url_path": "/admin?tab=auctions",
        "purpose": (
            "Reverse Auctions hosts live, downward-price bidding rooms. "
            "Admins open a room, set the reserve price + step size + duration, "
            "invite pre-qualified vendors, and run the session. The room streams "
            "bids in real-time via WebSocket."
        ),
        "prerequisites": ["Approved shortlist of bidders", "Admin login"],
        "actions": [
            {"id": "create-room", "label": "Open a new auction room",
             "when": "Post commercial evaluation, when you want to squeeze the final price.",
             "steps": ["Click **NEW ROOM**.", "Enter notice ref, reserve price, step size, duration.",
                       "Pick invited vendors (multi-select).", "Click **OPEN ROOM**."],
             "expected": "Room appears with status `scheduled` and a shareable joining URL per vendor.",
             "controls": [
                 {"name": "Reserve price", "desc": "Starting cap; bids must be ≤ current best minus step."},
                 {"name": "Step size",     "desc": "Minimum decrement between bids."},
                 {"name": "Duration",      "desc": "Timer with auto-extension when a bid lands in the last 60 sec."},
             ], "errors": [
                 {"code": "HTTP 400", "msg": "Reserve must be > 0",
                  "fix": "Set a positive reserve price."},
             ], "screenshot": "admin-auctions-new.png"},
            {"id": "close-room", "label": "Close an active room",
             "when": "Timer expired or you want to end early.",
             "steps": ["Click **CLOSE ROOM**.", "Confirm — final winner is the lowest bid.",
                       "The room state is frozen; export the transcript from **DOWNLOAD LOG**."],
             "expected": "Status flips to `closed`; audit trail exported as CSV.",
             "controls": [], "errors": [], "screenshot": "admin-auctions-close.png"},
        ],
    },
    "admin-meetings": {
        "surface": "admin", "title": "Meetings",
        "url_path": "/admin?tab=meetings",
        "purpose": (
            "Meetings schedules pre-bid, technical clarification, and commercial "
            "opening calls — auto-creates Zoom join URLs + email invites (via "
            "Resend). Each meeting is bound to a notice_ref so the minutes "
            "become part of the audit trail."
        ),
        "prerequisites": ["Zoom OAuth app + JWT credentials in Secrets", "Admin login"],
        "actions": [
            {"id": "schedule-meeting", "label": "Schedule a meeting",
             "when": "Pre-bid clarification session or bid opening.",
             "steps": ["Click **NEW MEETING**.", "Fill title, notice ref, type, start time, duration.",
                       "Add attendees (email list).", "Click **SCHEDULE**."],
             "expected": "Zoom URL generated; invites go out within 60 sec.",
             "controls": [
                 {"name": "Type", "desc": "pre_bid · technical · commercial · debrief."},
             ], "errors": [
                 {"code": "HTTP 502", "msg": "Zoom API unauthorised",
                  "fix": "Regenerate the Zoom JWT + update Secrets."},
             ], "screenshot": "admin-meetings-new.png"},
            {"id": "attach-minutes", "label": "Attach minutes-of-meeting",
             "when": "Post-meeting, before archival.",
             "steps": ["Open the meeting row.", "Upload the MoM PDF.", "Click **SAVE**."],
             "expected": "MoM link appears; audit trail records upload.",
             "controls": [], "errors": [], "screenshot": "admin-meetings-mom.png"},
        ],
    },
    "admin-l1": {
        "surface": "admin", "title": "L1 Comparison",
        "url_path": "/admin?tab=l1",
        "purpose": (
            "L1 Comparison presents a side-by-side ranked view of all shortlisted "
            "bids for a notice: L1 (lowest), L2, L3 with their commercial + "
            "technical scores and deviations. Master Admins use this before "
            "issuing the award."
        ),
        "prerequisites": ["Commercial envelope opened for the notice"],
        "actions": [
            {"id": "compare-bids", "label": "Compare shortlisted bids",
             "when": "Award decision meeting.",
             "steps": ["Enter notice ref.", "The comparison table renders bidders sorted by commercial ascending.",
                       "Click any row to see the full bid details."],
             "expected": "Table shows: rank, vendor, commercial, technical, weighted, delta vs L1.",
             "controls": [
                 {"name": "Export CSV", "desc": "Download the comparison for the tender file."},
             ], "errors": [], "screenshot": "admin-l1-table.png"},
        ],
    },
    "admin-boq": {
        "surface": "admin", "title": "BOQ & Contracts",
        "url_path": "/admin?tab=boq",
        "purpose": (
            "The BOQ (Bill of Quantities) editor manages line-item pricing "
            "against active contracts. Track quantities, unit rates, variations, "
            "and running totals. Used by the Accounting team for progressive "
            "certification."
        ),
        "prerequisites": ["Active contract (from Awards)", "Accounting or Admin login"],
        "actions": [
            {"id": "add-boq-line", "label": "Add a BOQ line",
             "when": "Introducing a new billable item to the contract.",
             "steps": ["Open the contract.", "Click **ADD LINE**.", "Fill item code, description, unit, rate, quantity.",
                       "Click **SAVE**."],
             "expected": "Line total auto-computes; contract running total updates.",
             "controls": [
                 {"name": "Item code", "desc": "Optional but drives grouping in reports."},
             ], "errors": [
                 {"code": "HTTP 422", "msg": "Quantity must be >= 0",
                  "fix": "Zero is allowed for placeholder lines; negatives are not."},
             ], "screenshot": "admin-boq-add-line.png"},
            {"id": "certify-progress", "label": "Certify a progress claim",
             "when": "Contractor submits a monthly progress claim.",
             "steps": ["Enter claimed % per line.", "Total certified value auto-calculates.",
                       "Click **CERTIFY** to lock the claim."],
             "expected": "Certified snapshot stored; contract accrual updates.",
             "controls": [], "errors": [], "screenshot": "admin-boq-certify.png"},
        ],
    },
    "admin-vintel": {
        "surface": "admin", "title": "Vendor Intel",
        "url_path": "/admin?tab=vintel",
        "purpose": (
            "Vendor Intel provides ratings, watch-list, and blacklist management "
            "across the supplier base. Anonymised entries appear as '—' for "
            "confidentiality. Bug #84: table wraps in `overflow-x-auto` for "
            "mobile viewports."
        ),
        "prerequisites": ["Admin login"],
        "actions": [
            {"id": "rate-vendor", "label": "Rate a vendor",
             "when": "Post-contract review, or after a quality incident.",
             "steps": ["Locate the vendor row.", "Click **MANAGE**.",
                       "Enter score (0–100) and pick a band (A/B/C/D).",
                       "Click **SAVE RATING**."],
             "expected": "Rating saved; vendor sort order reflects new score.",
             "controls": [
                 {"name": "Score",  "desc": "0-100. Feeds award weightings."},
                 {"name": "Band",   "desc": "Grouping label for shortlist filters."},
             ], "errors": [], "screenshot": "admin-vintel-rate.png"},
            {"id": "blacklist", "label": "Blacklist a vendor",
             "when": "Serious governance/quality failure.",
             "steps": ["Open the vendor's manage modal.",
                       "Enter a blacklist reason (required).", "Click **BLACKLIST**."],
             "expected": "Vendor row shows red **BL** flag; blocked from future bidding.",
             "controls": [], "errors": [
                 {"code": "Reason required",
                  "msg": "Blacklist reason must be provided",
                  "fix": "Type a non-empty reason before submitting."},
             ], "screenshot": "admin-vintel-blacklist.png"},
        ],
    },
    "admin-masters": {
        "surface": "admin", "title": "Masters",
        "url_path": "/admin?tab=masters",
        "purpose": (
            "Masters is the reference-data hub: sectors, entity types, KZ "
            "licenses, country meta, currency lists. Changes here cascade "
            "immediately to every registration/vendor/notice form."
        ),
        "prerequisites": ["Master Admin login"],
        "actions": [
            {"id": "add-sector", "label": "Add a new primary sector",
             "when": "Onboarding a new industry category.",
             "steps": ["Go to the Sectors sub-tab.", "Click **ADD SECTOR**.",
                       "Enter code, name (EN/RU/KK).", "Save."],
             "expected": "Sector appears in the dropdowns app-wide.",
             "controls": [], "errors": [
                 {"code": "HTTP 409", "msg": "Sector code already exists",
                  "fix": "Codes must be unique. Use ISO codes when possible."},
             ], "screenshot": "admin-masters-sector.png"},
        ],
    },
    "admin-permissions": {
        "surface": "admin", "title": "Permissions",
        "url_path": "/admin?tab=permissions",
        "purpose": (
            "Permissions manages the role-to-capability matrix and admin "
            "user seats. Roles: admin, master_admin, reviewer, committee_member, "
            "certifier, legal, accounting, escrow_agent. Only Master Admin can "
            "grant new seats."
        ),
        "prerequisites": ["Master Admin login"],
        "actions": [
            {"id": "invite-admin", "label": "Invite a new admin user",
             "when": "Onboarding a new PMC operator.",
             "steps": ["Click **INVITE ADMIN**.",
                       "Enter email + choose role.",
                       "Click **SEND INVITE**."],
             "expected": "Email invite sent via Resend with a magic-link to set password + 2FA.",
             "controls": [], "errors": [
                 {"code": "HTTP 409", "msg": "Admin with this email already exists",
                  "fix": "Edit the existing user's role rather than duplicating."},
             ], "screenshot": "admin-permissions-invite.png"},
        ],
    },
    "admin-packages": {
        "surface": "admin", "title": "Packages",
        "url_path": "/admin?tab=packages",
        "purpose": (
            "Packages tracks the Kazakhstan Integrated Development Programme "
            "work packages — cross-notice roll-up view of budget, timeline, and "
            "contractor. Filter by region, sector, status."
        ),
        "prerequisites": ["Admin login"],
        "actions": [
            {"id": "package-detail", "label": "Open a package detail",
             "when": "Reviewing a package's full lifecycle.",
             "steps": ["Click the package row.", "Right pane shows notices, awards, contractors, budget consumed."],
             "expected": "Detail view opens instantly.",
             "controls": [
                 {"name": "Filters", "desc": "Region · Sector · Status."},
             ], "errors": [], "screenshot": "admin-packages-detail.png"},
        ],
    },
    "admin-audit": {
        "surface": "admin", "title": "Audit",
        "url_path": "/admin?tab=audit",
        "purpose": (
            "Audit is the immutable, tamper-evident trail of every state-"
            "changing action on the platform. Filter by actor email, entity "
            "type, entity ID, event kind, or time window. Export to CSV for "
            "regulator submissions."
        ),
        "prerequisites": ["Admin login"],
        "actions": [
            {"id": "query", "label": "Query the audit log",
             "when": "Investigating a support ticket or preparing an audit response.",
             "steps": ["Set filters (actor, entity, from/to date).",
                       "Click **RUN QUERY**.",
                       "Results paginate at 100 rows."],
             "expected": "Table populates; each row is expandable to show the diff.",
             "controls": [
                 {"name": "Event kind", "desc": "created · updated · deleted · signed · released · dissolved · ..."},
             ], "errors": [], "screenshot": "admin-audit-query.png"},
            {"id": "export-csv", "label": "Export audit log as CSV",
             "when": "Providing evidence to an external regulator.",
             "steps": ["Set filters.", "Click **EXPORT CSV**."],
             "expected": "CSV downloads with every filtered row + full diff.",
             "controls": [], "errors": [], "screenshot": "admin-audit-export.png"},
        ],
    },
    "admin-catalog": {
        "surface": "admin", "title": "Product Catalog",
        "url_path": "/admin?tab=catalog",
        "purpose": (
            "Product Catalog manages the SaaS product line: subscription tiers, "
            "one-off setup fees, add-ons. Every product ties to a Stripe price "
            "ID; checkout links can be generated for direct-to-buyer sales."
        ),
        "prerequisites": ["Stripe test/live keys configured", "Master Admin login"],
        "actions": [
            {"id": "add-product", "label": "Add a new product",
             "when": "Launching a new SaaS tier or add-on.",
             "steps": ["Click **NEW PRODUCT**.", "Fill name, description, price, currency.",
                       "Stripe price is auto-created via the API.", "Click **SAVE**."],
             "expected": "Product visible in the checkout catalog; Stripe price_id captured.",
             "controls": [
                 {"name": "Price",     "desc": "Cents. Auto-multiplied for KZT (100x)."},
                 {"name": "Recurring", "desc": "One-time · monthly · yearly."},
             ], "errors": [
                 {"code": "Stripe 401", "msg": "Invalid API key",
                  "fix": "Update the STRIPE_API_KEY secret and restart the backend."},
             ], "screenshot": "admin-catalog-new.png"},
        ],
    },
    "admin-engagements": {
        "surface": "admin", "title": "Engagements",
        "url_path": "/admin?tab=engagements",
        "purpose": (
            "Engagements is the consulting / advisory quote pipeline. Track "
            "leads, sent quotes, signed engagements, and revenue recognition. "
            "Feeds the CFO dashboard."
        ),
        "prerequisites": ["Sales/Master Admin login"],
        "actions": [
            {"id": "new-quote", "label": "Send a new quote",
             "when": "Prospect responded to an intro call.",
             "steps": ["Click **NEW QUOTE**.", "Fill client, scope, value, delivery date.",
                       "Click **SEND**."],
             "expected": "Quote PDF emailed to the client; row appears with status `sent`.",
             "controls": [], "errors": [
                 {"code": "HTTP 422", "msg": "Value must be > 0", "fix": "Set a positive quote value."},
             ], "screenshot": "admin-engagements-quote.png"},
            {"id": "mark-signed", "label": "Mark quote as signed",
             "when": "Client returns the counter-signed quote.",
             "steps": ["Locate row.", "Click **MARK SIGNED**.", "Upload the signed PDF."],
             "expected": "Status flips to `signed`; revenue schedule created.",
             "controls": [], "errors": [], "screenshot": "admin-engagements-signed.png"},
        ],
    },

    # --------------------------------------------------------------- NON-ADMIN
    "vendor-portal": {
        "surface": "vendor", "title": "Vendor Portal",
        "url_path": "/vendor",
        "purpose": (
            "The Vendor Portal is the bidder-facing surface. After email "
            "verification, vendors browse notices, submit bids (with EMD), "
            "e-sign signatures via DocuSign, and export their data (GDPR "
            "request). All bidder actions are audit-logged."
        ),
        "prerequisites": ["Verified vendor account"],
        "actions": [
            {"id": "submit-bid", "label": "Submit a bid",
             "when": "Notice is open and the vendor is pre-qualified.",
             "steps": ["Log in at `/vendor`.", "Open the notice detail.",
                       "Click **SUBMIT BID**.", "Fill technical + commercial forms.",
                       "Attach documents (technical proposal, priced BOQ, EMD receipt).",
                       "Pay EMD via Stripe checkout (or upload wire receipt).",
                       "Click **SUBMIT**."],
             "expected": "Bid row appears with status `submitted`. Admin is notified.",
             "controls": [
                 {"name": "EMD payment",  "desc": "Stripe or wire. Wire requires reference upload."},
                 {"name": "Documents",    "desc": "PDFs only, ≤ 25 MB each."},
             ], "errors": [
                 {"code": "HTTP 409", "msg": "Bid already submitted for this notice",
                  "fix": "One bid per vendor per notice. Withdraw the current bid first if you need to resubmit."},
             ], "screenshot": "vendor-submit-bid.png"},
            {"id": "gdpr-export", "label": "Request a GDPR data export",
             "when": "Vendor exercises data-portability rights.",
             "steps": ["Click **GDPR** in the sidebar.", "Click **REQUEST EXPORT**."],
             "expected": "Email with a download link arrives within 24 h; ZIP contains all bids + registration + audit."\
             , "controls": [], "errors": [], "screenshot": "vendor-gdpr.png"},
            {"id": "e-signature", "label": "E-sign a contract via DocuSign",
             "when": "Awarded bidder receives the PO envelope.",
             "steps": ["Click the DocuSign link in the email.",
                       "Review the PO PDF.", "Click **SIGN**.",
                       "Return to the portal — signature status refreshes automatically."],
             "expected": "Envelope status flips to `completed`. Signed PDF downloadable from the awards tile.",
             "controls": [], "errors": [], "screenshot": "vendor-esign.png"},
        ],
    },
    "staff-portal": {
        "surface": "staff", "title": "Staff Portal",
        "url_path": "/staff",
        "purpose": (
            "The Staff Portal serves the specialised staff roles: certifier "
            "(site inspections), legal (contract review), accounting (invoice "
            "posting), escrow_agent (dual-signature releases), committee "
            "(evaluation scoring). Each role sees a role-specific dashboard."
        ),
        "prerequisites": ["Staff account with a specialised role"],
        "actions": [
            {"id": "certifier-inspect", "label": "Certifier — record an inspection",
             "when": "Site visit is complete.",
             "steps": ["Log in as certifier at `/staff`.",
                       "Open the assigned inspection card.",
                       "Fill findings (pass/fail per checkpoint).",
                       "Upload photos.", "Click **SUBMIT REPORT**."],
             "expected": "Bid moves from `certifier_review` to `legal_review`.",
             "controls": [
                 {"name": "Checkpoints", "desc": "Predefined per notice type."},
             ], "errors": [], "screenshot": "staff-certifier-inspect.png"},
            {"id": "legal-clear", "label": "Legal — clear a bid",
             "when": "Certifier report is in, contract review complete.",
             "steps": ["Log in as legal.", "Open the bid.",
                       "Tick the mandatory checklist (T&C compliance, sanctions screening).",
                       "Click **CLEAR**."],
             "expected": "Bid moves to `accounting_review`.",
             "controls": [], "errors": [], "screenshot": "staff-legal-clear.png"},
        ],
    },
    "registration-portal": {
        "surface": "registration", "title": "Registration Portal",
        "url_path": "/register",
        "purpose": (
            "The public Registration Portal walks a supplier through the "
            "5-section onboarding form (Section A → E). Drafts auto-save every "
            "10 seconds; a resume token is emailed so applicants can pick up "
            "later. Bug #30 added client-side email + phone regex validators."
        ),
        "prerequisites": ["Public — no login required"],
        "actions": [
            {"id": "start-registration", "label": "Start a new registration",
             "when": "Supplier wants to be listed for tender participation.",
             "steps": ["Open `/register`.", "Enter email + company name.",
                       "Click **START**. A resume token is emailed.",
                       "Fill Section A (company details), B (contacts), C (categories), D (KZ licenses), E (bank + declarations).",
                       "Attach mandatory documents.", "Click **SUBMIT** at the end."],
             "expected": "Submission appears in Admin → Registrations under `submitted` status.",
             "controls": [
                 {"name": "Contact email",  "desc": "Bug #30: inline validation (`name@company.com`)."},
                 {"name": "Contact phone",  "desc": "Bug #30: digits + `+`/spaces/hyphens, 7–20 chars."},
             ], "errors": [
                 {"code": "HTTP 422", "msg": "Enter a valid email like name@company.com",
                  "fix": "Correct the email format before proceeding."},
             ], "screenshot": "registration-start.png"},
            {"id": "resume-draft", "label": "Resume a saved draft",
             "when": "Applicant closed the browser and wants to continue.",
             "steps": ["Click the resume link in the email (or enter the token at `/register/resume`)."],
             "expected": "Draft opens at the last completed section.",
             "controls": [], "errors": [
                 {"code": "HTTP 410", "msg": "Resume token expired",
                  "fix": "Ask Admin to nudge / re-send the resume email from the Registrations panel."},
             ], "screenshot": "registration-resume.png"},
        ],
    },
    "public-board": {
        "surface": "public", "title": "Public Notice Board",
        "url_path": "/",
        "purpose": (
            "The public homepage anonymous browsing of open tender notices, "
            "filtered by type (tender/rfp/rfq) and country. Each notice card "
            "links to a detail page with attachments, Q&A thread, and a "
            "call-to-register CTA."
        ),
        "prerequisites": ["Public — no login required"],
        "actions": [
            {"id": "browse", "label": "Browse open tenders",
             "when": "Any visitor.",
             "steps": ["Open `/`.",
                       "Filter by type / country using the chip toolbar.",
                       "Click a notice card to open the detail page."],
             "expected": "Notices list refreshes instantly; detail page shows title, description, attachments, Q&A.",
             "controls": [
                 {"name": "Type filter",    "desc": "All · Tender · RFP · RFQ."},
                 {"name": "Country filter", "desc": "ISO alpha-2. Global tenders shown regardless."},
             ], "errors": [], "screenshot": "public-board.png"},
            {"id": "post-question", "label": "Ask a public Q&A question",
             "when": "Prospective bidder needs clarification.",
             "steps": ["Open a notice detail.",
                       "Scroll to the **Q&A** section.",
                       "Enter your question + your email.",
                       "Click **ASK**."],
             "expected": "Question appears in a moderation queue; Admin reply becomes public.",
             "controls": [], "errors": [], "screenshot": "public-qa.png"},
        ],
    },
    "committee-magic": {
        "surface": "magic", "title": "Committee Accept Portal",
        "url_path": "/committee-accept/",
        "purpose": (
            "External committee invitees (independent experts, industry "
            "advisers) accept or decline their invitation without a full staff "
            "account. Uses a signed magic-link token; the acceptance is "
            "audit-logged."
        ),
        "prerequisites": ["Magic-link URL from Bidding Ops → Form Committee"],
        "actions": [
            {"id": "accept", "label": "Accept the committee invitation",
             "when": "Invitee opens the magic-link URL.",
             "steps": ["Click the emailed link.",
                       "Review the committee scope (notice ref, chairperson, other members).",
                       "Click **ACCEPT**."],
             "expected": "Row on Admin's committee card flips to `accepted`.",
             "controls": [], "errors": [
                 {"code": "HTTP 410", "msg": "Token expired",
                  "fix": "Admin re-issues the invite from Bidding Ops → committee card → **Resend**."},
             ], "screenshot": "magic-committee-accept.png"},
            {"id": "decline", "label": "Decline the invitation",
             "when": "Invitee has a conflict.",
             "steps": ["Click **DECLINE** and provide a short reason."],
             "expected": "Row flips to `declined`.",
             "controls": [], "errors": [], "screenshot": "magic-committee-decline.png"},
        ],
    },
    "escrow-magic": {
        "surface": "magic", "title": "Escrow Officer Portal",
        "url_path": "/escrow/officer/",
        "purpose": (
            "External escrow trustees (bank officers) sign release actions via "
            "a signed magic-link — no staff account needed. Introduced in Bug "
            "#9c to fix the governance gap where the same email was on both "
            "sides of a joint account."
        ),
        "prerequisites": ["Magic-link URL from `POST /api/v1/escrow/magic-tokens`"],
        "actions": [
            {"id": "trustee-sign", "label": "Trustee signs a release",
             "when": "PMC officer has signed; awaiting trustee.",
             "steps": ["Open the magic-link URL.",
                       "Review the account + pending transaction.",
                       "Click **SIGN · RELEASE TO CONTRACTOR**."],
             "expected": "PMC officer sees both signatures; Release button unlocks.",
             "controls": [], "errors": [
                 {"code": "HTTP 409",
                  "msg": "This joint escrow account has the SAME email on both officers",
                  "fix": "Not applicable via magic-link — Admin must edit the account first (see Escrow module)."},
             ], "screenshot": "magic-escrow-sign.png"},
        ],
    },
}


def merge_into(target: dict) -> None:
    for k, v in EXTRAS.items():
        target[k] = v


if __name__ == "__main__":
    print(f"EXTRAS carries {len(EXTRAS)} authored surfaces")
