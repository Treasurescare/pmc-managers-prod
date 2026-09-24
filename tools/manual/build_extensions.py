"""Manual v46m — long-form appendix chapters injected into build.py.

Kept here so build.py stays readable. Contains chapters 26 – 35:
  26 · Modal walkthroughs (New Notice, EMD Compute, DocuSign, Corrigendum, Save-as-Master, Q&A)
  27 · Regulator-liaison protocol
  28 · ESG questionnaire template
  29 · Per-role runbooks
  30 · Field-by-field forms reference
  31 · Bug tracker snapshot (v46o cutover)
  32 · DPR pipeline internal reference
  33 · Incident-response playbook
  34 · Data-retention & backup policy
  35 · Vendor education curriculum
  36 · Change management & release cadence
"""

MODAL_WALKS = [
    ("New Notice draft modal",
     "Path: Admin → Notices → **New notice**. Opens a fullscreen sheet that composes a publishable notice from a Tender Builder template.",
     [
        "**Notice reference** — auto-generated `PMC-NOT-YYYY-NNNN`. Immutable once saved.",
        "**Tender Builder template** — dropdown of masters + drafts filtered to the picked country & industry.",
        "**Country / Industry / Category** — auto-populated from the template but overridable.",
        "**Awarding authority** — free text; appears on the public notice card.",
        "**Language pack** — English (default) / Russian / Kazakh — controls which localised strings render on the public detail page.",
        "**Estimated tender value** — numeric + currency. Feeds the EMD/Fee compute widget.",
        "**Submission deadline** — datetime picker. Stored UTC; rendered in visitor local timezone.",
        "**Bid validity days** — int; used to compute award-window countdowns.",
        "**EMD amount** — auto-computed from Masters → EMD slabs unless overridden. See chapter 26.2.",
        "**Tender fee amount** — same auto-compute path.",
        "**Attachments** — signed PDF, BOQ CSV, drawings. Multi-upload; each row supports Replace / Remove.",
        "**Publish schedule** — Publish now / Schedule at UTC timestamp. Scheduled notices sit in `is_scheduled=true` until the cron fires.",
        "**Publish button** — flips `is_published=true`, emits Resend digests to subscribed categories, pushes Snapchat + Instagram posts, and CloudFront-caches the public detail JSON.",
     ],
     [
        "Once published, edits create a **corrigendum** — the notice document itself becomes append-only.",
        "If the template is a draft (not master), the New-Notice modal freezes the template at publish time and stores a snapshot so later master edits do not affect published notices.",
        "Attachments are streamed to a private S3 bucket. Public download is via a pre-signed URL that expires 24 h after issue.",
     ]),

    ("EMD Compute modal",
     "Path: New Notice → **EMD Compute** button beside the EMD field, or Admin → Masters → EMD → **Test compute**.",
     [
        "**Country / Industry** — passed in from the notice or picked directly.",
        "**Tender value** — the value the EMD is a percentage of.",
        "**Applied slab preview** — read-only display of the matching slab from Masters → EMD (band, percentage, absolute floor, absolute ceiling).",
        "**Computed EMD** — the platform's calculation; can be overridden with justification.",
        "**Override reason** — required if the numeric value is edited manually. Written to the audit trail.",
        "**Apply button** — writes the value back into the New-Notice EMD field.",
     ],
     [
        "If no slab matches (missing masters), the widget shows a red warning and refuses to Apply. Seed the country's slabs first.",
        "Overrides above ±25 % of the computed value trigger a supervisor review flag on publish.",
     ]),

    ("DocuSign signer routing modal",
     "Path: Admin → DocuSign → **New envelope** → Signer routing tab.",
     [
        "**Template picker** — reusable envelope template (LoA / PO / Contract / NDA / Variation).",
        "**Signer 1** — usually the vendor; role auto-set. Email + name required.",
        "**Signer 2 / 3** — sequential routing (Legal → Finance → Countersign). Reorderable; click ↑↓.",
        "**Reminder cadence** — days until first reminder + repeat interval.",
        "**Expiry** — envelope self-expires after N days; default 30.",
        "**Decline handling** — Auto-invite runner-up / Re-open / Do nothing.",
        "**Preview fields** — read-only merged view showing every template placeholder with the resolved value.",
     ],
     [
        "A missing signer email raises a 422; the modal does not send the envelope until every signer has both name + email.",
        "If the envelope was previously sent and voided, resending creates a new envelope id — the audit trail keeps both.",
     ]),

    ("Corrigendum editor modal",
     "Path: Admin → Corrigenda → **New corrigendum**.",
     [
        "**Notice reference** — dropdown filtered to `is_published=true, is_withdrawn=false`.",
        "**Change type** — Extension / Clarification / Amendment / Withdrawal-of-lot.",
        "**Effective date** — datetime; controls which snapshot of the notice is active.",
        "**Summary** — one-paragraph public-facing summary; appears on the public notice detail immediately.",
        "**Change diff** — field-level diff editor. Green additions, red removals; each field carries a required rationale.",
        "**Attachments** — signed amendment PDF, updated BOQ, revised drawings.",
        "**Publish** — writes an immutable corrigendum row; `notice.corrigenda_count` increments; Resend digest to bidders who opened the notice.",
     ],
     [
        "Corrigenda are append-only. Errors are fixed by issuing a superseding corrigendum, never by editing.",
        "Withdrawal-of-lot triggers automatic partial-EMD refund workflow for any bids scoped to the withdrawn lot.",
     ]),

    ("Save-as-Master modal (Tender Builder)",
     "Path: Tender Builder → any draft → **⋯** → **Save as new master**.",
     [
        "**Master name** — editable; defaults to the draft's work title + date suffix.",
        "**Country** — required; drives where the master appears in the master library.",
        "**Industry / Category / Sub-category** — controls which notices auto-suggest this master.",
        "**Description** — one-paragraph internal summary shown in the master picker.",
        "**Retain attachments** — checkbox; unchecked strips the source draft's attachments so the master remains portable.",
        "**Save** — writes a new `tender_templates` document with `is_master=true` and returns its id.",
     ],
     [
        "The new master is instantly discoverable from every notice draft — no re-seed required.",
        "Editing a master version-bumps every notice using it *only if the notice was created after the edit*. Published notices carry their own snapshot (see chapter 26.1).",
     ]),

    ("Q&A moderation modal",
     "Path: Admin → Notices → [row] → **Q&A** tab → **Moderate**.",
     [
        "**Question queue** — sortable by bidder, submitted-at, status (Pending / Answered / Rejected).",
        "**Original question** — read-only; preserves the bidder's exact wording.",
        "**Public rendering preview** — how the anonymised Q&A appears on the public notice detail.",
        "**Answer editor** — rich text with the same allow-list as tender bodies (<p><br><b><i><ul><ol><li><h3>).",
        "**Answer language pack** — English / Russian / Kazakh, mirroring the notice's language pack.",
        "**Publish** — flips `is_answered=true` and fans out an in-app notification to every bidder who purchased the tender pack.",
        "**Reject** — bidder gets a private notification with reason; question is not exposed publicly.",
     ],
     [
        "Questions from bidders with unpaid tender-fee are rejected by default — sell the pack first.",
        "Answers cannot be edited once published; publish a corrigendum-of-Q&A if a factual correction is required.",
     ]),
]

REGULATOR_PROTOCOL = [
    ("Standing engagements",
     "PMC maintains a documented standing engagement with three regulator categories: (a) national procurement regulator, (b) sector regulator for each vertical it participates in (energy, transport, health, digital), (c) the audit board of the sponsoring GOC. Each engagement has a designated Partner-portal user, a monthly briefing calendar entry, and a co-signed MoU housed under Masters → Documents."),
    ("Data-request handling",
     "Any inbound data request from a regulator is logged into the audits collection with `action=regulator.data_request` and routed to Legal counsel + Partner lead within 4 h. The Partner portal exposes a read-only mirror of the requested entities scoped to the request's date range; export is CSV + JSON with SHA-256 checksum, signed by the CTO's key. No raw PII is shared unless the request cites a named legal instrument. The auditor CSV export flow strips PII by default (see Chapter 3)."),
    ("Notice-of-award publication",
     "Every award (`awards.finalised_at`) triggers a webhook to the regulator sink URL configured in Masters → Integrations. The webhook payload is the redacted award JSON — vendor legal name, PO number, contract value, awarding authority — and is retried 3× at 1/15/60 minute intervals on failure. The audit row includes the response body of every retry."),
    ("Corrigenda notification",
     "High-impact corrigenda (change-type in {Amendment, Withdrawal-of-lot}) also fire the webhook. The Partner-portal user can subscribe to a daily digest of corrigenda across the active portfolio."),
    ("Escalation flow",
     "If a regulator opens a formal enquiry, the operations team follows the ladder in chapter 19 (any staff → Partner lead → CEO → Board within 4 h). Legal counsel opens a dedicated Slack channel + Teams channel; both are exported to the audit vault daily. Every substantive reply is drafted in the Partner portal so the audit trail carries the reply verbatim."),
    ("Annual disclosure",
     "By 31 January each year PMC publishes an aggregate annual disclosure covering: total notices published, total contract value awarded, EMD collected + refunded, dispute rate, average cycle time, vendor NPS, and a category-wise summary. Draft lives under Masters → Documents → Annual disclosure; the CFO signs off before publication."),
    ("Audit-vault contents",
     "The audit vault is a private S3 bucket with Object-Lock in compliance mode. Contents: (a) daily snapshot of the audits collection, (b) daily snapshot of contracts, awards, escrow_transactions, (c) monthly export of stakeholder reports, (d) every DocuSign envelope PDF and completed-certificate. Retention: 10 years default, 15 years for contract vault."),
    ("Public-transparency URL",
     "`https://www.pmcmanagers.com/transparency` (planned) will expose the annual disclosure, aggregate KPIs, and the current corrigenda log so regulators can verify the audit story without opening a data request."),
    ("Right-to-audit clause",
     "Every PMC contract includes a right-to-audit clause granting the regulator 30-day-notice access to the audit-vault contents relating to that contract. The clause references chapter 3 (data protection) and the annual disclosure obligation."),
    ("Suspicious-activity reports (SAR)",
     "The AI anomaly detector's high-confidence flags (bid-clustering, price-dumping, alias-reuse across auctions, EMD-refund pattern anomalies) surface into a dedicated Legal queue. Legal reviews within 24 h; where warranted, a SAR is filed with the regulator via the Partner portal."),
]

ESG_QUESTIONNAIRE = [
    ("Governance",
     [
        "Does the organisation have a written anti-bribery & anti-corruption policy? Attach signed PDF.",
        "How many board seats are held by independent directors? Provide names + tenure.",
        "Frequency of internal audit; date of last audit; auditor firm.",
        "Whistle-blower policy in place? Who is the whistle-blower officer? What channels are available?",
        "Sanction-screening cadence for vendors + counterparties (OFAC / EU / LSEG). Frequency + last screening date.",
     ]),
    ("Environmental",
     [
        "Scope 1 + 2 emissions for the last reporting year (tCO2e). Methodology (GHG Protocol / ISO 14064).",
        "Scope 3 emissions covered: which categories (upstream materials, downstream logistics, business travel, cloud infra)?",
        "Renewable energy share of consumed electricity (%).",
        "Water withdrawal (m³) and share drawn from water-stressed regions.",
        "Waste diverted from landfill (%); hazardous waste manifest.",
        "Environmental incidents: number, severity band, remediation status.",
     ]),
    ("Social — workforce",
     [
        "Total headcount; % women in workforce; % women in management.",
        "Fatality rate (per 200 000 hours worked); LTIR; TRIR.",
        "Average training hours per employee per year.",
        "Employee turnover (voluntary / involuntary %).",
        "Minimum wage compared to statutory minimum in operating geographies.",
     ]),
    ("Social — supply chain & community",
     [
        "Share of tier-1 suppliers audited on labour + environmental criteria.",
        "Number of tier-1 suppliers rated as high-risk after audit; remediation plans in place.",
        "Community investment $ (last reporting year); primary beneficiary categories.",
        "Local-content share of awarded contract value.",
     ]),
    ("Ethics & compliance",
     [
        "Number of anti-bribery investigations opened / concluded in the reporting year.",
        "Whistle-blower reports received / substantiated / actioned.",
        "Regulatory sanctions imposed on the organisation or affiliates in the last 5 years.",
        "Legal disputes above $1M in the last 3 years; status.",
     ]),
    ("Data protection & cybersecurity",
     [
        "Is there a designated Data Protection Officer? Name + reporting line.",
        "Certifications held: ISO 27001, SOC 2 Type II, PCI-DSS, HIPAA, other (attach).",
        "Number of reportable data breaches in the last 3 years; root-cause classifications.",
        "Third-party penetration test cadence; last test firm + date; unresolved criticals.",
        "Backup + disaster-recovery drills cadence; last drill date + RTO / RPO achieved.",
     ]),
    ("Kazakhstan / CIS-specific supplements",
     [
        "Compliance with the Kazakhstan Law on Personal Data (Article 12) — where does personal data reside?",
        "Registration with the Ministry of Digital Development (if applicable) — registration number.",
        "Compliance with the local-content requirement of the Public Procurement Law — measurement methodology.",
        "Sanction screening against RK sanctions list; frequency; last screening date.",
     ]),
    ("Scoring rubric",
     [
        "Each category scored 0–5 (0=absent, 5=best-in-class). Weighted mean × 20 → 0–100.",
        "Bidders with weighted mean ≥ 65 are tagged **Preferred ESG**. Below 40 are tagged **Requires improvement** and given a 90-day plan.",
        "Below 25 blocks award of contracts above $10M — see the escalation matrix.",
     ]),
]

ROLE_RUNBOOKS = [
    ("Admin — daily runbook",
     [
        "08:30 — open Analytics, scan the funnel + KPI deltas vs yesterday.",
        "08:45 — review overnight Resend delivery logs; resend any first-touch failures.",
        "09:00 — clear Registrations queue: approve straightforward, RFI unclear, reject fraudulent.",
        "10:00 — publish scheduled notices (auto, but eyeball the digest emails).",
        "11:00 — Q&A moderation: answer or reject every question > 24 h old.",
        "12:00 — lunch.",
        "14:00 — Committee support: rubric issues, evaluator questions.",
        "15:00 — Award report generation for tenders past commercial-lock.",
        "16:00 — DocuSign chase: nudge every envelope > 5 days without progress.",
        "17:00 — Audit-trail spot check: pick 3 random entities from today, verify audit rows present.",
     ]),
    ("Escrow officer — weekly runbook",
     [
        "Monday — reconcile prior-week EMD receipts against Stripe payouts.",
        "Tuesday — process refunds eligible-since ≥ 7 days.",
        "Wednesday — forfeiture desk: any bidder that missed the mandatory acceptance window.",
        "Thursday — joint-account snapshot audit: pick 5 recent transactions, verify snapshot preserved on the row.",
        "Friday — weekly ledger export to Legal + Accounting; sign-off before COB.",
     ]),
    ("Committee member — per-cycle runbook",
     [
        "T-3 days — COI declaration (fresh, not carried over).",
        "T-2 days — rubric familiarisation; ask clarifications on any criterion you cannot confidently apply.",
        "T-1 day — technical envelope walkthrough with the drafting agent.",
        "T-0 → T+7 days — technical scoring; no commercial visibility yet.",
        "T+7 — commercial envelope unlocks after technical lock.",
        "T+8 → T+10 — commercial scoring.",
        "T+11 — award report; ties broken by chapter 8 rules.",
        "T+12 — sign the committee minutes; upload signed PDF to the notice.",
     ]),
    ("Legal counsel — per-contract runbook",
     [
        "LoA drafted from template; verify vendor legal name matches DocuSign signer 1.",
        "Contract clauses reviewed against redline library (Masters → Documents → Redlines).",
        "Right-to-audit clause present (chapter 27).",
        "Escalation clause present (chapter 19).",
        "Sign envelope in the DocuSign routing you defined; countersign after vendor signs.",
        "File the completed-certificate PDF into the audit vault (chapter 27.audit-vault).",
     ]),
    ("Support — vendor helpdesk runbook",
     [
        "Triage every inbound ticket within 2 h; SLA is 1 business day to first substantive response.",
        "Password reset: verify email ownership via the magic-link flow; never share reset codes over chat.",
        "Licence re-verification: check licence expiry, request updated licence PDF, mark vendor 'under review' pending re-approval.",
        "Bid submission failures: capture the browser Network tab, correlate with backend logs (grep the vendor_ref).",
        "Escalate to on-call engineer if failure is systemic (>3 vendors in 1 h).",
     ]),
]

FORM_FIELDS = [
    ("Public registration wizard — Section A (Identity)",
     [
        ("`company_name`",         "Legal entity name; unique across tenants. Immutable once verified."),
        ("`trade_name`",           "Optional DBA / brand name."),
        ("`registration_number`",  "Country-specific business registration number."),
        ("`legal_entity_type`",    "LLC / JSC / GP / Sole prop / etc."),
        ("`incorporation_date`",   "ISO date."),
        ("`registered_address`",   "Street + city + region + postcode + country."),
        ("`country`",              "ISO code; drives licence + tax field validators."),
     ]),
    ("Public registration wizard — Section B (Financial)",
     [
        ("`bank_name / iban / swift`",   "Payout bank details; validated against ISO 20022."),
        ("`tax_id`",                     "Country-specific validator."),
        ("`vat_number`",                 "EU/EAC/RK format enforced client-side."),
        ("`annual_revenue`",             "Optional; drives category eligibility thresholds."),
        ("`last_three_awards`",          "Text; historical awards demonstrating capacity."),
     ]),
    ("Public registration wizard — Section C (Compliance)",
     [
        ("`licences[]`",  "Uploaded PDF + issue/expiry — see licences deep dive."),
        ("`iso_certs[]`", "Optional ISO 9001 / 14001 / 27001 uploads."),
        ("`insurance`",   "Insurer + policy number + expiry."),
        ("`kyc_officer`", "Named individual responsible for KYC."),
     ]),
    ("Notice draft — critical fields",
     [
        ("`notice_ref`",         "Auto: PMC-NOT-YYYY-NNNN."),
        ("`work_title`",         "Public-facing headline; 8–14 words is optimal."),
        ("`work_description`",   "Rich text; 200–800 words."),
        ("`tender_value`",       "Numeric; currency in `budget_currency`."),
        ("`emd_amount / emd_percentage / emd_type`", "One of: absolute / percentage-of-value."),
        ("`tender_fee_amount`",  "Absolute; feeds the fee ledger."),
        ("`sub_start / sub_end`","UTC ISO; sub_end is the submission deadline."),
        ("`prebid_meeting_at`",  "Optional; opens a Zoom-schedule shortcut."),
        ("`evaluation_method`",  "QCBS / L1 / LCBS / BFS."),
        ("`bid_validity_days`",  "Int; drives the award-window countdown."),
        ("`categories[]`",       "UNSPSC nodes; drives vendor alerts + eligibility."),
        ("`attachments[]`",      "Multi-file; signed PDF, BOQ CSV, drawings."),
     ]),
    ("Rubric editor",
     [
        ("`technical_criteria[]`", "Array of {code, title, weight}. Weights sum to 1.00."),
        ("`commercial_weight`",    "0.0 – 1.0; typically 0.30."),
        ("`minimum_technical`",    "0 – 100; bidders below this are technically rejected."),
        ("`tiebreaker_rules`",     "Priced-lower / earlier-submission / higher-rating (see chapter 8)."),
     ]),
    ("Bid submission (vendor)",
     [
        ("`price_amount`",       "Numeric; currency inherits from notice."),
        ("`price_basis`",        "Fixed / Cost-plus / T&M."),
        ("`delivery_period`",    "Days from LoA."),
        ("`compliance_matrix`",  "Per-clause response; supports YES / NO / DEVIATION with rationale."),
        ("`bid_bond`",           "Optional bank guarantee PDF."),
        ("`bid_documents[]`",    "Multi-file; signed technical PDF, commercial spreadsheet."),
     ]),
]

BUG_TRACKER_STATE = [
    ("Closed in v46m", [
        "#78 · Auction summary button overflow on mobile — flex-col sm:flex-row.",
        "#81 · Vendor-intel columns overflow on mobile — grid responsive.",
        "#82 · Landing pipeline funnel labels wrap — 2/4/8 grid.",
        "#52 · Locked-eval envelope reopened silently — 409 + audit rejection.",
        "#49 · Rubric weights allowed > 1.00 — client + server bounds.",
        "#38 · Stakeholder snapshot 500 on any artefact failure — per-artefact try/except + errors[].",
    ]),
    ("Closed in v46o", [
        "Per-section ✨ AI silently 503'd on production — rewired to _llm_complete with managed AI gateway routing.",
        "Bid workflow narrative silently failed — same key-lookup widened.",
        "Auction anomaly narrative silently failed — same fix.",
        "Bid-pair AI redline silently failed — same fix.",
    ]),
    ("Open — P1", [
        "Registration wizard step-gate: strong on Section A, softer on Sections B/C.",
        "Profile avatar cache invalidation after re-login.",
        "Global email + mobile regex — inconsistent across a few older forms.",
        "TenderBuilder tab switch (Tender/RFP/RFQ) missing refetch.",
        "Escrow — modify email IDs on transaction signer flow.",
    ]),
    ("Open — P2", [
        "i18n Russian / Kazakh backfill across ~1500 UI keys.",
        "Manual v2 modal captures via Playwright (screens exist as narrative only).",
        "Firebase / APNs mobile push.",
        "LSEG / World-Check integration.",
        "PayPal / Kaspi payments alongside Stripe.",
        "Zoom integration for evaluation committees.",
    ]),
]

INCIDENT_RESPONSE = [
    ("Detection", "Alerts flow through CloudWatch → PagerDuty → on-call admin. The audit-log tail on Elastic Beanstalk feeds a 30-min sliding window that raises P1 on >5 auth failures / min or >3 500-class responses / min. The AI anomaly detector opens a P2 for any high-confidence flag; Legal triages daily."),
    ("Triage", "On-call admin acknowledges within 5 min, opens a Slack war-room channel, invites the CTO + Legal + Escrow + Support. Engineer captures the immediate CloudWatch tail, the audit rows for the affected entities, and the browser Network trace if a UI regression."),
    ("Containment", "If credentials or key material may be exposed: rotate the affected key first (the managed AI key rotates via the platform; Stripe via Stripe dashboard; JWT signing key via EB env-property + rolling restart). If a code path is at fault, roll back to the previous EB version via the Application Versions console."),
    ("Communication", "For any incident touching vendor bids or contract data, the CEO + Partner lead are informed within 1 h. Communications drafts customer language; nothing is sent without CTO + Legal sign-off. The audit-vault records the entire war-room transcript."),
    ("Recovery", "Once mitigated, engineer captures the RCA + timeline + fix in `/app/deliverables/incidents/YYYY-MM-DD-<slug>.md`. That file is committed via 'Save to Github' and cross-linked from the audit vault."),
    ("Post-mortem", "Blameless post-mortem within 5 business days. Attendees: engineer, CTO, on-call admin, affected role owner. Output: (a) written RCA, (b) 3 preventive actions with owners + due dates, (c) update to the troubleshooting playbook (chapter 12)."),
    ("Regulator notification", "If personal data is exposed the DPO notifies the RK data authority within 72 h per the Personal Data law. Legal owns the wording; the audit vault preserves the transmitted notice."),
    ("Legal disclosure", "For any incident that may materially affect a live bid — retention breach, evaluation-envelope tamper, escrow ledger corruption — Legal freezes the affected tender until the RCA is signed off."),
]

DATA_RETENTION = [
    ("Tenants + auth realms", "Retained for the lifetime of the tenant + 10 years after termination."),
    ("Notices + tender_templates", "Retained indefinitely — the annual disclosure references them by ref."),
    ("Registrations (rejected)", "Retained 3 years then purged; audit-log row preserved."),
    ("Bids + scores + rubrics", "Retained 15 years — required by the audit-board contract clause."),
    ("Escrow transactions", "Retained 15 years — required by financial regulation."),
    ("Corrigenda", "Retained indefinitely with the parent notice."),
    ("Audits", "Retained 10 years default; 15 years for contract-touching actions."),
    ("Ratings", "Retained indefinitely (vendor-visible)."),
    ("dpr_jobs.result", "Retained 6 hours; failed jobs retained 24 h with error string."),
    ("Reports snapshots", "Retained 5 years then rolling-summarised."),
    ("Backups", "Nightly Mongo dump to S3 (7-day rolling), weekly cold-copy to Glacier (12-month rolling). Weekly restore drill on a scratch cluster."),
    ("DR RTO / RPO", "RTO 4 h · RPO 24 h. Documented in Chapter 33."),
]

VENDOR_CURRICULUM = [
    ("Module 1 — Account & Profile", "Registration wizard, email verification, MFA setup, Section A/B/C completeness, licence upload + expiry alerts."),
    ("Module 2 — Discovering opportunities", "Public notice board, category subscriptions, email digests, RSS + Snapchat + Instagram surfaces, calendar of pre-bid meetings."),
    ("Module 3 — Purchasing tender packs", "Tender-fee payment via Stripe (test + live), download of the packet, corrigenda subscription, Q&A engagement."),
    ("Module 4 — Preparing a bid", "Compliance matrix, price basis, BoQ workbook, bid-bond upload, submission dry-run in the vendor sandbox."),
    ("Module 5 — Submitting a bid", "Envelope sealing, timing, submission proof, common failure modes (invalid PDF, missing licence, expired MFA)."),
    ("Module 6 — Reverse auctions", "Invitations, masked aliases, manual + auto bidding, walk-away floor, anti-sniping, auction-close etiquette."),
    ("Module 7 — After the award", "LoA reception, DocuSign signing, PO number, contract execution, milestones, invoicing, EMD refund workflow, review + trust badge."),
    ("Module 8 — Dispute resolution", "Grounds for dispute, timeline, evidence pack, arbitration clause, escalation to Legal."),
]

CHANGE_MANAGEMENT = [
    ("Weekly release train", "Every Wednesday 15:00 UTC. Frontend + backend deployed together. Preview cycle Tue afternoon; production cycle Wed afternoon."),
    ("Hotfix path", "Any P0 (auth outage, escrow tamper, evaluation-envelope corruption) may bypass the train. Hotfix requires CTO sign-off + 15-minute soak on preview + rollback plan."),
    ("Version scheme", "vXY where X is a marketing generation, Y is the feature letter. 'v46m' = generation 46, feature letter m. Backend + frontend versions may diverge (frontend catches up on the next Wed train)."),
    ("Deprecation policy", "Deprecated endpoints keep serving for 90 days with a `Deprecation` response header + a `Sunset` header. Emails go to every partner using the endpoint at day 0, 30, 60, 89."),
    ("Feature flags", "Non-breaking features behind `feature_flags` collection. Preview flags toggled per-user; production flags toggled per-tenant."),
    ("Rollback criteria", "Automatic rollback if health-check < 90 % for 5 min, or if error rate > 5 % of requests for 2 min. Manual rollback available via EB Application Versions."),
    ("Change-log discipline", "Every merged PR appends to `/app/memory/CHANGELOG.md`; PRD.md summarises weekly. The manual's chapter 14 mirrors the last 12 months."),
]

# ============================================================================
# v46o — deep-appendix chapters 37 – 44 (each targets 4-10 pages of prose)
# ============================================================================

SECURITY_CONTROLS = [
    ("Identity", [
        ("Password policy",       "12+ chars, complexity enforced, bcrypt-hashed with per-user salt, rehash on cost bump."),
        ("Brute-force lockout",   "5 failed attempts in 15 min → 15-min lockout; audit row per attempt."),
        ("Session cookie",        "HttpOnly, SameSite=Lax, Secure in prod; 8-h idle, 30-day absolute."),
        ("MFA",                   "TOTP + optional WebAuthn; enforced for admin + management; opt-in for others."),
        ("Magic link",            "Signed JWT with 15-min TTL; single-use; invalidated on password change."),
    ]),
    ("Transport & network", [
        ("TLS",                    "TLS 1.3 only; HSTS max-age 365 days + preload."),
        ("CDN",                    "CloudFront front; origin only allows CloudFront-signed requests."),
        ("Backend origin",         "EB security group only allows the CloudFront IP list + the office VPN CIDR."),
        ("Rate limits",            "60 req/min per IP on auth, 300 req/min per session elsewhere."),
        ("WAF",                    "AWS WAF managed common rules + custom binary-body blocker (why DPR uses base64 JSON)."),
    ]),
    ("Data protection", [
        ("At-rest encryption",     "S3 SSE-KMS + MongoDB Atlas encryption-at-rest."),
        ("In-flight encryption",   "TLS end-to-end + LlmChat proxy over HTTPS."),
        ("Backup encryption",      "Glacier vault encrypted with a customer-managed KMS key rotated annually."),
        ("Secrets management",     "AWS Secrets Manager for prod; .env files are gitignored and never bundled in EB zips."),
        ("PII redaction",          "Auditor role CSV export strips PII by default; unredacted export requires legal + CTO co-sign."),
    ]),
    ("Application-level", [
        ("CSRF",                   "Double-submit token; every mutating request must carry the X-CSRF-Token header."),
        ("XSS",                    "Rich-text sanitisation via _sanitize_body allow-list; React auto-escapes by default."),
        ("SSRF",                   "Outbound HTTP restricted to a URL allow-list (managed AI gateway, Stripe, DocuSign, Resend)."),
        ("Serialisation",          "PyObjectId annotated type; no raw ObjectId leakage; all API models are Pydantic-typed."),
        ("File uploads",           "Signed URLs to a private bucket, MIME sniff on server, 100 MB DPR cap, 25 MB elsewhere."),
    ]),
    ("Operational", [
        ("Change advisory board",  "Every prod change reviewed by CTO + Legal + on-call admin on the weekly train."),
        ("Access reviews",         "Quarterly review of all admin + staff roles; revoke unused within 90 days."),
        ("Vulnerability scans",    "Weekly Snyk on backend requirements + npm audit on frontend; SLA 30 days for High, 90 days for Medium."),
        ("Penetration test",       "Annual third-party pen-test; unresolved criticals block the next feature release."),
        ("Incident drills",        "Quarterly tabletop; annual full-DR failover to the scratch cluster."),
    ]),
]

TENDER_COMMITTEE_CONSTITUTION = [
    ("Composition",
     "A minimum of five voting members: (a) technical lead from the sponsoring GOC, (b) financial lead from PMC accounting, (c) legal counsel, (d) domain expert (rotating), (e) external observer from the Partner portal. Quorum: four members with at least one from each mandatory role (a, b, c)."),
    ("Term",
     "Two-year rotating term; no member serves more than two consecutive terms. External observers are appointed per-tender."),
    ("Conflict of interest",
     "Every member signs a fresh COI declaration per tender. Any material relationship — equity, past employment, first-degree family — triggers recusal. Recusal is audit-logged and the missing weight redistributes proportionally."),
    ("Voting",
     "Technical scores are simple weighted average; commercial score is L1-driven; final ranking is the QCBS composite. Ties broken by: (1) lower price, (2) earlier submission timestamp, (3) higher aggregate trust rating, (4) coin toss on video call with all members present."),
    ("Minutes",
     "Chair drafts the minutes within 48 h of the meeting. Every member signs digitally via DocuSign; the signed PDF is uploaded to the notice and mirrored to the audit vault."),
    ("Dispute mechanism",
     "A dissenting member may attach a written dissent to the minutes. Dissents that raise substantive process issues freeze the award until Legal signs off."),
    ("Confidentiality",
     "All committee materials are Confidential — Internal Use Only. Unauthorised disclosure triggers immediate revocation + a Legal review. Every download from the committee vault is audit-logged."),
    ("External observer",
     "The observer has voice but no vote. Their role is to attest process fidelity; their sign-off appears on the annual disclosure."),
    ("Meeting cadence",
     "Ordinary: on-demand per tender. Standing: quarterly retrospective on process + outcomes. Extraordinary: any dispute or regulator enquiry."),
    ("Compensation",
     "Members receive a per-tender honorarium disclosed on the annual disclosure. External observers receive a fixed retainer + expenses."),
]

DR_DRILL_SCRIPT = [
    ("T-14 days", "Announce drill window to on-call rota + Support + Partner leads. Freeze non-critical deploys 24 h before the drill."),
    ("T-1 day", "Verify Mongo dump succeeded on the scratch cluster. Verify EB app version is deployable to the DR environment. Verify DocuSign, Stripe, Resend sandbox credentials in Secrets Manager."),
    ("T-0 · 09:00 UTC", "Declare drill start in the war-room channel. Rotate DNS to the DR CloudFront distribution (weight 100 → 0 on prod, 0 → 100 on DR)."),
    ("T-0 · 09:05 UTC", "Restore last night's Mongo dump onto the DR cluster (target RTO 4 h)."),
    ("T-0 · 09:10 UTC", "Deploy the current EB backend version to the DR environment. Point secrets to DR values."),
    ("T-0 · 09:20 UTC", "Smoke test: admin login, list notices, place a mock bid, run an evaluation lock, generate an award report, refund an EMD. All 6 must pass or the drill is aborted and rolled back."),
    ("T-0 · 10:00 UTC", "End drill. Rotate DNS back to prod. Compare timestamps to targets; log actual RTO / RPO. Post-mortem the same afternoon."),
    ("T+1 day", "Publish drill report to Partner portal. If RTO > 4 h or RPO > 24 h, opens a P1 remediation ticket with the CTO as owner."),
]

SAMPLE_NOTICE = [
    ("Header",
     "**Notice ref:** PMC-NOT-2026-0472 · **Awarding authority:** Astana Municipal Water Utility · **Country:** Kazakhstan · **Category:** Water & wastewater — pipeline construction · **Estimated value:** KZT 3,850,000,000 · **EMD:** KZT 96,250,000 (2.5 %) · **Tender fee:** KZT 250,000 · **Submission deadline:** 2026-10-31 15:00 UTC · **Bid validity:** 180 days · **Evaluation:** QCBS 70/30."),
    ("Scope",
     "Design + build + commission of a 47 km ductile-iron potable water pipeline from the Astana North reservoir to the Saryarka distribution station, including 12 pressure-reduction chambers, SCADA integration, and 24-month operations warranty. Full BoQ in the tender packet."),
    ("Eligibility",
     "Bidders must (a) hold a valid Class-A pipeline construction licence issued by the RK Ministry of Construction, (b) demonstrate at least 3 pipeline projects of comparable value in the last 5 years, (c) meet a minimum annual turnover of KZT 6 bn averaged over the last 3 years, (d) not appear on any RK / OFAC / EU / LSEG sanction list, (e) commit to a minimum 60 % local-content share."),
    ("Documents required",
     "Signed cover letter, corporate registration, tax clearance, 3 years audited financials, list of past projects with client references, ISO 9001 + ISO 14001 certificates, health & safety plan, project execution plan, quality plan, environmental & social management plan, bid bond (bank guarantee), price schedule against the BoQ."),
    ("Timeline",
     "Publication → today. Pre-bid meeting → 2026-10-03 10:00 UTC via Zoom. Query cut-off → 2026-10-15. Submission deadline → 2026-10-31 15:00 UTC. Technical envelope opening → 2026-11-03 10:00 UTC. Commercial envelope opening → 2026-11-18 10:00 UTC. Award → target 2026-12-05. Contract signing → 2026-12-20."),
    ("Payment terms",
     "10 % advance against bank guarantee, 80 % against milestone certificates verified by the Engineer, 10 % retention released 12 months after handover subject to defect-liability closure."),
    ("Dispute resolution",
     "Any dispute is escalated through: (1) direct engineer-vendor conference within 7 days, (2) formal notice + 30-day cure period, (3) mediation via the Astana International Arbitration Centre, (4) binding arbitration under the AIAC rules. Governing law: Kazakhstan."),
    ("Corrigendum log (sample)",
     "**C-01** (2026-10-05): pre-bid meeting relocated from in-person to Zoom-only due to venue capacity. **C-02** (2026-10-12): eligibility relaxed — 2 comparable pipeline projects (was 3) sufficient. **C-03** (2026-10-18): submission deadline extended by 3 days in response to bidder queries about the SCADA specification."),
    ("Q&A extract (sample)",
     "Q1: Is the SCADA integration open-standard or vendor-locked? — A1: Open-standard (Modbus TCP + OPC-UA); vendor-locked proposals will be flagged in the compliance matrix. Q2: Is the bid bond negotiable with a corporate guarantee? — A2: No; only a bank guarantee from a Category-A RK bank is acceptable. Q3: Is the local-content share tested at award or at contract-completion? — A3: Both — an at-award commitment and an at-completion verification, with a 5 % contract-value penalty if the completion figure is below the committed figure."),
    ("Attachments (sample)",
     "01_Signed_Notice.pdf · 02_BoQ_v2.xlsx (post C-02) · 03_Drawings_A_C_series.zip · 04_Draft_Contract.docx · 05_Bid_Bond_Template.pdf · 06_Health_Safety_Plan_Template.pdf."),
]

SAMPLE_BID = [
    ("Cover letter",
     "From: NurAzia Infrastructure LLP (NAI). Signed by the Managing Director. Bid reference: PMC-BID-2026-1183. Attaches the certificate of incorporation, tax clearance, and the notarised power of attorney authorising the signatory. Commits to the price and validity period; references PMC-NOT-2026-0472 and all corrigenda published up to submission."),
    ("Technical envelope",
     "180-page technical bid organised into 12 chapters mirroring the notice's compliance matrix: company profile · project experience · project execution plan · quality plan · HSE plan · ESMS · SCADA architecture · pressure-management strategy · maintenance philosophy · training programme · local-content commitment · deviations. Each clause carries a YES / NO / DEVIATION cell against the notice requirement; deviations are rationalised with an impact + mitigation."),
    ("Commercial envelope",
     "Price schedule against the notice's BoQ. Base bid: KZT 3,712,500,000 (below estimate). Escalation formula: quarterly, capped at 8 % annually. Payment currency: KZT for local scope, USD (spot at contract-signing) for imported SCADA hardware. Optional items: 24-month O&M extension at KZT 84 M / year."),
    ("Compliance matrix (excerpt)",
     "**Clause 4.2.1 (Class-A licence)** — YES · attached licence LIC-2019-0142. **Clause 4.2.2 (3 comparable projects)** — YES · attached list with client references. **Clause 5.4 (Modbus TCP + OPC-UA)** — YES · Siemens SIMATIC + Rockwell Logix, both supported. **Clause 6.1 (Advance guarantee)** — DEVIATION · standby letter of credit instead of a bank guarantee; rationale: bank capacity limits; mitigation: SLC issued by Halyk Bank (Category-A)."),
    ("Local-content commitment",
     "At-award commitment: 63 %. Categorisation: 42 % labour (RK residents), 15 % locally-manufactured pipe (Aktau Pipe Mill), 6 % services (RK-registered subcontractors)."),
    ("Bid bond",
     "Bank guarantee KZT 96,250,000 issued by Halyk Bank Kazakhstan, valid 210 days from submission (30 days beyond award timeline). PDF attached with the bank's SWIFT confirmation."),
    ("Signatures",
     "Digitally signed by the Managing Director and countersigned by the Company Secretary. All 12 chapter documents carry the corporate seal + digital signature stamp. The DocuSign envelope reference is preserved in the audit trail."),
    ("Envelope timing",
     "Technical envelope submitted 2026-10-31 12:14:07 UTC (2 h 46 min before deadline). Commercial envelope sealed simultaneously. Audit trail preserves both timestamps + the vendor's IP."),
    ("Post-submission outcome (illustrative)",
     "Technical score: 82.4 / 100 (rank 2). Commercial score: 95.1 / 100 (rank 1 — lowest price). QCBS composite: (0.70 × 82.4) + (0.30 × 95.1) = 86.2 / 100 → **rank 1**. Awarded 2026-12-05. LoA countersigned 2026-12-14. PO issued 2026-12-16. Contract executed 2026-12-20."),
]

DETAILED_API_REFERENCE = [
    ("Auth", [
        ("POST /api/v1/admin/auth/login",         "Body: {email, password}. 200: {id, email, name, role, token}. Sets admin_session cookie."),
        ("POST /api/v1/staff/auth/login",         "Body: {email, password, role, tenant_code?}. 200: {active_role, mfa_required?}. Sets staff_session cookie."),
        ("POST /api/v1/vendor/auth/login",        "Body: {email, password}. 200: {vendor_ref}. Sets vendor_session cookie."),
        ("POST /api/v1/*/auth/logout",            "Clears the realm cookie; audit row `auth.logout`."),
        ("POST /api/v1/*/auth/mfa/verify",        "Body: {code}. Required after login when the user has MFA configured."),
    ]),
    ("Public discovery", [
        ("GET /api/v1/meta/public/stats",         "60-s CloudFront cache. Returns {notices_published, suppliers_approved, packages_total}."),
        ("GET /api/v1/meta/public/notices",       "Paginated: ?page=&limit=&country=&category=&q=. Returns notice cards."),
        ("GET /api/v1/meta/public/notices/{ref}", "Full detail — notice + corrigenda + Q&A."),
        ("GET /api/v1/meta/public/tenders/live",  "Alias of /notices?status=live."),
        ("GET /api/v1/meta/public/tenders/completed", "Alias of /notices?status=completed."),
    ]),
    ("Vendor onboarding", [
        ("POST /api/v1/registrations/draft",      "Body: {email, company_name?, country}. 201: {registration_id, magic_token}."),
        ("PATCH /api/v1/registrations/{id}",      "Body: any subset of Section A/B/C fields. 200: updated draft."),
        ("POST /api/v1/registrations/{id}/submit","Locks the draft, notifies Support, and emails a receipt."),
        ("POST /api/v1/admin/registrations/{id}/approve", "Admin only. Provisions the vendor account + emails credentials."),
    ]),
    ("Tender Builder", [
        ("GET /api/v1/tender-templates",          "?is_master=&country=&industry=&q=. Paginated list."),
        ("POST /api/v1/tender-templates",         "Clone from a master or start from blank."),
        ("GET /api/v1/tender-templates/{id}",     "Full document with sections + attachments."),
        ("PATCH /api/v1/tender-templates/{id}",   "Partial update; every save creates a snapshot."),
        ("POST /api/v1/tender-templates/{id}/save-as-master", "Promote a draft to a reusable master (country required)."),
        ("POST /api/v1/tender-templates/{id}/sections/{code}/ai-draft", "v46o — routes through _llm_complete. Body: {tone, length}."),
        ("POST /api/v1/tender-pro/templates/{id}/ai-fill-all", "Draft every empty section body in one pass."),
    ]),
    ("AI DPR", [
        ("POST /api/v1/tender-pro/dpr/analyze-json",  "Sync path for &lt; 4 MB. Body: {filename, content_b64, template_id?}."),
        ("POST /api/v1/tender-pro/dpr/analyze-async", "v46l async path. Returns {job_id}."),
        ("GET  /api/v1/tender-pro/dpr/jobs/{id}",     "Poll status: {status, progress, phase, result, error}."),
    ]),
    ("Evaluation", [
        ("POST /api/v1/evaluations/rubric",          "Upsert rubric for a notice."),
        ("POST /api/v1/evaluations/lock-envelope",   "v46m — refuses re-lock (409). Body: {notice_ref, kind}."),
        ("GET  /api/v1/evaluations/lock-state/{ref}","v46m — returns seal timestamps + attribution."),
        ("POST /api/v1/evaluations/score",           "Submit a technical or commercial score. Blocked if envelope is sealed."),
        ("GET  /api/v1/evaluations/award-report/{ref}", "L1 comparison + weighted scores."),
    ]),
    ("Escrow, awards, contracts", [
        ("POST /api/v1/escrow/transactions",         "Record an EMD held/refunded/forfeited entry. Requires joint-account snapshot."),
        ("POST /api/v1/awards/loa",                  "Draft + send Letter of Award via DocuSign."),
        ("POST /api/v1/awards/po",                   "Emit the PO number after vendor acceptance."),
        ("POST /api/v1/docusign/envelopes",          "Create an envelope from a template with a signer routing spec."),
        ("GET  /api/v1/docusign/envelopes/{id}",     "Status: sent / delivered / completed / declined."),
    ]),
    ("Auctions", [
        ("POST /api/v1/auctions",                    "Create an auction room for an evaluated notice."),
        ("POST /api/v1/auctions/{ref}/invite",       "Invite a technically-qualified vendor."),
        ("POST /api/v1/auctions/{ref}/bid",          "Place a manual or auto bid. Server-side alias masking."),
        ("GET  /api/v1/auctions/{ref}/spectate",     "Read-only public spectator feed with masked aliases."),
    ]),
    ("Reporting", [
        ("GET  /api/v1/stakeholder-reports/tenders", "Pipeline snapshot per notice."),
        ("GET  /api/v1/stakeholder-reports/awards",  "PO numbers + contract value + winning bidder."),
        ("GET  /api/v1/stakeholder-reports/escrow",  "Aging days per status."),
        ("GET  /api/v1/stakeholder-reports/sla",     "Milestone hit-rate per active contract."),
        ("POST /api/v1/reports/snapshot",            "Persist every artefact to disk; per-file try/except; returns errors[]."),
    ]),
]

ACCEPTANCE_TESTS = [
    ("Public discovery", [
        "Anonymous visitor loads / — KPI counters render with real numbers.",
        "Visitor filters /notices by country=KZ — the count matches the API response.",
        "Visitor opens /tenders/live — every card has a countdown chip.",
        "Visitor opens /about and /vision — pages render without a JS error.",
    ]),
    ("Login gateway", [
        "Visitor loads /login — 5 portal cards visible.",
        "Clicking each portal reveals a credential form with the correct badge + colour.",
        "Wrong password shows the exact backend error in a toast; correct password redirects to the right portal.",
        "Vendor portal accepts vendor credentials; staff portals accept staff credentials; cross-realm is refused.",
    ]),
    ("Tender Builder", [
        "Admin creates a new tender from a master template.",
        "Admin edits a section body; auto-snapshot appears in Version history.",
        "Admin clicks ✨ AI on a section — body populates in &lt; 15 s (v46o fix).",
        "Admin uploads a 20 MB DPR — Background chip appears, progress bar advances, section count &gt; 30 (v46l).",
        "Admin runs Save-as-Master — new master appears in the picker under the picked country (v46f).",
    ]),
    ("Evaluation & awards", [
        "Admin sets rubric; invalid weights disable Save.",
        "Committee submits scores; sealed envelopes reject new scores.",
        "Admin locks technical envelope; button becomes 'Sealed 🔒'; banner shows timestamp + sealer.",
        "Admin generates award report — L1 identified with weighted scores.",
        "Attempt to re-lock returns 409 (v46m).",
    ]),
    ("Escrow", [
        "Admin records an EMD receipt with two signers; joint-account snapshot preserved on the row.",
        "Refund workflow requires two officers; audit trail preserves both.",
        "Aging bucket dashboard rolls up 0-30 / 31-60 / 61-90 / 90+ days.",
    ]),
    ("Auctions", [
        "Admin invites qualified vendors; only technically-qualified are eligible.",
        "Vendor joins auction; alias masked; auto-bid config accepted.",
        "Last-second bid extends the auction by 5 min.",
        "Spectator link exposes only masked aliases.",
    ]),
    ("Compliance", [
        "Audit trail export ships as CSV with SHA-256 checksum.",
        "Auditor role CSV export strips PII.",
        "Regulator webhook fires on award; retries 3× at 1/15/60 min on failure.",
    ]),
]

# ============================================================================
# v46o — extra deep-appendix chapters 44 – 52
# ============================================================================

SAMPLE_CORRIGENDA = [
    ("C-01 · pre-bid meeting relocation",
     "**Published:** 2026-10-05 09:14 UTC · **Author:** Astana Municipal Water Utility ·  **Type:** Clarification · **Effective:** 2026-10-05 immediately. **Body:** The pre-bid meeting scheduled for 2026-10-03 10:00 UTC has been relocated from the Utility headquarters (venue capacity 40) to a Zoom-only session. The Zoom link + passcode have been emailed to every bidder who purchased the tender pack and is also visible on the notice detail page. Attendance is optional but strongly recommended. Minutes will be published within 48 h. **Impact:** none on the submission deadline."),
    ("C-02 · eligibility relaxation",
     "**Published:** 2026-10-12 15:41 UTC · **Type:** Amendment · **Effective:** 2026-10-12 immediately. **Body:** Clause 4.2.2 (three pipeline projects of comparable value in the last 5 years) is relaxed to two pipeline projects; the definition of *comparable value* is unchanged (≥ 70 % of the estimated tender value). **Rationale:** feedback from pre-bid meeting attendees indicated that only three Kazakhstan-registered contractors would qualify under the original clause; opening to two projects broadens the field to eight while preserving the capacity bar. **Impact:** bidders may now resubmit updated eligibility declarations up to 24 h before the submission deadline."),
    ("C-03 · deadline extension",
     "**Published:** 2026-10-18 11:02 UTC · **Type:** Extension · **Effective:** 2026-10-18 immediately. **Body:** The submission deadline is extended by three (3) calendar days from 2026-10-28 15:00 UTC to 2026-10-31 15:00 UTC. **Rationale:** Q&A responses received on 2026-10-15 (Q1, Q2, Q3) materially expanded the SCADA specification; bidders requested additional time for design revisions. **Impact:** technical envelope opening is correspondingly pushed from 2026-10-31 to 2026-11-03 10:00 UTC; commercial envelope opening from 2026-11-15 to 2026-11-18 10:00 UTC. All other timeline items unchanged."),
    ("C-04 · attachment update",
     "**Published:** 2026-10-19 10:00 UTC · **Type:** Amendment · **Effective:** 2026-10-19 immediately. **Body:** Attachment 02_BoQ_v1.xlsx is superseded by 02_BoQ_v2.xlsx. Changes: (a) added six SCADA line items reflecting the C-03 clarification, (b) unified valve specifications on line 47–52, (c) corrected the unit-of-measure on line 89 (previously *ea*, now *m*). Bidders must price against BoQ v2; bids priced against BoQ v1 will be technically rejected."),
    ("Corrigenda discipline notes",
     "**Every corrigendum is append-only** — errors are corrected by a superseding corrigendum, never by editing. The audit trail therefore captures the full narrative of a tender's amendments. Bidders are auto-notified via Resend digest for every published corrigendum on any tender pack they purchased; the notification carries a signed link to the corrigendum PDF."),
]

SAMPLE_DOCUSIGN_WALK = [
    ("Envelope template",
     "Selected: *LoA-Standard-KZT-2026*. Merge fields: {vendor_legal_name, vendor_registration_no, work_title, notice_ref, po_number, contract_value_kzt, effective_date, defect_liability_months, bid_bond_number, bid_bond_expiry}."),
    ("Signer 1 — Vendor (NAI)",
     "Name: Aigerim Bekova · Email: <ceo@nurazia.kz> · Role: Managing Director · Auth: SMS OTP + email-click · Fields: signature, initial-each-page, executed-date."),
    ("Signer 2 — Legal (PMC)",
     "Name: Dilnaz Karimova · Email: <legal@pmcmanagers.com> · Role: Head of Legal · Auth: SSO · Fields: signature, review-stamp."),
    ("Signer 3 — Finance (PMC)",
     "Name: Talgat Serikov · Email: <cfo@pmcmanagers.com> · Role: CFO · Auth: SSO + WebAuthn · Fields: signature, PO stamp."),
    ("Signer 4 — Countersign",
     "Name: Aliya Nurlanova · Email: <ceo@pmcmanagers.com> · Role: CEO · Auth: SSO + WebAuthn · Fields: signature, corporate seal stamp."),
    ("Routing",
     "Sequential. Signer 1 → 2 → 3 → 4. Envelope expires 2026-12-14. First reminder after 3 business days, subsequent every 2. Decline handling: Auto-invite runner-up (per notice policy)."),
    ("Status timeline (sample)",
     "**2026-12-05 14:12 UTC** sent to Signer 1. **2026-12-06 09:41 UTC** viewed. **2026-12-08 11:18 UTC** signed. **2026-12-09 14:02 UTC** Legal signed. **2026-12-10 09:58 UTC** CFO signed. **2026-12-14 16:22 UTC** CEO countersigned. Envelope completed; certificate downloaded to audit vault."),
    ("Post-completion",
     "Completed envelope PDF + Certificate-of-Completion stored under `/audit-vault/contracts/PMC-NOT-2026-0472/`. PO number `PMC-PO-2026-1183` emitted. Contract activation email sent to NAI + internal stakeholders."),
]

STAKEHOLDER_REPORT_SAMPLE = [
    ("Tenders report — September 2026",
     "18 notices published, aggregate value KZT 24.8 bn. Median cycle time (draft→publish) 11 days (target ≤ 14). Bidder attention 71 % (target ≥ 65). Bids per notice median 5.5 (target ≥ 4). Two notices flagged for below-target attention → assigned to category audit."),
    ("Awards report — September 2026",
     "9 awards finalised, aggregate contract value KZT 11.4 bn. Winning bidders: 5 KZ, 3 EAC, 1 international. Local-content committed weighted-average 61 % (target ≥ 55). No award disputes opened."),
    ("Escrow report — September 2026",
     "EMDs held opening balance KZT 1.28 bn (33 notices), receipts KZT 486 M (18 notices), refunds KZT 342 M (14 notices), forfeitures KZT 0 (0 notices), closing balance KZT 1.42 bn (37 notices). Aging: 0-30 days 62 %, 31-60 22 %, 61-90 11 %, 90+ 5 %. Refund SLA 100 %."),
    ("SLA report — September 2026",
     "42 active contracts. Milestones hit-rate 94.3 % (2 breaches under review). Average DocuSign envelope turnaround 6.8 days (target ≤ 10). One contract paused pending regulator enquiry (see chapter 27)."),
    ("Anomaly report — September 2026",
     "3 high-confidence flags: (a) bid-clustering on notice 0468 (three bidders within 0.8 % — under committee review), (b) price-dumping on notice 0455 (one bidder 41 % below peer average — invited for clarification), (c) alias-reuse in auction 0451 (same alias re-appeared 14 min after ejection — investigated, false positive due to shared session token). No SAR filed."),
]

AUDIT_TRAIL_SAMPLE = [
    ("Row 1", "at=2026-09-24T05:41:12Z · actor=6a6edc680e4f4fef11774096 (adminsupport@pmcmanagers.com) · action=notice.publish · entity=notice · ref=PMC-NOT-2026-0472 · payload={published_at:'2026-09-24T05:41:12Z', digest_sent:true}"),
    ("Row 2", "at=2026-09-24T05:41:15Z · actor=system · action=integration.regulator_webhook · entity=notice · ref=PMC-NOT-2026-0472 · payload={url:'https://regulator.example/webhook', status:200, retries:0}"),
    ("Row 3", "at=2026-10-05T09:14:08Z · actor=8x3ee640abcfaa10022eb · action=corrigendum.publish · entity=corrigendum · ref=C-01 · payload={notice_ref:'PMC-NOT-2026-0472', type:'clarification'}"),
    ("Row 4", "at=2026-10-31T12:14:07Z · actor=vendor_ref='PMC-SUP-2024-0083' · action=bid.submit · entity=bid · ref=PMC-BID-2026-1183 · payload={notice_ref:'PMC-NOT-2026-0472', envelopes_sealed:['technical','commercial']}"),
    ("Row 5", "at=2026-11-03T10:02:44Z · actor=adminsupport · action=envelope.lock.technical · entity=notice · ref=PMC-NOT-2026-0472 · payload={sealed_at:'2026-11-03T10:02:44Z'}"),
    ("Row 6", "at=2026-12-05T14:12:08Z · actor=adminsupport · action=award.finalise · entity=award · ref=PMC-NOT-2026-0472 · payload={vendor_ref:'PMC-SUP-2024-0083', contract_value_kzt:3712500000}"),
    ("Row 7", "at=2026-12-14T16:22:41Z · actor=system · action=docusign.envelope_completed · entity=envelope · ref=DS-2026-0972 · payload={po_number:'PMC-PO-2026-1183', certificate_url:'…/certificate.pdf'}"),
    ("CSV export policy", "Auditor-role exports strip PII (email, phone, national id, bank iban) and replace them with per-user pseudonyms. Unredacted exports require Legal + CTO co-sign; the co-sign row itself is written into the audits collection."),
]

MOU_TEMPLATE = [
    ("Parties", "This Memorandum of Understanding (this **MoU**) is entered into on ____ between (i) **PMC Managers Limited** (the *Platform Operator*) and (ii) [Sponsoring Government Owned Corporation / Bank / Regulator] (the *Sponsor*)."),
    ("Purpose", "The Sponsor engages the Platform Operator to operate an end-to-end procurement platform for tenders issued by the Sponsor. The scope includes notice publication, bidder self-registration, bid receipt, EMD custody, evaluation, award, e-signature, contract administration, and immutable audit."),
    ("Term", "This MoU is effective from the Effective Date and continues for an initial term of 24 months, renewable for successive 12-month terms unless either party gives 90 days' written notice of non-renewal."),
    ("Fees", "The Sponsor pays the Platform Operator a monthly platform fee of KZT __ plus a per-notice fee of KZT __ per published notice, invoiced monthly, payable within 30 days of invoice date. Late payment attracts interest at the base rate + 3 % per annum."),
    ("Data ownership", "All data uploaded by the Sponsor or its bidders remains the property of the respective uploader. The Platform Operator holds a limited licence to store and process the data solely for the purposes contemplated by this MoU. On termination the Sponsor may export all data in structured JSON + CSV within 30 days."),
    ("Confidentiality", "Each party treats the other's confidential information with the same care as its own material of equal sensitivity and no less than a reasonable-professional standard. Confidential information may not be shared with third parties except as necessary to perform this MoU."),
    ("Right to audit", "The Sponsor has the right, on 30 days' written notice, to audit the Platform Operator's controls, logs, and data handling as they relate to the Sponsor's tenders. The Platform Operator provides access to the audit vault, immutable audit trail, and the incident-log for the audit period."),
    ("Termination", "Either party may terminate this MoU: (a) for material breach uncured within 30 days of written notice, (b) upon insolvency of the other party, (c) upon the other party's failure to maintain any statutory licence necessary to perform this MoU."),
    ("Governing law", "This MoU is governed by the laws of the Republic of Kazakhstan. Disputes are resolved per chapter 40 of the operator manual (arbitration under the AIAC rules)."),
    ("Signatures", "Signed for and on behalf of the Sponsor by ____ (name, title). Signed for and on behalf of the Platform Operator by ____ (name, title). Date: ____"),
]

RACI_MATRIX = [
    ("Publish a notice",           "Agent: R · Admin: A · Legal: C · Committee: I · Support: I · Escrow: I · Partners: I · Vendors: I"),
    ("Answer a Q&A question",       "Agent: R · Admin: A · Legal: C · Committee: I · Support: R · Escrow: — · Partners: — · Vendors: I"),
    ("Publish a corrigendum",       "Agent: R · Admin: A · Legal: C · Committee: I · Support: I · Escrow: — · Partners: I · Vendors: I"),
    ("Receive EMD",                 "Agent: — · Admin: A · Legal: — · Committee: — · Support: I · Escrow: R · Partners: I · Vendors: I"),
    ("Lock technical envelope",     "Agent: — · Admin: R/A · Legal: I · Committee: I · Support: — · Escrow: — · Partners: I · Vendors: I"),
    ("Score technical",             "Agent: — · Admin: A · Legal: I · Committee: R · Support: — · Escrow: — · Partners: I · Vendors: —"),
    ("Generate award report",       "Agent: — · Admin: R/A · Legal: C · Committee: C · Support: — · Escrow: — · Partners: I · Vendors: I"),
    ("Issue LoA",                   "Agent: — · Admin: R/A · Legal: R · Committee: I · Support: — · Escrow: — · Partners: I · Vendors: I"),
    ("Countersign contract",        "Agent: — · Admin: A · Legal: R · Committee: — · Support: — · Escrow: — · Partners: I · Vendors: I"),
    ("Refund EMD",                  "Agent: — · Admin: A · Legal: I · Committee: — · Support: I · Escrow: R · Partners: I · Vendors: I"),
    ("Forfeit EMD",                 "Agent: — · Admin: A · Legal: R · Committee: — · Support: I · Escrow: R · Partners: I · Vendors: I"),
    ("Deploy release train",        "Agent: — · Admin: A · Legal: I · Committee: — · Support: I · Escrow: — · Partners: I · Vendors: I · Engineering: R"),
    ("Handle incident",             "Agent: — · Admin: R · Legal: R · Committee: I · Support: R · Escrow: R · Partners: I · Vendors: I · Engineering: R"),
    ("Regulator response",          "Agent: — · Admin: A · Legal: R · Committee: I · Support: I · Escrow: I · Partners: R · Vendors: I · Engineering: I"),
]

COST_BENEFIT_WORKSHEET = [
    ("Direct benefit — cycle-time reduction",
     "Baseline cycle time (draft → award) pre-PMC: 92 days industry average. Post-PMC: 43 days observed on the last 20 tenders. Saving: 49 days × KZT 320 000 / day of frozen budget × 45 tenders/year = **KZT 706 M / year**."),
    ("Direct benefit — L1 improvement",
     "Broader bidder attention (71 % vs baseline 42 %) yields ~3.4 % improvement in awarded price. On KZT 24.8 bn/year of awarded value that is **KZT 843 M / year**."),
    ("Direct benefit — audit cost reduction",
     "Immutable audit trail + downloadable evidence bundles reduce external-audit fees by ~40 %. Baseline audit spend KZT 84 M/year → saving **KZT 33.6 M / year**."),
    ("Direct benefit — dispute reduction",
     "Corrigenda discipline + Q&A moderation drop the dispute rate from 6.1 % to 2.4 %. Average dispute cost KZT 12 M. Saving: **KZT 20 M / year** on 45 tenders."),
    ("Cost — platform fees",
     "Monthly platform fee KZT 32 M × 12 = **KZT 384 M / year**. Per-notice fee KZT 640 000 × 45 = KZT 28.8 M / year. Total operating cost **≈ KZT 413 M / year**."),
    ("Cost — internal ops",
     "3 FTE for admin + 2 FTE for escrow + 1 FTE for support. Fully loaded cost **≈ KZT 96 M / year**."),
    ("Net benefit",
     "Benefits KZT 1 603 M − costs KZT 509 M = **net KZT 1 094 M / year** on the current KZ programme. Payback within the first tender cycle."),
    ("Sensitivity",
     "A 20 % drop in L1 improvement erodes benefit by KZT 168 M. A 30 % expansion in tender volume adds KZT 480 M. Break-even at 21 published notices per year."),
]

COMMITTEE_MINUTES_TEMPLATE = [
    ("Header",  "**Meeting:** Tender Committee for PMC-NOT-YYYY-NNNN · **Date/time:** YYYY-MM-DD HH:MM UTC · **Venue:** Zoom (recorded) · **Chair:** [Name] · **Secretary:** [Name]"),
    ("Attendance", "Voting members present: [Names]. Voting members absent: [Names + reason]. Observers present: [Names]. Quorum: [YES / NO]."),
    ("COI declarations", "Each voting member's COI status. Any recusals + reallocation of weight."),
    ("Rubric confirmation", "Rubric reviewed, no changes / changes as follows: [list]. Rubric locked at [timestamp]."),
    ("Technical scoring", "Per-bidder technical score summary. Any deviations from the rubric noted with rationale. Technical envelope locked at [timestamp] by [Name]."),
    ("Commercial opening", "Commercial envelopes opened at [timestamp]. Per-bidder commercial score. Anomalies flagged: [list]."),
    ("QCBS composite + ranking", "Weighted composite scores. Ranking. Tie-breaker rules invoked: [YES / NO]."),
    ("L1 recommendation", "Committee recommends award to [Bidder] at [price]. Rationale."),
    ("Dissents", "Any dissenting opinions attached, with signatures."),
    ("Actions", "Legal: draft LoA within 3 business days. Finance: issue PO within 5 business days. Support: notify runner-up + non-qualifiers by end of week."),
    ("Signatures", "Digital signatures of all voting members via DocuSign envelope [id]."),
]

PROCUREMENT_POLICY_SUMMARY = [
    ("Guiding principles",
     "Openness · non-discrimination · value-for-money · transparency · documented audit trail · proportionality of process to value."),
    ("Above-threshold tenders",
     "Notices ≥ KZT 250 M must be published on the PMC platform + the national gazette. Pre-bid meeting mandatory. Evaluation committee minimum 5 members with an external observer."),
    ("Restricted tenders",
     "Restricted-list tenders (defence, critical infrastructure) require an additional CEO + Board sign-off. Bidder shortlist justified in the tender packet. Public visibility limited to award notice."),
    ("Single-source procurement",
     "Permitted only under Article 39 of the Public Procurement Law. Requires (a) written justification, (b) CFO + Legal sign-off, (c) public disclosure within 15 days of award."),
    ("Framework agreements",
     "Multi-year framework agreements allowed for repeatable services. Call-offs against a framework do not require re-publication but each call-off is audit-logged with the reference framework MoU."),
    ("Anti-bid-rigging",
     "The AI anomaly detector runs on every closed tender. Patterns above the threshold auto-open a Legal review. Confirmed rigging → three-year debarment + regulator SAR."),
    ("Debarment",
     "Debarred vendors are marked in the master with a red badge; the vendor cannot log in for the debarment period. Debarment is public; the annual disclosure lists every debarment."),
    ("Emergency procurement",
     "Emergency purchases (natural disaster, national security) may bypass the standard timeline with CEO + Board sign-off. All emergency procurement is post-published within 30 days with the emergency rationale."),
    ("Complaints & appeals",
     "Bidders may lodge a complaint within 7 days of any decision. Complaints route through Legal; final appeal is the national procurement dispute panel. Timelines and outcomes are audit-logged."),
    ("Annual review",
     "The procurement policy is reviewed annually by the Board + external observer. Amendments require CEO sign-off + Board minute reference."),
]

# ============================================================================
# v46o — final push chapters 53 – 58
# ============================================================================

LOCALISATION_STRINGS = [
    ("Public — hero", [
        ("home.hero_kicker",   "EN: PMC Managers · Sovereign Tender Board · RU: PMC Managers · Суверенная тендерная площадка · KK: PMC Managers · Егемен тендер тақтасы"),
        ("home.hero_headline", "EN: Sovereign procurement for a modern republic · RU: Суверенные закупки для современной республики · KK: Заманауи республика үшін егемен сатып алулар"),
        ("home.hero_lede",     "EN: Publish, evaluate, award and audit — end to end… · RU: Публикация, оценка, награждение и аудит — от начала до конца… · KK: Жариялау, бағалау, марапаттау және аудит — басынан аяғына дейін…"),
        ("home.cta_view_notices", "EN: View open notices · RU: Открытые извещения · KK: Ашық хабарламалар"),
        ("home.cta_register",  "EN: Register as supplier · RU: Регистрация поставщика · KK: Жеткізуші ретінде тіркелу"),
    ]),
    ("Login gateway", [
        ("login.gateway_kicker", "EN: PMC Managers · Sovereign Gateway · RU: PMC Managers · Суверенный шлюз · KK: PMC Managers · Егемен қақпа"),
        ("login.select_portal",  "EN: Select your command portal · RU: Выберите свой командный портал · KK: Басқару порталыңызды таңдаңыз"),
        ("login.portal_admin",   "EN: System Administrator · RU: Системный администратор · KK: Жүйе әкімшісі"),
        ("login.portal_management","EN: PMC Management · RU: PMC Руководство · KK: PMC Басшылық"),
        ("login.portal_partners","EN: Strategic Partners · RU: Стратегические партнёры · KK: Стратегиялық серіктестер"),
        ("login.portal_agents",  "EN: Procurement Agents · RU: Агенты по закупкам · KK: Сатып алу агенттері"),
        ("login.portal_vendors", "EN: Registered Vendors · RU: Зарегистрированные поставщики · KK: Тіркелген жеткізушілер"),
    ]),
    ("Notice detail", [
        ("notice.tender_value","EN: Estimated tender value · RU: Ориентировочная стоимость тендера · KK: Тендердің болжамды құны"),
        ("notice.emd_amount",  "EN: EMD amount · RU: Сумма гарантийного взноса · KK: Кепілдік жарнасы"),
        ("notice.sub_end",     "EN: Submission deadline · RU: Крайний срок подачи · KK: Ұсыну мерзімі"),
        ("notice.eligibility", "EN: Eligibility · RU: Требования к участникам · KK: Қатысушыларға қойылатын талаптар"),
    ]),
    ("Evaluation", [
        ("eval.sealed",        "EN: Sealed · RU: Опечатано · KK: Мөрленген"),
        ("eval.lock_tech",     "EN: Lock technical envelope · RU: Опечатать техническую часть · KK: Техникалық конвертті мөрлеу"),
        ("eval.lock_comm",     "EN: Lock commercial envelope · RU: Опечатать коммерческую часть · KK: Коммерциялық конвертті мөрлеу"),
        ("eval.rubric_save",   "EN: Save rubric · RU: Сохранить критерии · KK: Критерийлерді сақтау"),
    ]),
    ("Vendor tabs", [
        ("vendor.tab_tenders", "EN: Open tenders · RU: Открытые тендеры · KK: Ашық тендерлер"),
        ("vendor.tab_bids",    "EN: My bids · RU: Мои заявки · KK: Менің өтінімдерім"),
        ("vendor.tab_rate",    "EN: Ratings · RU: Оценки · KK: Бағалар"),
        ("vendor.tab_sign",    "EN: Signatures · RU: Подписи · KK: Қолтаңбалар"),
    ]),
]

VENDOR_SANDBOX = [
    ("What it is",       "A parallel PMC environment with dummy tenders, dummy escrow, and dummy DocuSign so a new vendor can practise the full journey — registration, bid pack purchase, bid submission, reverse auction — without touching live data."),
    ("How to enable",    "Support opens Admin → Vendors → row → **Sandbox mode**. The vendor immediately sees a *Sandbox* banner across the vendor portal and every action prefixes its notification subject with *[SANDBOX]*."),
    ("Guardrails",       "Sandbox payments route to the Stripe test mode key; the DocuSign envelopes are dispatched from the demo account; EMDs are recorded to a separate `escrow_transactions_sandbox` collection and never mixed with the live ledger."),
    ("Duration",         "14 days by default; extendable in 7-day chunks. Auto-graduates the vendor when they successfully bid on 3 sandbox tenders."),
    ("Coach mode",       "The sandbox banner includes a coach chat with contextual tips — for example, on the compliance-matrix screen the coach explains what YES/NO/DEVIATION mean and how to phrase deviation rationale."),
    ("Reset",            "Support can Reset the vendor's sandbox state in one click; every dummy bid + EMD entry is purged and the vendor starts fresh."),
]

COMMITTEE_TRAINING = [
    ("Module 1 — Public procurement law refresher", "3-hour class covering the RK Public Procurement Law, GFR 2017 equivalents, and the specific chapters PMC uses as guardrails. Includes a 30-question knowledge check."),
    ("Module 2 — Evaluation rubrics done right",    "Weight design, scale calibration, minimum-technical cutoffs, tie-breaker discipline, and the perils of criteria bloat. Includes 5 sample rubrics to critique."),
    ("Module 3 — Bid comparison",                    "Compliance-matrix reading, deviation classification, interpolation of missing values, and applying the AI redline output as an aid (not a substitute) for committee judgement."),
    ("Module 4 — Anti-bid-rigging heuristics",       "Bid-clustering, price-dumping, alias-reuse, EMD-refund pattern anomalies. When to invite clarification, when to escalate to Legal."),
    ("Module 5 — Committee ethics",                  "COI declarations, recusal, confidentiality, signature discipline, dissent process. Real cases from anonymised PMC minutes."),
    ("Module 6 — Award report & post-mortem",        "L1 selection, sensitivity analysis, dispute-window handling, feedback loop into rubric v2 for future tenders."),
    ("Certification",                                "Passing the knowledge checks in all 6 modules certifies a member. Re-certification annually + on any material policy change."),
]

ETHICS_CODE = [
    ("Integrity",   "Every PMC staff member and committee member exercises independent judgement free of external interference."),
    ("Impartiality","Neither favour nor prejudice colours evaluation. Rubrics are applied uniformly across bidders."),
    ("Confidentiality","Every committee document is Confidential — Internal Use Only unless explicitly cleared for publication."),
    ("Conflict of interest","Any material relationship — equity, past employment, first-degree family, gifts above USD 100 — is disclosed and triggers recusal."),
    ("Gift policy","Gifts above USD 100 / year in aggregate from any single bidder are prohibited. Below-threshold gifts are declared."),
    ("Anti-bribery","Any offer of bribe is reported to Legal + CEO within 24 h. The offering party is banned pending Legal review."),
    ("Whistle-blower protection","Staff reporting misconduct in good faith are protected from retaliation. Reports route to the DPO + external audit committee."),
    ("Speaking on behalf of PMC","Only the CEO, CFO, CTO or a designated spokesperson may speak on behalf of PMC to media, regulators, or the public."),
    ("Use of AI","AI outputs are advisory. Every awarded decision has a human sign-off on the audit trail."),
    ("Enforcement","Violations lead to formal review + possible termination, per the HR policy. The Board is informed of every substantiated violation."),
]

BOARD_REPORTING_PACK = [
    ("Executive summary",   "One page: KPIs vs target, headline wins, any P0 / P1 concerns, next-quarter focus."),
    ("Financial pack",      "Revenue vs plan, cost lines, cash position, aged receivables, next-quarter forecast."),
    ("Programme pack",      "Notices published + awarded (vs plan), contract portfolio, dispute rate, vendor NPS."),
    ("Operations pack",     "SLA hit-rate (refund, LoA turnaround, milestone), incidents, drill outcomes."),
    ("Risk pack",           "Top 10 risks with heat-map, mitigation status, new risks identified this quarter."),
    ("Compliance pack",     "Audit trail summary, regulator interactions, ESG progress, PII incidents."),
    ("People pack",         "Headcount, turnover, DE&I metrics, training completion."),
    ("Product pack",        "Release train history, AI copilot uptake, upcoming features, technical debt burn-down."),
    ("Q&A + resolutions",   "Motions for Board approval; ratifications of prior circulars; standing orders."),
]

IT_OPERATIONS = [
    ("Runbook custody",     "IT operations runbooks live under `/app/deliverables/ops/`. Every playbook has an owner + review date + last-executed timestamp."),
    ("Environment matrix",  "prod (EB + S3 + CloudFront + Mongo Atlas M40), preview (this environment), sandbox (scratch cluster), DR (paired region)."),
    ("Secret rotation",     "Managed AI key auto-rotated by the platform. Stripe, DocuSign, Resend keys rotated annually + on incident. JWT signing key rotated on suspicion of exposure."),
    ("Log retention",       "CloudWatch 90 days hot + 5 years cold. Audit vault 10 years / 15 years as per chapter 34."),
    ("Monitoring",          "CloudWatch metrics + PagerDuty routing. Custom metrics: dpr_job_latency_p95, envelope_lock_rate, audit_row_lag."),
    ("Backup",              "Nightly Mongo dump (7-day rolling S3), weekly Glacier cold-copy (12-month rolling), quarterly restore drill."),
    ("Capacity planning",   "Every doubling of published notices triggers a capacity review — CPU, RAM, LLM quota, S3 spend, Mongo Atlas tier."),
    ("Cost management",     "Monthly cost report to the CTO; anything above 15 % QoQ opens a review with the sponsoring finance lead."),
    ("Vendor management",   "Renewals tracked in Masters → Integrations → Renewals. 90-day advance notice on any AI Gateway / AWS / Mongo Atlas / DocuSign / Stripe / Resend renewal."),
    ("End-of-life policy",  "Any dependency EOL'd by upstream triggers a migration project with a 6-month cushion before the upstream end-date."),
]

SAMPLE_QA_DIGEST = [
    ("Q01 — SCADA standards","The tender specifies Modbus TCP + OPC-UA. Are proprietary Siemens S7 or Allen-Bradley EtherNet/IP protocols acceptable as additional layers? — **A:** Yes, provided the mandatory Modbus TCP + OPC-UA layers are fully implemented and remain the primary telemetry channel. Vendors offering only proprietary stacks will be technically rejected."),
    ("Q02 — Bid bond form","Is a corporate guarantee acceptable in lieu of a bank guarantee? — **A:** No. Only unconditional, first-demand bank guarantees issued by Category-A RK banks are acceptable. See Corrigendum C-02 for the expanded bank list."),
    ("Q03 — Local content","Is local content tested at award only, or also at contract completion? — **A:** Both. A committed percentage at award and a verified percentage at project completion; a 5% contract-value penalty applies if the completion figure is below the committed figure."),
    ("Q04 — Pipeline coating","Is polyethylene coating acceptable, or is only fusion-bonded epoxy? — **A:** Fusion-bonded epoxy (FBE) is mandatory for the trunk main; PE coating is acceptable only for distribution branches ≤ DN 200."),
    ("Q05 — Design responsibility","Is this a design-build contract or execution-only against the Engineer's design? — **A:** Design-build. Bidders must include a design responsibility statement and PI insurance evidence."),
    ("Q06 — Currency","May the imported SCADA hardware be quoted in EUR instead of USD? — **A:** Yes; supply an FX-rate assumption clause and lock at contract signing."),
    ("Q07 — JV",   "Can two contractors bid as a Joint Venture? — **A:** Yes; submit a notarised JV agreement, joint bid bond, and a lead-partner designation. Combined turnover counts toward the eligibility bar."),
    ("Q08 — Subcontracting","What is the maximum subcontracted share? — **A:** 40 % of contract value. Every subcontractor above USD 500 K is pre-approved by the Engineer."),
    ("Q09 — Insurance","Minimum PI + CAR insurance thresholds? — **A:** PI USD 5 M / claim, CAR at contract value + 10 %. Certificates to be endorsed to PMC + Sponsor."),
    ("Q10 — Payment currency","Advance and retention in KZT or USD? — **A:** KZT for local scope; USD for imported hardware pass-through only, evidenced by supplier invoices."),
]

BID_EVAL_MATRIX = [
    ("Bidder A — NAI",       "Tech 82.4 · Comm 95.1 · QCBS 86.2 · Rank **1** · Deviations 3 (minor) · Local content 63 %"),
    ("Bidder B — SarPipe",   "Tech 78.9 · Comm 88.2 · QCBS 81.7 · Rank 2 · Deviations 5 (minor) · Local content 71 %"),
    ("Bidder C — AsiaBuild", "Tech 74.1 · Comm 92.4 · QCBS 79.6 · Rank 3 · Deviations 4 (2 major) · Local content 55 %"),
    ("Bidder D — EuroFlow",  "Tech 88.2 · Comm 71.0 · QCBS 83.0 · Rank 4 (very close 2nd on tech, but priced highest) · Deviations 1 · Local content 22 %"),
    ("Bidder E — KZ-Hydro",  "Tech 61.5 · **below minimum technical 65** → technically rejected · not scored commercially · Deviations 8"),
    ("Notes",                "Committee unanimous on Bidder A. Bidder D flagged as an excellent runner-up should Bidder A decline. Bidder C invited for clarification on the two major deviations."),
]

STANDARD_CLAUSES = [
    ("Payment terms",       "Advance 10 % · Interim 80 % against certified milestones · Retention 10 %, released 12 months after handover subject to defect-liability closure."),
    ("Variation orders",    "Any change of scope > USD 25 K or > 3 % of contract value requires a written variation order signed by the Engineer + Contractor + PMC before execution."),
    ("Liquidated damages",  "0.5 % of contract value per week of delay, capped at 10 % of contract value. LDs are not exclusive; PMC reserves the right to terminate for cause after 12 weeks of accumulated delay."),
    ("Termination for cause","30-day cure notice for material breach; termination after cure fails; PMC may draw the bid bond and appoint a substitute contractor at the defaulting party's risk and cost."),
    ("Termination for convenience","Either party may terminate on 60 days' written notice. Contractor entitled to work-done value + 8 % overhead on unexecuted balance up to 6 % of contract value."),
    ("Force majeure",       "Standard definition + 30-day extension per FM event + right to terminate after 180 days of continuous FM. Force majeure claims must be filed within 14 days of onset."),
    ("Governing law",       "Laws of the Republic of Kazakhstan. Disputes resolved per the arbitration clause (AIAC rules, Astana seat, English language)."),
    ("Warranty",            "24 months defect-liability from taking-over. Any latent defect appearing within 24 months rectified at Contractor's cost within 30 days of notice."),
    ("Indemnity",           "Contractor indemnifies PMC + Sponsor against third-party claims arising from Contractor's negligence, breach or wilful misconduct. Cap: contract value + 10 %."),
    ("Confidentiality",     "Both parties treat all project information as Confidential — Internal Use Only. Publications require prior written consent + fact-check by Legal."),
]

COMMS_TEMPLATES = [
    ("Bidder invitation email","Subject: Invitation to bid — PMC-NOT-YYYY-NNNN · Body: opens with the notice title, ends with the tender-pack purchase link + submission deadline in the bidder's timezone. Includes the RFC 8288 unsubscribe link for the digest."),
    ("Corrigendum notification email","Subject: Corrigendum C-NN — PMC-NOT-YYYY-NNNN · Body: one-paragraph summary + full-diff link + impact statement. Sent within 5 min of publication."),
    ("Award-decline runner-up email","Subject: Invitation to accept award (runner-up) — PMC-NOT-YYYY-NNNN · Body: original L1 declined, runner-up invited to accept within 5 business days; LoA drafted from the same template."),
    ("Refund notice email","Subject: EMD refund initiated — PMC-BID-YYYY-NNNN · Body: refund amount, bank routing, expected credit date, contact for reconciliation."),
    ("Regulator quarterly digest","Subject: PMC quarterly disclosure — Q?-YYYY · Body: KPI table, notable awards, incidents (if any), roadmap outlook. Attached: signed PDF + CSV."),
    ("Vendor NPS survey","Subject: How was your recent bid experience? · Body: 1-question NPS (0-10) + free-text comment. Auto-triggered 14 days after award decision. Aggregated in Analytics."),
    ("Committee meeting invite","Subject: Committee meeting — PMC-NOT-YYYY-NNNN — YYYY-MM-DD · Body: agenda, Zoom link, materials pack link, quorum reminder, COI declaration form."),
    ("Incident customer notice","Subject: Service update — PMC platform · Body: what happened, when, who was affected, what we did, what changes to prevent recurrence. Requires CTO + Legal sign-off before send."),
]

NPS_SURVEY = [
    ("Question 1", "On a scale from 0-10, how likely are you to recommend the PMC platform to a peer procurement organisation?"),
    ("Question 2", "What did you like most about your recent experience?"),
    ("Question 3", "What one thing would you change?"),
    ("Question 4 (conditional, score 0-6)", "What went wrong, and how can we make it right?"),
    ("Question 5 (conditional, score 9-10)", "May we quote your feedback in our annual disclosure? (Y/N)"),
    ("Scoring", "Promoters (9-10) minus Detractors (0-6) as a percentage of respondents. Target NPS ≥ 42. Below 30 opens a vendor-experience review with the CEO."),
    ("Publication", "Aggregate score published quarterly on the Partner portal + summarised in the annual disclosure. Individual scores never linked to a bidder identity."),
]

DEBARMENT_LOG = [
    ("Row schema","{debarment_id, vendor_ref, vendor_legal_name, reason, effective_from, effective_to, decision_body, rationale_pdf_url, appeal_status, publication_url}"),
    ("Sample row 1","DEB-2024-003 · PMC-SUP-2019-4471 · Falsified compliance matrix in PMC-NOT-2024-0219. 3-year debarment 2024-08-14 to 2027-08-13. Decision body: Board of Directors. Appeal: rejected 2024-11-02."),
    ("Sample row 2","DEB-2025-012 · PMC-SUP-2022-0119 · Cartel behaviour flagged by anomaly detector, confirmed by Legal. 5-year debarment 2025-03-01 to 2030-02-28. Decision body: Board. SAR filed with regulator."),
    ("Publication","Debarment log is public at /transparency/debarment. Search + filter by year + reason class. Regulator receives a webhook on every new debarment."),
    ("Appeal process","Vendor may appeal to the Board within 30 days of debarment. Appeal is decided within 60 days. During appeal, the vendor remains debarred but marked *Under appeal* in the log."),
]

TEXT_MESSAGE_LIBRARY = [
    ("Login OTP (SMS)", "PMC verification code: 728341. Valid for 5 minutes. Do not share this code."),
    ("Auction start (SMS)", "PMC · Reverse auction for PMC-AUC-2026-0083 starts in 15 minutes. Join now: [short-link]."),
    ("Envelope lock (in-app)", "The technical envelope for PMC-NOT-2026-0472 has been sealed at 2026-11-03 10:02 UTC by adminsupport@pmcmanagers.com. No further technical scores can be submitted."),
    ("Award decision (in-app)", "Congratulations — you have been awarded PMC-NOT-2026-0472. Please review the LoA and countersign within 5 business days."),
    ("EMD refund (in-app)", "Refund of KZT 96,250,000 for PMC-BID-2026-1183 initiated. Expected credit within 5 business days."),
    ("Password reset (email)", "You requested a password reset. Follow this signed link within 15 minutes: [signed-link]. Ignore if you did not request this."),
]

RELEASE_PLANNING = [
    ("Q1 2027 roadmap",
     "P0: i18n Russian + Kazakh string backfill · P0: Manual v3 with modal captures via Playwright · P1: Firebase / APNs mobile push · P1: LSEG / World-Check integration · P2: Kaspi payments alongside Stripe."),
    ("Q2 2027 roadmap",
     "P0: Zoom integration for evaluation committees · P1: PayPal payments · P1: Public transparency portal · P2: Debarment appeal workflow · P2: Auction spectator SSE feed."),
    ("Q3 2027 roadmap",
     "P0: Multi-tenant billing separation · P1: Bulk vendor import CSV · P2: AI copilot for compliance-matrix review · P2: Contract-milestone auto-nudging."),
    ("Q4 2027 roadmap",
     "P0: Annual disclosure automation · P1: Sponsor-branded white-label UI · P2: Advanced analytics with cohort funnels · P2: Vendor NPS auto-tagging via LLM."),
]

MANUAL_MAINTENANCE = [
    ("Ownership",         "The manual is owned by the CTO. Content editors: Product, Legal, Operations. Review cadence: quarterly + on every material release."),
    ("Refresh cadence",   "Screens re-captured after each visual release (any 'v' version bump that changes UI). Text refreshed after every functional release. Cover date auto-bumps."),
    ("Toolchain",         "`/app/tools/manual/capture.py` (Playwright) + `/app/tools/manual/build.py` (WeasyPrint + python-docx). `build_extensions.py` holds long-form appendix data."),
    ("Regenerating",      "SSH into the preview environment. `python3 /app/tools/manual/capture.py` to refresh screens. `python3 /app/tools/manual/build.py` to rebuild MD + DOCX + PDF."),
    ("Publishing",        "Copy the three artefacts + the zipped bundle from `/app/deliverables/v46_manual/build/` into `/app/frontend/public/downloads/`. They will be served at `https://<host>/downloads/PMC_v46m_Master_Training_Manual.pdf`."),
    ("Versioning",        "Filename carries the release code (e.g. `PMC_v46m_...`). The cover shows the release code + month/year. Old manuals are retained in `/app/deliverables/v46_manual/archive/`."),
    ("Translation",       "Next milestone: full RU + KK translations. See chapter 53 for the key inventory. A translator glossary lives under Masters → Documents → Translator glossary."),
    ("Feedback",          "Every reader can email <manual-feedback@pmcmanagers.com>. Feedback is triaged weekly by the CTO's office and folded into the next quarterly refresh."),
]
