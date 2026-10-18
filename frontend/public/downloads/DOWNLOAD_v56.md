# PMC Managers — Release v56 (18 Jun 2026)

Completes the work-distribution phase started in v55. Four admin features,
all verified in preview (testing_agent iteration_89: Bidding Ops 100%;
iteration_88: Company Master + staff picker + escrow scope all PASS).

## 1. Bidding Ops — Assign specialists
On **Bidding ops** (`/admin/e/bidding`), click a bid row → the right-side
detail panel now has an **Assign specialists** button. It opens a modal with
one dropdown per role (Escrow Agent, Certifier, Legal Counsel, Accounting,
Committee Member). Each dropdown lists active staff who hold that role, tagged
with their country scope (or **Global**). Assigning (or clearing) calls
`POST /api/v1/bids/{id}/assign` and feeds the v55 "assigned-to-me" queue.

## 2. Company Master (full)
**Admin → Masters → Companies** is now a full master:
- Profile: name, code, country → state → city → ZIP, registered address,
  registration/incorporation number, incorporation date, tax ID, active flag.
- Documents: single slot each for **Incorporation Certificate / MOA / AOA**
  with upload / view / download / remove.
- **Licenses**: repeatable list (multiple files), upload / view / download / remove.
- Saving the profile never wipes uploaded documents (managed by dedicated
  endpoints).

New backend endpoints (admin):
- `PATCH /api/v1/masters/companies/{id}` (profile)
- `PUT|DELETE /api/v1/masters/companies/{id}/documents/{slot}` (slots:
  incorporation_certificate, moa, aoa)
- `POST /api/v1/masters/companies/{id}/licenses`, `DELETE …/licenses/{index}`

## 3. Staff company picker
New Staff + inline Edit forms now have a **Company** dropdown (from the
Companies master), persisting `company_id` on the staff record for future
company-aware distribution.

## 4. Escrow institution country scope
**Admin → Escrow Institutions** → select an institution → **Country scope**
editor (comma-separated ISO-2 codes; blank = Global/all). `GET
/api/v1/escrow-institutions?country=XX` returns only global or XX-scoped
institutions. Endpoint: `PATCH /api/v1/escrow-institutions/{iid}/scope`.

## Artifacts
- Backend: `pmc-backend-v56.zip` (no DocuSign key / no .env / no tests)
- Frontend: `pmc-frontend-v56-prod-build.zip`

## Deploy (one upload for all 4 features)
1. Backend ZIP → Elastic Beanstalk, wait until environment is green.
2. Unzip the frontend build contents → S3 bucket root (overwrite).
3. CloudFront invalidation `/*`.
4. Confirm footer shows **Frontend v56 · Backend v56**.

## Verify after deploy
- Set a Malaysia staff member's country scope to `MY` in Masters → Staff;
  confirm their /staff queue no longer shows LATAM (unassigned) bids while a
  blank-scope staff still sees everything.
- Assign a specialist to a bid in Bidding ops; confirm it appears in that
  staff member's queue.
