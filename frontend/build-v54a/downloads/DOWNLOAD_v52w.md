# PMC Managers — Release v52w (frontend + backend)

## What changed since v52v

### Server-side Created-by / From / To rollout — remaining 4 panels
The v52v shared `CreatorDateFilterBar` filtered client-side only. v52w pushes
the same three filters down to Mongo for the remaining panels, so large
datasets no longer ship every row to the browser before filtering.

**Backend — new query params (`created_by_email`, `created_from`, `created_to`):**
- `GET /api/v1/reverse-auctions` — regex-matches `created_by`, range-filters
  `created_at` (ISO strings, same pattern as `bids.py` / `packages.py`).
- `GET /api/v1/docusign/envelopes` — same, on `created_by` + `created_at`;
  `limit` still honoured alongside the filters.
- Evaluation bids and Awards already used `GET /api/v1/bids`, which gained
  these params in v52v — no backend change needed there.

**Frontend — panels now send the params on every filter change:**
- **LiveAuctionsPanel** → `reverseAuctionApi.list(creatorDateParams(cdf))`
- **DocuSignPanel** → `docusignApi.listEnvelopes(creatorDateParams(cdf))`
  (`listEnvelopes` signature changed from `(limit)` to a params object)
- **EvaluationPanel** → `bidApi.list({ notice_ref, ...creatorDateParams(cdf) })`
- **AwardsPanel** → `bidApi.listAll({ status: "awarded", ...creatorDateParams(cdf) })`
- New shared helper `creatorDateParams()` in `CreatorDateFilterBar.jsx`
  (omits empty filters so requests stay no-op).
- Client-side `matchCreatorDate` kept as an instant fallback over the
  returned rows while the refetch is in flight (both, per your choice).
- Datalist sources fixed: auctions/envelopes store the creator in
  `created_by` (not `created_by_email` / `signer_email`), so the pickers now
  suggest the actual creator emails.

**Verified (preview, admin login):**
- Reverse auctions: empty → 7 rows; `created_by_email=zzz-nobody` → 0;
  2026 range → 7; 2027 range → 0.
- DocuSign envelopes: empty → 4; no-match creator → 0; 2026 range + limit → 4;
  2027 range → 0.
- Frontend production build compiles clean.

## Deploy

1. **Backend** — upload `pmc-backend-v52w.zip` to Elastic Beanstalk
   (Dockerfile at root; `.env` and `docker-compose.yml` excluded; AL2023
   Docker contract).
2. **Frontend** — unzip `pmc-frontend-v52w-prod-build.zip` to your S3 bucket
   root (overwrite). CloudFront → invalidation `/*`.
3. Open Reverse auctions / DocuSign / Evaluation / Awards — typing a creator
   or picking a date range now refetches from the server (watch the Network
   tab: `?created_by_email=…&created_from=…&created_to=…`).
