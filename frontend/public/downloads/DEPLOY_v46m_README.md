# PMC Managers — Deploy v46m (Bug Blitz Round Two, cumulative on v46l)

## What's new since v46l

### Locked-evaluation guard (Bug #52 — hardened)
- **Backend** `POST /api/v1/evaluations/lock-envelope` now **refuses to re-lock** (HTTP 409 + audit trail message). No silent overwrites of the lock timestamp / attribution.
- **Backend** `GET /api/v1/evaluations/lock-state/{notice_ref}` — new endpoint returns `{technical_locked_at, technical_locked_by, commercial_locked_at, commercial_locked_by}`.
- **Frontend** `EvaluationPanel`:
  - Loads lock state on every notice-ref change.
  - "Lock Technical / Lock Commercial" buttons become **disabled + "Sealed 🔒" label** once locked, with a tooltip showing the seal timestamp.
  - New **envelope status banner** shows the seal timestamps + who locked each envelope.
  - Backend already refuses new scores on locked envelopes (Bug #52 in prior release); the UI now matches.

### Mobile overflow (Bug tracker items 78 / 81 / 82)
- **AuctionRoom · recent bids row** (`AuctionRoom.jsx` L192–L207) — was fixed widths `w-32 / w-24` colliding on narrow phones. Now `flex-col sm:flex-row`, fixed widths only kick in ≥ 640 px, `break-all` on the money column so long six-figure prices never overflow.
- **Analytics · pipeline funnel** — already fixed in v46 (2 / 4 / 8 responsive grid). No change needed.

### Rubric max (Bug #49) & Registration step gate
- Verified in code — both were fixed in earlier releases and still hold:
  - `RubricEditor` enforces `weight 0–1`, `commercial 0–1`, `min-tech 0–100`, weights sum ≈ 1.00, "Save rubric" disabled until valid.
  - `RegistrationResume` blocks the **Next** button when any of `company_name / registered_address / country / registration_number / legal_entity_type` is empty and shows a red gap count.

### Stakeholder-report snapshot JSON parse — RCA outcome
- The snapshot endpoint (`POST /api/v1/reports/snapshot`) already wraps every artefact in its own try/except and returns a well-formed JSON envelope with an `errors[]` list — no more opaque 500s (Bug #38).
- Grepping the current frontend surfaces no code path that consumes this endpoint, so there is **no live JSON parse regression** to reproduce. Flagging as *no repro against current source*; happy to re-open with a specific browser stack trace / URL if you still see it after deploying v46m.

### i18n Russian / Kazakh backfill
- Not shipped in v46m. Full retranslation of ~1 500 keys is a dedicated pass. Marking as *still open* in the tracker.

### Manual v2
- Not shipped in v46m. Regenerating a 130–160 page manual requires ~200 fresh Playwright captures against the deployed sovereign screens plus a WeasyPrint build. Planned as its own release once v46m has landed on production so the captures reflect the final visual state.

## Deploy

Same order as v46l — this drop is **cumulative** on top of v46l, so if you already deployed v46l you can either:

* (a) drop **v46m only** on top, OR
* (b) skip v46l and deploy v46m directly.

```bash
# Backend
eb deploy --staged --label v46m

# Frontend (non-destructive!)
unzip pmc-frontend-v46m-prod-build.zip -d ./v46m-build
aws s3 sync ./v46m-build/ s3://pmc-managers-frontend-prod/ \
  --exact-timestamps --exclude "downloads/*"
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```

## Post-deploy validation checklist

1. **DPR unlimited (v46l carried forward)** — upload a 20 MB / 500-page DPR; the file card shows a "Background" chip, live progress bar advances, section count exceeds 30.
2. **Envelope lock** — go to Evaluation, enter a live notice ref, click Lock Technical; the button becomes "Technical · Sealed 🔒" and the banner shows the seal timestamp. Refreshing the page persists the sealed state.
3. **Reverse-auction mobile** — open `/auction-room/<ref>` on a phone; the recent-bids rows now wrap cleanly and prices never overflow.
