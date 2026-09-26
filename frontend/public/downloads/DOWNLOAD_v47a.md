# v47a — Admin bid actions: Approve / Hold / Resume / Reject

## What changed

### 1 · Approve button (was: Flag→Certifier)
The admin's pipeline-advance action on the bids table is now labelled **Approve → Certifier** (green). It appears when the bid is at `escrow_accepted` and admin is the active pipeline step. Same backend action as before (`decision` with `action=accept, role=admin`) — no behaviour change, just the clarity you asked for.

### 2 · Hold / Resume (new)
- New `on_hold` bid status. **Hold** is available on every in-flight stage (`submitted`, `emd_pending`, `emd_paid`, `escrow_accepted`, `admin_flagged`, and all review stages). It asks for an optional reason, stores `held_from_status` + `held_by` + `held_at` on the bid, and the row's "Next step" column shows *"On hold — admin to resume"*.
- **Resume** appears on held bids and restores the exact previous status.
- Backend enforces: only `role=admin` can hold/resume (other roles get 403); terminal states (`awarded`, `rejected`, `withdrawn`, `closed`, already `on_hold`) get 400.
- Hold/resume entries land in `workflow_history` and the audit log.

### 3 · Reject extended
Reject now also works on `on_hold` bids (previously only `emd_paid` / `escrow_accepted` / `admin_flagged`).

### Status labels
- Admin table: `escrow_accepted` → "Awaits Admin approval", `admin_flagged` → "Approved — Awaits Certifier", new "ON HOLD" chip.
- Vendor dashboard + bid detail modal: `on_hold` shows as "On Hold" / "On hold by PMC admin".

## Verified on preview
- `hold` on an `emd_pending` bid → `{"ok":true,"status":"on_hold"}` ✅
- `resume` → restores `emd_pending` ✅
- `hold` attempted as `certifier` role → 403 "Active role admin cannot act as certifier" ✅
- Frontend prod build clean, no preview URL baked in.

## Deploy
- `pmc-backend-v47a.zip` — decision endpoint with hold/resume + matrix label.
- `pmc-frontend-v47a-prod-build.zip` — same-origin build with the new action buttons.

Standard sync:
```
aws s3 sync /tmp/pmc-build/ s3://pmc-managers-frontend-prod/ --delete --exclude "downloads/*" \
    --exclude "index.html" --exclude "service-worker.js" --exclude "manifest.json" \
    --cache-control "max-age=31536000,immutable"
aws s3 cp /tmp/pmc-build/index.html        s3://pmc-managers-frontend-prod/index.html        --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/service-worker.js s3://pmc-managers-frontend-prod/service-worker.js --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/manifest.json     s3://pmc-managers-frontend-prod/manifest.json     --cache-control "no-cache, no-store, must-revalidate"
aws cloudfront create-invalidation --distribution-id E2WZTT1TMQEK9W --paths "/*"
```

## Carries forward
v46z (EMD fallback + View/Print bid modal) and v46y (Rate-a-Peer co-participation gate, 1-10 scoring, super-admin weightage) are all included in this backend zip — one deploy updates everything.
