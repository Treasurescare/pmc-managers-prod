# PMC Managers — v51ax (remaining bug-sheet clearing batch)

**Build date:** 2026-10-10
**Frontend bundle:** `pmc-frontend-v51ax-prod-build.zip`
**Backend bundle:** `pmc-backend-v51ax.zip` (includes the DocuSign fix)

## 🐞 Fixed

### DocuSign admin-sign doesn't flip vendor status (xlsx #17)
Root cause: `_on_envelope_completed()` in `routers/docusign.py` stamped the
bid with `db.bids.update_one({"id": row["bid_id"]}, ...)`. Bid documents
are keyed on Mongo `_id` (ObjectId) — there is no `id` field — so the
update silently matched zero documents every time. The envelope completed,
emails went out, but the bid was never stamped, so the vendor portal kept
showing "pending signature".
Fix: match by `{"_id": ObjectId(bid_id)}` and also set
`docusign_completed_at` for a clear audit trail.

### $0 EMD bids stuck at Step 4 (xlsx #14)
Backend already creates zero-EMD bids directly in `submitted` status — but
`VendorBidWorkspaceE.jsx` computed
`emdSettled = emdDue > 0 && emdOutstanding === 0`, which is permanently
false when due is 0, so the workspace never unlocked the finish flow.
Fix: `emdSettled = emdDue <= 0 || emdOutstanding === 0`.

### Comma rejected in registration figures (xlsx #11)
Section A (employees) and Section C (turnover years 1–3) used
`type="number"` inputs, which browsers refuse to type commas into.
Switched to `type="text" inputMode="decimal"` and strip commas before
parsing, so `1,250,000` works.

## ✅ Verified as already-correct (no code change needed)

- **Corrigendum on public page** (docx #18): the publish flow sets
  `is_active: true` and the public notice endpoint attaches all active
  corrigenda. If one specific corrigendum isn't showing, share its
  notice_ref — it's a data state on that record, not the pipeline.

## 📝 Remaining (out of scope for this batch)

- **DocuSign Resend 424** — rotate `DOCUSIGN_*` keys (operational, steps in
  DOWNLOAD_v51av.md).
- **Engagements: no schedule-meeting action** — P2 feature.
- **Admin prolonged-use crashes** — needs a memory-profiling session.

## Deploy

1. Backend: upload `pmc-backend-v51ax.zip` to Elastic Beanstalk
   (`pmc-backend-prod`) — replaces v51au.
2. Frontend: unzip `pmc-frontend-v51ax-prod-build.zip` into S3 →
   CloudFront invalidation `/*`.
