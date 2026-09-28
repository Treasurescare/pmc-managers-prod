# PMC Managers Limited — Release v49f

## What's new in v49f

### 1 · Vendor portal in-page CTAs now wired end-to-end
The Option E static templates carried lots of dead `href="#"` buttons (Pay EMD,
Upload bank guarantee, View bid, Continue draft, View contract, Start bid,
Track, See all N notices, Saved searches, Sign LOA, Review & sign, Details,
Debrief, Reply, Preview, Change licence…). Users saw a beautiful page but every
button was inert.

`PmcLinkPatcher.jsx` was extended with a regex-based CTA matcher so every
vendor label lands on the right portal page:

| Label                                       | Routes to           |
| ------------------------------------------- | ------------------- |
| Pay EMD · Pay with card · Upload bank guarantee | `/vendor/emd`   |
| View bid · Continue draft · Track · Details · Debrief · Reply · Preview | `/vendor/mybids` |
| View contract · Review & sign · Sign LOA · Send me the DocuSign link | `/vendor/signatures` |
| Start bid · See all N open notices · Saved searches | `/vendor/tenders` |
| Add the licence · Change                    | `/vendor/company`   |
| Review · Leave a review                     | `/vendor/reviews`   |
| Raise a ticket                              | `/help`             |

### 2 · Vendor KPI tiles are clickable
The four KPI tiles on the vendor home now behave like links (cursor pointer,
`role="link"`, keyboard-accessible with Enter/Space):

| Tile                | Routes to           |
| ------------------- | ------------------- |
| Active bids         | `/vendor/mybids`    |
| Closing this week   | `/vendor/tenders`   |
| Matched to your KYC | `/vendor/tenders`   |
| KYC status          | `/vendor/company`   |
| Escrow balance · Pending EMD | `/vendor/emd` |

### 3 · Active / Closed tabs toggle
`<button class="pmc-tab">Active|Closed</button>` on the vendor home Your Bids
panel now toggles `aria-selected` when clicked (same behaviour as chips) so the
selection feels alive instead of frozen.

### 4 · Rate-limit `/password-reset/request` (per-email + per-IP)
- **Per-email cooldown**: 60 seconds between requests for the same address.
- **Per-IP sliding window**: max 10 requests / 5 minutes per source IP.
- The check runs BEFORE the account lookup, so a 429 response never leaks
  whether the email actually exists.
- Trims the in-memory table when it grows past 10 000 entries so a bad actor
  can't spike memory.
- Verified live:
  - 1st `POST` from an IP → **200 `{ok:true}`**.
  - 2nd `POST` with same email within 60 s → **429** with `"Please wait N s"`.
  - A different email within the same window → **200** (per-IP window still had budget).

## Bundles
- **Frontend:** `pmc-frontend-v49f-prod-build.zip`
  Built with `REACT_APP_BACKEND_URL=""` (same-origin S3/CloudFront ready).
- **Backend:** `pmc-backend-v49f.zip`
  Contains `Dockerfile`, `Dockerrun.aws.json`, `.platform/` at the archive root.

## Deploy
- Frontend: unzip into S3 root, invalidate CloudFront `/*`.
- CloudFront SPA rule (still required) — custom error responses:
  `403` → `/index.html` 200, `404` → `/index.html` 200.
- Backend: upload zip to Elastic Beanstalk. No new env vars required.

## Notes for scale-out
The reset rate limiter is single-pod in-memory. If we move to multi-instance
EB or add horizontal scaling, swap `_email_last` / `_ip_hits` for a Redis-
backed store; keep the same 60 s / 10-per-5-min knobs.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49e` if needed.
