# PMC Managers — Frontend Production Build v51aq

**Release:** v51aq
**Build date:** 2026-10-07
**Bundle:** `pmc-frontend-v51aq-prod-build.zip`
**Contents:** React static build (`index.html` + `static/` assets), `downloads/` folder excluded to keep the bundle lean.

## What's new in v51aq

- **Escrow duplicate guard + cancel**: one bid can hold only ONE open escrow
  transaction (`409` on duplicates). Admin cancel endpoint +
  "Cancel row" button in the Escrow / EMD panel.
- **Unresolved-duplicates banner**: `GET /api/v1/escrow/transactions/duplicates`
  feeds a red banner listing any bid with >1 open row, click-to-filter.
- **Officer-email guard on PATCH**: `PATCH /api/v1/escrow/accounts/{id}`
  now refuses PMC + Escrow officer email collisions (matches CREATE rule).
- **Release audit CSV export**: `GET /api/v1/escrow/exports/releases.csv?year=`
  with an "Export releases · CSV" button in the ledger toolbar.
- **Transaction search bar**: fuzzy filter over bid ref / notice / vendor /
  amount / currency / status above the EMD ledger.
- **Escrow Institution portal fully integrated** (v51al–v51an):
  registration flow with KYC document uploads, admin review queue at
  `/admin/e/escrow-institutions`, signatory password login + reset
  (`/escrow/login`), dashboard with pending-signature grid and sign-off,
  notice ↔ escrow account routing picker, approval magic-link emails,
  cron expiry watchdog (`POST /api/v1/cron/escrow-expiry-watchdog`).
- **Orphan-bid hardening** (v51al): `POST /api/v1/bids` rejects
  price ≤ 0, empty document lists, missing technical envelope, and
  unacknowledged corrigenda (412) before any DB write. Admin can delete
  legacy orphan bids via `DELETE /api/v1/bids/admin/{id}` with an
  in-page banner.

## Deploy

Unzip into your web root (e.g. `s3://<bucket>/` or nginx docroot) and make
sure your router falls back to `index.html` for SPA routes. Point
`REACT_APP_BACKEND_URL` at the same backend you were running for v51ak —
all new endpoints are backward-compatible.
