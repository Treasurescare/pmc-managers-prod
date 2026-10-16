# PMC Managers · v52h deployment bundle

Build date: 15 Oct 2026 · supersedes v52f.

## What's in this release

### Backend (`pmc-backend-v52h.zip`)
- **CSRF cookie survives iframe/CHIPS contexts** — all five auth routers (admin, staff, vendor, escrow account, escrow signatory) now set `csrf_token` with `Secure; SameSite=None; Partitioned` via `security.set_csrf_cookie()`. Fixes 403 "CSRF token missing or invalid" when the preview and production app run inside an iframe.
- **Document download gate accepts escrow sessions** — `uploads._require_any_signed_in` now also accepts `escrow_account_token` and `escrow_sig_token`. Previously institution users got 401 viewing their own uploaded KYC files; anonymous access is still blocked.
- **Profile change-request workflow** — new router `escrow_profile_changes` mounted in `server.py`:
  - `POST /api/v1/escrow-accounts/me/change-requests` · `GET …/me/change-requests` · `DELETE …/me/change-requests/{id}`
  - `GET /api/v1/escrow-institutions/{iid}/change-requests` · `POST …/change-requests/{id}/approve|reject`
  - Allowed targets: whitelisted core fields, whole-array replacement for `signatories`/`banking`, whole-dict or `documents.<slot>` for documents.
  - Approvals `$set` the field on the institution and ping the owner via the bell + email.

### Frontend (`pmc-frontend-v52h-prod-build.zip`)
- **Unified login works for escrow institutions** — `SignInE` Escrow Institution tab tries the account-first endpoint first, preserves the 403 unverified message, and falls back to legacy signatory login only on 401/404. CSRF token is cached in `sessionStorage` as a double-safety fallback across all three escrow entry points.
- **Document upload fix** — `uploadsApi.uploadFile(file, { scope })` chains presign + direct and the escrow registration wizard uses it. No more "`uploadsApi.uploadFile is not a function`".
- **File viewing works inside the preview iframe** — `uploadsApi.openFile(key)` fetches the file inside the SPA (same cookie partition), builds a blob URL and opens it. Replaces `<a target="_blank">` which failed under Partitioned (CHIPS) cookies.
- **Full Institution profile tab** — read-only view of every registered field with per-field **Request change** buttons and a pending-requests list; document rows render as `New file: <filename> · <KB> · View`.
- **Admin Escrow Institutions filters** — search by name/trading-name/email/reg-number, From/To created-date pickers, status select, pipeline shows `N of total` while filtering, one-click Reset. Admin detail panel now includes a Change Requests block with current-vs-proposed diff, "View proposed file" for document replacements, and Approve / Reject actions.
- **Sign-out routes to `/login`** — unified sign-in page, matching the rest of the console.

### Behaviour note after deploying
Existing sessions must sign out and sign back in once to receive the new `csrf_token` cookie. Everything else is backward compatible.

## Downloads
- Backend: `/downloads/pmc-backend-v52h.zip`
- Frontend static build: `/downloads/pmc-frontend-v52h-prod-build.zip`

## Deployment checklist

### Backend (AWS Elastic Beanstalk, AL2023 Docker)
1. In EB → your backend environment → **Upload and deploy** → pick `pmc-backend-v52h.zip`.
2. Watch the Events tab until the environment goes **Ok / Green**.
3. Hit `/api/health` to confirm boot.
4. Required env vars (already set, confirm): `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `COOKIE_DOMAIN`, `RESEND_API_KEY`, `EMERGENT_LLM_KEY`.

The ZIP is EB-ready: `Dockerfile` is at root, `.dockerignore` and `.ebextensions/` are included, there is intentionally no `docker-compose.yml`.

### Frontend (S3 + CloudFront)
1. Unzip `pmc-frontend-v52h-prod-build.zip`.
2. `aws s3 sync` the contents into your frontend bucket.
3. `aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"`.

## Smoke tests after deploy (3 minutes)
1. Sign in via `/login` → **Escrow Institution** with a verified account — should land on `/escrow/me` without any 403 or "credentials don't match" error.
2. Open **Institution profile** tab → click **Request change** on any field → submit — toast "Change request submitted — awaiting PMC review" and the pending row renders. **No CSRF 403**.
3. Click **View** on an uploaded document — the file opens in a new tab. **No "Sign in to download tender documents"**.
4. In Admin → **Escrow institutions** → search by email, filter by date, filter by status, click a row, scroll to **Profile change requests** → Approve one — field update propagates to the institution and the owner's bell lights up.
5. Sign out from the escrow dashboard — lands on `/login`.
