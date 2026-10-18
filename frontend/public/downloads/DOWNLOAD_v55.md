# PMC Managers — Release v55 (17 Jun 2026)

## Work distribution: staff country-scope + hybrid bid queue

Previously every specialist staff member (escrow agent, certifier, legal,
accounting, committee) saw the GLOBAL list of all bids at their stage — a
Malaysia escrow agent saw LATAM bids and vice-versa. v55 scopes the queue.

### How it works now (hybrid)
When acting as a specialist role, a staff member's /staff queue shows:
1. Bids explicitly **assigned to them** for that role, PLUS
2. **Unassigned** bids whose notice `delivery_country` is within their
   **country scope** (blank scope = all countries / global).
Oversight roles (admin / reviewer / auditor) still see everything.

### What's included
- `country_scope` (list of ISO country codes) on staff records — set it in
  **Admin → Masters → Staff** (New Staff form and inline Edit). Blank = global.
- Backend queue filter on `GET /api/v1/bids` applies the hybrid rule for all
  five specialist roles.
- `POST /api/v1/bids/{id}/assign` (admin/reviewer) to assign/clear a specialist
  staff member on a bid — the API that the Bidding Ops assignment UI will call.
- 2FA on high-risk roles (accounting / escrow_agent / legal_counsel) is OFF for
  testing via `REQUIRE_HIGH_RISK_MFA` (set true before beta).

Verified in preview: scope=[ZZ] unassigned → 0 bids; scope=[] → all; assigned-
to-me (any scope) → shown; assigned-to-someone-else → hidden.

### Still to come (next increments, agreed same phase)
- Bidding Ops **assignment UI** (dropdown of role-holders tagged by country).
- Company Master full fields (country→state→city→zip, incorporation details,
  document upload/view/download) + `company_id` picker on the staff form.
- Escrow-institution country scoping (show all → country-based).

## Artifacts
- Backend: `pmc-backend-v55.zip` (no DocuSign key / no .env)
- Frontend: `pmc-frontend-v55-prod-build.zip`

## Deploy
1. Backend → Elastic Beanstalk (wait green).
2. Frontend → S3, then CloudFront invalidate `/*`.
3. In Admin → Masters → Staff, set each specialist's Country scope (blank = all),
   then sign in as that staff member and confirm the queue is scoped.
