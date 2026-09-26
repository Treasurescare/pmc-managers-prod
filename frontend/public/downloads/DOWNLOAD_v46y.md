# v46y — Rate a peer vendor: co-participation gated, 1-10 scoring, super-admin weightage

## Fixes

### 1 · "Submit anonymous review" does nothing (P0)
- Root cause: production DB had no `rating_criteria_sets` seeded → `/public/rubric` returned 404 → the submit button in the UI was permanently `disabled`. The click did fire but React's `disabled` attribute swallowed it silently. No error toast was shown either.
- Fix: added `_seed_default_rubric()` to `server.py` startup — idempotently creates a 5-parameter, 1-10 scale default rubric (quality, delivery, comms, compliance, cost). Also migrates any legacy 1-5 rubric to 1-10 on cold start.
- Errors from `/peer/submit` now surface via `showApiError` with a `Could not submit review` fallback title, so no silent failure again.

### 2 · Only co-participants can rate each other (P0)
- New helper `_co_participation_map()` in `routers/vendor_ratings.py` — walks `bids` collection to find vendors who bid (non-draft, non-withdrawn) on the same notice as the caller.
- `GET /api/v1/vendor-ratings/directory` now returns **only** those vendors, optionally scoped to one `tender_ref`.
- New `GET /api/v1/vendor-ratings/my-tenders` — lists distinct tenders the caller bid on, each with the count of co-bidders, so the vendor can pick which project the review is for.
- `POST /peer/submit` now **requires** `tender_ref` and independently verifies both parties bid on it. Returns `400` if omitted, `403` if not co-participating.
- Frontend rewritten: Step 1 = tender picker, Step 2 = co-participant picker, Step 3 = score 1-10 on each criterion, submit.

### 3 · Scoring range 1-10 across all criteria (P0)
- Backend default in `RatingCriterionIn.scale_max` bumped from 5 to 10.
- Seed rubric uses 1-10 for all 5 criteria.
- Cold-start migrator raises any existing rubric's `scale_max` to 10.

### 4 · Weightage editable only by super-admin (P0)
- Super-admin = admin/owner role with `hierarchy_level >= 10`. The master admin (`adminsupport@pmcmanagers.com`) already qualifies from v46w's role backfill.
- `POST /api/v1/tender-pro/rating-criteria` and `PATCH /api/v1/tender-pro/rating-criteria/{sid}`: if the caller is not super-admin, `weight` from the payload is **ignored** — new criteria are stamped with `weight=1.0`, existing criteria preserve their prior weight.
- New helper endpoint `GET /api/v1/tender-pro/rating-criteria/me` returns `{is_super_admin, hierarchy_level, roles}` so the admin UI can show/hide the weight column accordingly. (UI toggle wire-up planned for v46z; the backend guard is live now.)

---

## Verified live on preview
- `GET /public/rubric` → 5 criteria, scale 1-10.
- `POST /peer/submit` without `tender_ref` → HTTP 400, clear error message.
- `POST /peer/submit` with a `tender_ref` you did not bid on → HTTP 403, clear error message.
- `GET /directory` without any bids → empty array (no random vendor list).

## Deploy
- `pmc-backend-v46y.zip` — includes co-participation gate + super-admin weight lock + rubric seed. On EB cold-start the default rubric self-seeds and any legacy 1-5 rubric is migrated to 1-10 with no data loss.
- `pmc-frontend-v46y-prod-build.zip` — same-origin build, hash `main.513a41ae.js`. Ships the new 3-step Rate-A-Vendor flow.

Sync command (same as v46x):
```
aws s3 sync /tmp/pmc-build/ s3://pmc-managers-frontend-prod/ --delete --exclude "downloads/*" \
    --exclude "index.html" --exclude "service-worker.js" --exclude "manifest.json" \
    --cache-control "max-age=31536000,immutable"
aws s3 cp /tmp/pmc-build/index.html        s3://pmc-managers-frontend-prod/index.html        --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/service-worker.js s3://pmc-managers-frontend-prod/service-worker.js --cache-control "no-cache, no-store, must-revalidate"
aws s3 cp /tmp/pmc-build/manifest.json     s3://pmc-managers-frontend-prod/manifest.json     --cache-control "no-cache, no-store, must-revalidate"
aws cloudfront create-invalidation --distribution-id E2WZTT1TMQEK9W --paths "/*"
```
