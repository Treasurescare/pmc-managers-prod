# PMC Managers — Release v53g (frontend + backend)

## What changed since v53f

### Zero-EMD auto-clear now covers REGULAR sealed bids too
v53f applied the rule to reverse-auction awards; v53g extends the same rule
to sealed bids, per your call — **no EMD due ⇒ no money held ⇒ no escrow
sign-off**, regardless of bid source.

**Backend (`bids.py` create_bid):**
- A sealed bid on a tender with zero EMD due is now created directly at
  **`escrow_accepted`** (was: `submitted`, where it waited for a manual
  escrow-agent click — the v52cs workaround).
- Two system-stamped `workflow_history` entries ("Auto-cleared: no EMD
  due…" / "…no escrow sign-off is required") + `escrow_auto_cleared: true`
  for audit.
- The **tender desk (admin) is notified immediately** ("ready for Flag to
  certifier") — previously zero-EMD bids at `submitted` notified nobody,
  which is why they sat invisible.
- EMD-bearing bids: **unchanged** (emd_pending → pay → escrow accept).

**Also fixed — L1 comparison blind spot (`comparison.py`):** `live_statuses`
only covered `submitted`/`technical_cleared`/`commercial_open`/
`under_evaluation`/`awarded`, so any bid mid-pipeline (escrow_accepted,
admin_flagged, certifier_cleared, legal_cleared, accounting_cleared,
emd_paid) was being reported as "withdrawn/rejected" in L1 results. All
alive pipeline statuses are now included.

**Vendor portal (VendorMyBidsE):** mid-pipeline statuses now show as
"In PMC review" under Active bids instead of falling through unlabelled.

**E2E verified in preview (real vendor submission):**
- Zero-EMD notice → bid created at `escrow_accepted`, both system history
  entries present, admin notification fired.
- EMD-bearing notice → bid at `emd_pending`, no auto-clear flags. 
- Test data cleaned.

**Existing prod rows:** zero-EMD bids submitted before v53g that still sit
at `submitted`/`emd_pending` can still be moved by the escrow agent accept
(v52cs path) — or ask me for a one-time sweep to auto-clear them.

## Deploy

1. **Backend** — `pmc-backend-v53g.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53g-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
