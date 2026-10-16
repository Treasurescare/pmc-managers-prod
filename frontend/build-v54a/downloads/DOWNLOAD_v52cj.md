# PMC Managers — Backend v52cj — Security Hardening Pack (12 Oct 2026)

Fixes all 4 findings from the security audit.

## SEC-001 [CRITICAL] — Stripe webhook signature verification REQUIRED
**Files**: `config.py`, `routers/payments.py:329-343`, `routers/billing.py:197-219`

- Added `STRIPE_WEBHOOK_SECRET` config env.
- Both webhook handlers now:
  1. Return **HTTP 503** if the secret is not configured (never trust an unsigned event).
  2. Pass `webhook_secret=` to `StripeCheckout.handle_webhook()` so the pmc_lib verifies the signature via `stripe.Webhook.construct_event`.
- Verified live: `POST /api/webhook/stripe` with a forged body now returns **503** (previously would have marked a bid as `emd_paid`).

**Required env to redeploy**: add `STRIPE_WEBHOOK_SECRET` to Elastic Beanstalk → Configuration → Software → Environment properties. Get the value from Stripe Dashboard → Developers → Webhooks → your endpoint → **Signing secret**.

## SEC-002 [HIGH] — Registration resume token no longer leaked by email
**File**: `routers/registrations.py:255-305` (`create_draft`)

- When an existing draft/submitted/under-review/needs-clarification record is found for the submitted email, the response is now **generic**: `{ok: True, message: "If a draft exists for this email, we've sent a resume link to it."}` — **no token, no id, no resume_url**.
- The resume link is emailed to the record's own address only.
- New drafts (first-time email) still return the token so the client can redirect immediately.
- Verified live: 2nd call with same email returns only `{ok, message}` keys; no `magic_token` key.

## SEC-003 [HIGH] — Mass assignment on public draft PATCH closed
**Files**: `models/registration.py:19-27`, `routers/registrations.py:303-321`

- Pydantic model `RegistrationUpdateIn`: `extra="allow"` → `extra="forbid"`. Unknown keys now return **422**.
- Public PATCH endpoint also strips protected fields (`status`, `vendor_ref`, `tenant_id`, `magic_token`, `created_at`, `submitted_at`, `reviewed_at`, `reviewer_notes`, `reviewed_by`, `approved_at`, `rejected_at`) as defence in depth.
- Verified live: PATCH with `{"evilfield": "x"}` returns 422.

## SEC-004 [HIGH] — Default seed passwords disabled on reachable envs
**File**: `config.py:46-82` (`_seed_password`)

- Fallback literal passwords are now ONLY served when the operator explicitly opts in via `LOCAL_DEV=1`. In every other environment (preview, staging, production) `_require_env` fails hard at boot with a visible error listing all env vars present.
- On the local preview we've added `LOCAL_DEV=1` to `backend/.env` so dev work continues; the boot log clearly flags each account still using a default with a CRITICAL message (6 lines).
- **To rotate on production**:
  1. Do NOT set `LOCAL_DEV` on EB.
  2. Set `OWNER_PASSWORD`, `STAFF_PW_ESCROW`, `STAFF_PW_CERTIFIER`, `STAFF_PW_LEGAL`, `STAFF_PW_ACCOUNTS`, `STAFF_PW_COMMITTEE` to strong unique values.
  3. Set `ADMIN_PASSWORD` if you want to rotate the admin seed (optional — you've already set this on preview).

## Not in this build (operational, not code)
- **Android upload keystore removed from source**: still committed at `frontend/android/app/pmc-upload-key.keystore` in git history. You should rotate the Play Store upload key AND run `git filter-repo --path frontend/android/app/pmc-upload-key.keystore --invert-paths` on the repo. I did not touch git history — that's a destructive one-way operation that needs your explicit go-ahead.

## Deploy
- **Backend only** — frontend unchanged (stay on v52ci).
- Elastic Beanstalk: upload `pmc-backend-v52cj.zip`.
- **New env vars required on EB before deploy**: `STRIPE_WEBHOOK_SECRET` (required), plus the SEC-004 seed passwords listed above.

File: `pmc-backend-v52cj.zip`
