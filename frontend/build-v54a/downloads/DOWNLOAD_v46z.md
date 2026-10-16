# v46z — EMD fallback + View/Print bid detail

## Fixes

### 1 · Bids silently accepted without EMD prompt (P0)
- **Root cause**: `POST /api/v1/bids` computed `emd_due` from `notice.emd_config`. When admins publish a notice without `emd_config`, the value defaults to `EMDConfig(fixed_amount=0, percentage=0)` and `emd_due = 0`. The bid gets `status="submitted"` and the "Pay EMD" button never renders. That's what happened to `info@emeraldcorporates.com`.
- **Fix**: When `notice.emd_config is None` AND `budget_amount > 0`, the backend now applies a **fallback of 1 % of budget with a floor of 500** in the notice currency and stamps `emd_source = "default_fallback"`. This ensures the vendor is always prompted to pay EMD when the admin forgot to configure it. If the admin explicitly configured `emd_config` (even zeros), we respect that — `emd_source = "notice_config"`.
- **Live verified**: bid on `PMC-NOT-2026-0018` (budget 100 000 USD, no `emd_config`) → `emd_due_amount = 1000`, `status = "emd_pending"`, `emd_source = "default_fallback"` → the "Pay EMD" button now shows.

### 2 · View + Print on My Bids (P0)
- New `BidDetailModal.jsx` — fetches `GET /api/v1/bids/{id}` (existing endpoint) plus notice metadata and renders a printable, read-only bid card with:
  - bid ref, notice ref + title, status, timestamps
  - commercial (price, EMD due/paid, EMD source)
  - technical + commercial notes
  - attached documents
  - workflow history
- Each row in the My Bids list now has a **View** button. Inside the modal there's a **Print / Save PDF** button that triggers `window.print()` with a scoped stylesheet that hides everything except the modal body — so vendors can save a clean PDF snapshot for their records.

## Deploy

- `pmc-backend-v46z.zip` — includes the EMD fallback logic.
- `pmc-frontend-v46z-prod-build.zip` — same-origin build, includes BidDetailModal + View button + "No EMD required" badge.

Standard sync command (same as v46x/v46y):
```
aws s3 sync /tmp/pmc-build/ s3://pmc-managers-frontend-prod/ --delete --exclude "downloads/*" \
    --exclude "index.html" --exclude "service-worker.js" --exclude "manifest.json" \
    --cache-control "max-age=31536000,immutable"
aws s3 cp /tmp/pmc-build/index.html        s3://pmc-managers-frontend-prod/index.html        --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/service-worker.js s3://pmc-managers-frontend-prod/service-worker.js --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/manifest.json     s3://pmc-managers-frontend-prod/manifest.json     --cache-control "no-cache, no-store, must-revalidate"
aws cloudfront create-invalidation --distribution-id E2WZTT1TMQEK9W --paths "/*"
```

## Existing bids on prod that are stuck at `submitted` with `emd_due=0`

These are orphans from the pre-fix era. Two options:

1. **Let them ride** — the admin can manually mark them `emd_paid` via the Admin console (or delete + re-invite the vendor to re-bid). Simpler if there are only a few.
2. **Bulk backfill** — I can ship a `scripts/backfill_emd_due.py` that walks bids with `emd_due_amount = 0` on notices with `budget_amount > 0`, applies the same 1 %/$500 fallback and flips them to `emd_pending`. Tell me if you want that as v46z-hotfix.

## Combined ledger (also carrying v46y forward)

The v46z backend also ships v46y's Rate-a-Peer rebuild:
- Co-participation gate on `/directory` + `/peer/submit`
- 1-10 scoring rubric auto-seeded on cold start
- Weightage locked to super-admin (hierarchy_level ≥ 10)
