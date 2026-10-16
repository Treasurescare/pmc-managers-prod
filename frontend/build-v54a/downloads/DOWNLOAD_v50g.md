# PMC Managers Limited — Release v50g

## What's new (Bug Tracker v17 — Batch 0 + Batch A)

### Batch 0 — Masters restored + Category master

* **Masters tab is back** at `/admin/e/masters`. New sidebar entry under
  Permissions. Mounts the fully-wired legacy MastersPanel (Staff,
  Companies, Tenants, Approval Matrix, Hierarchy, Rating & Fees,
  Charge Fee, **Categories**, Investor Demo) inside the Option E shell.
* **Procurement Category master** — new backend endpoints:
    * `GET  /api/v1/masters/categories?country=KZ&include_inactive=…`
    * `GET  /api/v1/masters/categories/public?country=…`  (vendor-facing)
    * `POST /api/v1/masters/categories`
    * `PATCH /api/v1/masters/categories/{id}`
    * `DELETE /api/v1/masters/categories/{id}` (soft deactivate)
    * Seeded on backend cold-start from UNSPSC taxonomy (87 nodes) **plus**
      KZ legacy `KZ_CATEGORY_LICENSE_MAP` (18 licence-mapped categories) =
      105 total. Idempotent — safe to redeploy.
    * Each row: code, name (EN/RU/KZ), country_scope, required_licences,
      parent_code, unspsc_code, source, is_active.
* **Create Notice form** — Category field is now a **dropdown** fed from
  the Category master, auto-filtered by Delivery country. No more
  free-text drift; shows `UNSPSC-code · Name` for every option.
* **New Masters → Categories tab** — table UI with search, country filter,
  source filter (manual / UNSPSC / legacy), show-inactive toggle, add new
  category modal, reactivate/deactivate per row.
* **Tooltip readability fix** — the ⓘ InfoDot tooltips were white-on-
  cream and unreadable on the Create Notice form. Changed shadcn
  TooltipContent to dark forest-green background with white text and
  brass border. Readable on every page/theme.

### Batch A — Login / Auth

* **#121 — Forgot-password email delivery** — ALREADY FIXED (02 Oct 2026)
  via Resend DNS (DKIM + SPF CNAMEs in Route 53), new Resend API key,
  suppression list cleared, `EMAIL_FROM_ADDRESS` moved to the verified
  root domain. Live delivery to `adminsupport@pmcmanagers.com` confirmed.
* **#124 — Wrong credentials silent on wrong role** — `/login` now shows
  a clear 8-second toast when sign-in fails, with the role name:
  _"Sign-in failed for the \<Supplier/PMC staff/Administrator\> portal.
  Check your email, password, and that you picked the right role."_
  No more silent failures; backend error logged to console for support.
* **#123 — Translation button shows no options** — DEFERRED (not located
  on `/login` in current build; needs user to tell us which screen).

## Bundles
* **Frontend: `pmc-frontend-v50g-prod-build.zip`**  (deploy to S3+CF)
* **Backend: `pmc-backend-v50g.zip`**  (deploy to Elastic Beanstalk — must
  deploy both so the Category master seeds on cold-start)

## Deploy
Frontend: `aws s3 sync --delete` the unzipped build → CloudFront invalidate `/*`.
Backend: upload the zip in EB console → wait for green → verify
`https://api.pmcmanagers.com/api/v1/masters/categories/public` returns 100+ rows.
