# PMC Managers v2 — Domain Specification

Extracted from v1 legacy build (`pmc-tender-v1-legacy` on GitHub, tag `v1.0`).
This document is the **source of truth for business rules and data shapes** in the v2 build. It is stack-agnostic — it will migrate unchanged from MongoDB (v2 pilot) to PostgreSQL (Phase 2 AWS).

---

## 1. Roles (v2 scope)

| Role | v2 Phase-1 Scope | Notes |
|---|---|---|
| **Vendor / Supplier** | Registers via portal (App 3). Not bidding in Phase-1 (bidding explicitly out of scope per Build Sheet v2 Part 5). | Public + magic-link resume. |
| **Admin** | Reviews registrations, publishes tender notices (App 4), imports 203 KZ packages (App 2). | Cognito MFA in Phase 2 — JWT for now. |
| **Reviewer** | Reads registration queue, comments, escalates. | Sub-role of admin for now. |
| **Site Lead** | Uses App 1 (mobile evidence capture). | Deferred to Phase 2 (needs S3 Object Lock). |
| **Public** | Views the tender notice board (App 4). No login. | SEO-indexed pages. |

## 2. Pre-Tender Registration — Sections A–E

### Section A — Identity & Basic Information
- `company_name` (required)
- `trade_name`
- `registered_address` (required)
- `mailing_address`
- `country` (required, dropdown of 30 countries; **KZ** default for this programme)
- `country_id_label` (auto-derived from country)
- `registration_number` (required)
- `incorporation_date`
- `tax_id`
- `legal_entity_type` (required — LLC / JSC / Sole Prop / Partnership / Branch / Other)
- `website`
- `employees_count`

### Section B — Contact & Signatory
- Contact: `contact_name` · `contact_title` · `contact_office_phone` · `contact_mobile` · `contact_email`
- Signatory: `signatory_name` · `signatory_title` · `signatory_contact`

### Section C — Banking & Financial
- `bank_name` · `bank_branch` · `bank_account_number` · `bank_swift` · `bank_address`
- Turnover (3 years): `turnover_year1` · `turnover_year2` · `turnover_year3` · `turnover_currency` (USD default)

### Section D — Business Profile & Capability
- `primary_sector` (required, from taxonomy)
- `business_description` (required, long text)
- `operating_regions[]` (multi-select)
- `business_categories[]` (multi-select, from taxonomy — see §4)
- `previous_projects[]` — [{name, client, value, year, description}]
- `references[]` — [{name, organisation, role, email, phone}]
- `iso_certifications` · `licenses_permits` · `insurance_details` · `litigation_history`
- **`kz_licenses[]`** — multi-select from KZ license list (§3). Used to gate access to KZ tenders requiring specific licenses.

### Section E — Documents, Declarations & Signature
- `documents[]` — [{name, type, url, uploaded_at}]. Types: certificate of incorporation, tax certificate, ISO cert, license, insurance, bank letter, other.
- **6 Declarations** (all boolean, all required = true to submit):
  1. `decl_conflict_of_interest` — no conflict with PMC/Emerald/Big B
  2. `decl_integrity` — no active blacklisting/sanctions
  3. `decl_accuracy` — all information accurate
  4. `decl_data_consent` — GDPR-style consent
  5. `decl_fee` — understands registration fee is non-refundable (deferred in Phase-1 — fee flow "pilot mode")
  6. `decl_notification` — accepts email notifications
- eSignature: `signature_name` · `signature_title` · `signature_date`

### Status lifecycle
`draft` → `submitted` → `under_review` → { `approved` | `rejected` | `needs_clarification` } → (if `needs_clarification`) back to `submitted`
On `approved`: system assigns `vendor_ref = PMC-SUP-000001` sequentially (per Build Sheet Part 6, App 3 admin side).

## 3. KZ Licenses (gating list)

Held under `kz_licenses[]` on the vendor profile. Required for certain tender categories (§4).

1. Construction (1st category)
2. Electrical installation
3. Mechanical works
4. Plumbing & firefighting
5. Medical gas installation
6. HSE compliance

## 4. KZ Category → Required License Mapping

When a tender notice is created with `delivery_country = KZ`, these categories auto-require the mapped licenses:

| Category | Required Licenses |
|---|---|
| Medical gas pipeline systems | Medical gas installation |
| OT equipment & laminar flow systems | Medical gas installation |
| Modular operation theatres (OTs) | Medical gas installation · Mechanical works |
| External power supply grid connection | Electrical installation |
| Substation works (HT/LT) | Electrical installation |
| Transformers procurement & installation | Electrical installation |
| Elevators & escalators | Mechanical works · Electrical installation |
| Elevators for hostel blocks | Mechanical works · Electrical installation |
| Elevator & escalator AMC | Mechanical works · Electrical installation |
| Fire alarm & safety systems | Electrical installation · HSE compliance |
| External firefighting network (hydrants) | Plumbing & firefighting · HSE compliance |
| Fire system AMC | HSE compliance |
| Water treatment plant (WTP) | Plumbing & firefighting |
| Sewage treatment plant (STP) | Plumbing & firefighting |
| Hostel bathrooms & plumbing | Plumbing & firefighting |
| Hospital civil & superstructure works | Construction (1st category) · HSE compliance |
| Main academic building civil works | Construction (1st category) |
| Hotel superstructure works | Construction (1st category) |

## 5. Tender Notice (public — App 4)

The notice board is public. Notices are **read-only** — no bidding.

- `notice_ref` (unique, e.g., `PMC-NOT-2026-0042`)
- `title` (required)
- `description` (required, markdown-lite)
- `document_type` — `tender` | `rfp` | `rfq` (Phase-1 shows as read-only informational)
- `category` (from taxonomy)
- `delivery_country` (default KZ)
- `submission_deadline` (ISO datetime)
- `pre_bid_meeting_date`
- `budget_currency` · `budget_amount` (optional, may be redacted)
- `required_licenses[]` (auto-populated for KZ)
- `attachments[]` — SBD templates, drawings, BoQs (via presign upload)
- `contact_email` · `contact_name`
- `is_published` (bool; only true notices appear on the public board)
- `published_at` · `created_by` · `tenant_id`

## 6. Package (App 2 — Package Tracker)

The 203 KZ work packages (across health, education, hospitality verticals). Loaded via CSV import.

- `package_ref` (unique)
- `title` · `category` · `phase`
- `value` · `currency`
- `float_target_date` (target tender-publication date)
- `status` — `backlog` | `scoping` | `sbd_draft` | `ready` | `published` | `cancelled`
- `owner_user_id` (admin/site_lead)
- `attached_documents[]`
- `tenant_id`

## 7. Milestone (App 1 — deferred to Phase 2)

Data shape defined here so App 1's offline SQLite schema can be prepped now:

- `milestone_id` · `contract_id` · `vendor_id`
- `scheduled_date` · `actual_date`
- `defects_count` · `defect_severity` (minor/major/critical) · `rework_required` · `rework_days_lost`
- `variation_claims_count` · `variation_claims_value` · `variation_outcome` (none/pending/approved/rejected)
- `safety_incidents_count` · `safety_incident_category` · `payment_dispute` · `payment_dispute_note`
- `witness_name` · `witness_role` · `witness_signature_key` (S3 key when Phase 2)
- `evidence_keys[]` (S3 keys, WORM under Object Lock — Phase 2)
- `device_timestamp` (stored verbatim, never normalised)
- `gps_latitude` · `gps_longitude` · `device_id`
- `client_record_uuid` (device-generated idempotency key)
- `server_timestamp` (server-set)

## 8. Tenant Model

**Every** document/record carries `tenant_id`. Phase-1 uses a **single default tenant** (`PMC-KZ-01`) — but structurally the platform is multi-tenant from day one.

- Tenant is inferred from the authenticated user's session — never sent from the client.
- Public endpoints (App 4 notice list) run **without a tenant context** and filter explicitly on `is_published = true`.
- Phase 2 migration to PostgreSQL will enforce this via RLS + `force row level security`.

## 9. Audit Trail

Every state change (registration submit/approve/reject, notice publish/unpublish, package status change) writes an `audit_event`:
- `seq` (monotonic integer)
- `previous_hash` (SHA-256 of previous event)
- `current_hash` (SHA-256 of this event's payload + previous_hash)
- `actor_user_id` · `event_type` · `target_type` · `target_id` · `payload` · `at`

Same design as v1. In Phase 2 the audit_event table gets append-only triggers + evidence uploads to Object Lock.

## 10. Internationalisation (i18n)

- **English** — primary
- **Russian** — full parity
- **Kazakh (KK)** — required for App 3 (Registration Portal) per Build Sheet
- All strings under `frontend/src/i18n/{en,ru,kk}.json`
- User preference persisted in `localStorage.pmc_lang`
- Public notice board (App 4) — EN + RU

## 11. Out of Scope (v2 Phase-1)

Per Build Sheet v2 Part 5 "**never implement**":
- Bid submission / bid opening
- Evaluation scoring
- Contract award workflows
- Payment processing (Stripe fee flow is "pilot mode" only — no real money)
- Encryption / key management (deferred to AWS KMS in Phase 2)
- S3 Object Lock (deferred to Phase 2)
- AWS Cognito (using local JWT for admin login until Phase 2)
- Multi-tenant RLS enforcement (structural tenant_id only)

## 12. Categories Taxonomy (excerpt — 200+ full list migrates as constants file)

Health · Hospital civil · Hostel · Hotel · Academic building · Utilities · Elevators · Fire safety · Medical gas · WTP · STP · IT & networking · Furniture & fit-out · Signage · Landscaping · Security systems · HVAC · Solar · UPS · Diesel gensets · Kitchen equipment · Laundry · Waste management · CSSD · Modular OTs · ICU beds · Ward furniture · Radiology · Lab equipment · Oxygen plants · Dialysis units · CCTV · PA systems · BMS · Signage · Interpretation booths · Auditorium AV · Library systems · LMS · Student housing FF&E · Cafeteria · Sports facilities · Landscaping · Boundary walls · External roads · Storm drainage · … (full list retained from v1 constants).
