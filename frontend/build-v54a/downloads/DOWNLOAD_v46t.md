# v46t — Web Push, Escrow signer edit, E.164 phone validation

## What's new

### 1 · Web Push (VAPID) — installed and wired
- **Backend router** `/api/v1/push/*` (`backend/routers/push.py`):
  - `GET  /api/v1/push/config` — public VAPID key + enabled flag (anonymous).
  - `POST /api/v1/push/subscribe` — idempotent, stores endpoint + P-256 + auth in `push_subscriptions`.
  - `POST /api/v1/push/unsubscribe` — marks endpoint inactive.
  - `POST /api/v1/push/test` — admin-only fan-out for smoke tests.
  - `GET  /api/v1/push/subscriptions` — admin-only list (last 500).
- **Service worker** now handles `push` and `notificationclick` events (see `frontend/public/service-worker.js`, cache version bumped to `pmc-shell-v46t`).
- **Frontend hook** `frontend/src/lib/push.js` + button `frontend/src/components/EnablePushButton.jsx`. Wired into TopBar (compact pill on `lg:` and up).
- **Trigger hooks**:
  - `bids.py` — on `status == awarded`, pushes "Contract awarded" to the vendor.
  - `corrigenda.py` — on new corrigendum, pushes "Corrigendum #N · <notice_ref>" to every subscriber.
- **iOS 16.4+**: requires the app be **installed to home screen** — Safari refuses in-tab.

### 2 · Escrow signer edit — new UI
- `frontend/src/apps/admin-console/escrow/EscrowSignerEditor.jsx` renders under the accounts section on the Escrow tab. Admin picks an account + side (PMC vs Escrow institution) + updates name/email/designation. Uses the existing `PATCH /api/v1/escrow/accounts/{id}` endpoint (backend already accepted `pmc_officer` / `escrow_officer` payloads). Every change is audit-logged with the acting admin.

### 3 · E.164 phone validation — tightened
- `FormPrimitives.PhoneInput` now enforces `+?[1-9]\d{6,14}` after stripping spaces/hyphens/brackets. Error copy: "Enter international format 7–15 digits, e.g. +7 701 555 0100."

---

## To activate push in production

Generate a VAPID keypair once and paste the values into environment variables. A helper script is included:

```bash
python3 /app/tools/push/generate_vapid_keys.py
```

The script prints ready-to-paste lines for **`backend/.env`** (three keys) and **`frontend/.env`** (one key — the same public value). Do this **before** deploying so the backend endpoint reports `"enabled": true` and browsers can subscribe. Same keys must be present in both prod-frontend build and prod-backend .env.

Environment variables consumed by the backend router:

| Var | Purpose |
|---|---|
| `VAPID_PRIVATE_KEY` | EC P-256 PKCS8 PEM (single-line, `\n`-escaped) |
| `VAPID_PUBLIC_KEY` | Base64url-encoded uncompressed EC point |
| `VAPID_CLAIM_EMAIL` | JWT `sub` claim, e.g. `mailto:admin@pmcmanagers.com` |

Frontend variable:

| Var | Purpose |
|---|---|
| `REACT_APP_VAPID_PUBLIC_KEY` | *(optional — falls back to `GET /api/v1/push/config`)* |

## Verifying end-to-end

1. Add the keys, redeploy backend + frontend.
2. Open the installed PMC PWA on Android or an iOS-16.4+ home-screen icon.
3. Tap the top-right **Enable alerts** pill.
4. Grant browser permission.
5. From an admin session, hit `POST /api/v1/push/test` with `{"title":"hello","body":"world","url":"/"}`.
6. A notification appears; tapping it opens the app to `/`.

---

## Downloads

- **[pmc-backend-v46t.zip](./pmc-backend-v46t.zip)** — EB Docker archive with push router
- **[pmc-frontend-v46t-prod-build.zip](./pmc-frontend-v46t-prod-build.zip)** — same-origin build with SW handler, install prompt, safe-area fixes, push button
- **[DOWNLOAD_v46t.md](./DOWNLOAD_v46t.md)** — this file
