# PMC Managers v2 — Trainee Handbook (Wave F — Sep 2026 update)

## Change log
- **Sep 2026 (v3.1)** — Wave F revision. Added: Permissions Matrix operation, sub-admin (reviewer/support) workflows, Portal Branding, Help Requests, Bug fix highlights (Waves A–G).
- Previous: v3.0 (draft), v2.x (mid-2026), v1.x (initial).

---

## Chapter 1 — Roles & Access Control

PMC v2 has **two overlapping access-control systems**. Understand both.

### 1.1 Role-based (RBAC)
- **admin** — Master Admin. Full access to everything. Only role that can *publish* notices.
- **reviewer** — Sub-admin operational staff. **Can now create draft notices** (Sep 2026). Cannot publish. Sees all admin panels.
- **support** — Read-only helper. Can access Help Requests, cannot edit tenders.
- **committee_member** — Scores technical/commercial envelopes on assigned bids.
- **escrow_agent** — Reviews escrow accounts; can sign as PMC officer only.
- **certifier** — Technical clearance on bids.
- **legal_counsel** — Legal sign-off.
- **accounting** — Records EMD receipts, releases funds.
- **auditor** — Read-only across all tenants.

### 1.2 Permissions Matrix (per-document overrides)
Master admin can override the RBAC defaults per document type. E.g. give `reviewer` publish rights on notices for a specific tenant. Access: **Admin → Masters → Permissions**.

**Effective rule** = RBAC default UNION Permissions Matrix override. If no override is stored, the DEFAULT_MATRIX in `permissions.py` applies.

### 1.3 Hierarchy Level (legacy)
`hierarchy_level` (1..5) is a legacy field from Wave 7. Only used by the old approval-chain module. Prefer Permissions Matrix going forward.

---

## Chapter 2 — Notices workflow

1. Master admin or reviewer clicks **New notice**
2. Fill fields (Title ≥ 3 chars, Description ≥ 10 chars — enforced)
3. **"Publish immediately"** checkbox:
   - Enabled if you are Master Admin → notice appears on public board
   - Disabled if you are reviewer/sub-admin → saves as draft; Master Admin publishes later
4. On success: toast reads `Notice created · PMC-NOT-YYYY-####`; form fully resets.

---

## Chapter 3 — Registrations & Vendor Approval

Flow: Vendor visits `/register` → magic-link email → completes 4 sections → **Submits** → status = `submitted`.

Admin review at **Admin → Registrations**:
- Sort by status tab (submitted, under_review, needs_clarification, approved, rejected, draft)
- Click a row → review sections + uploaded documents → **Approve / Reject / Request clarification** (notes required for reject/clarify)
- Toast reads *"Approval / Rejection / Clarification recorded"* (fixed Sep 2026 — was "clarify recorded")

**Nudge stale drafts** button: emails everyone whose draft is >7 days old + creates in-app notification per email sent (new Sep 2026). Three toast branches:
- No drafts found → info toast
- No stale drafts → warning toast
- N reminded → success toast

---

## Chapter 4 — Bidding Ops & Committee

Committee members MUST declare Conflict-of-Interest (COI) **before** scoring any bid. This is enforced server-side — POST /evaluations/score returns 400 if no COI record exists.

Two-cover enforcement: technical envelope must be locked before commercial is opened.

---

## Chapter 5 — Escrow (Wave G governance)

- **Joint control**: Every escrow account has **two named officers** — PMC officer + Escrow institution officer.
- **Sep 2026 enforcement**: PMC officer and Escrow officer MUST have **different email addresses**. Attempting to reuse the same login is now rejected at account creation.
- Every release requires **both** officers to sign the same intended action (release-to-contractor / release-to-vendor / forfeit). Only after dual signature can the admin fire `/release`.
- External escrow officer receives a magic-link email; no full staff account needed.

---

## Chapter 6 — Reverse Auctions (Wave G governance)

- Draft auctions do **not expose** the public bidder link (Sep 2026 fix). Only after admin clicks **Start** does the vendor URL appear.
- Starting requires ≥2 registered participants. If below threshold, the Start button returns a clear error naming the shortfall.
- Closing rejects auctions that are still in `draft` state.

---

## Chapter 7 — Meetings

- Cancelled meetings are **hidden by default** in the admin list (Sep 2026). Pass `include_cancelled=true` to see them.
- Every invitee receives a magic-link `/meet/{token}` — Jitsi or Zoom depending on provider chosen at creation.

---

## Chapter 8 — Handling errors & session preservation

**Root React ErrorBoundary** (Sep 2026): if any panel crashes, you stay logged in. The screen shows a soft error card with **Reload** / **Try again** buttons. Preserves your session so you never need to re-login.

Common triggers this prevents:
- Bulk Invite CSV with malformed rows
- Generate Award Report timeout
- Any unhandled Promise rejection in an admin panel

---

## Chapter 9 — Help Requests

**Admin → Help Requests**: users file requests via `/help-request` from the login page ("Trouble signing in?"). Every request lists requester, priority, category, assignee, aging. Assign to any admin.

---

## Chapter 10 — Portal Branding

**Admin → Branding**: upload a per-tenant logo → shown in the top bar for that tenant's users. Live preview available.

---

## Chapter 11 — Quick reference: bug fixes shipped

See `PMC_Bug_Tracker_v3.xlsx` (delivered separately) — 62 bugs across 7 waves, current status of each.

---

## Chapter 12 — Governance items pending

- G3 — Consolidate the two access-control systems (RBAC + Level) → this handbook is the first step; consolidation into a single matrix is scheduled next.
- G4 — Stakeholder Reports module description doesn't match implementation. Product decision needed: rename or rebuild.

---

*End of handbook.*
