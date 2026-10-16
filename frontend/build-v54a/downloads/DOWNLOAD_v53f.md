# PMC Managers — Release v53f (frontend + backend)

## What changed since v53e

### Zero-EMD logic fix — no money held ⇒ no escrow sign-off
You asked: "if there's no EMD, we don't need an escrow officer sign-off —
the logic should change." Correct, and it now does.

**Two layers, clarified:**
- **Money layer (escrow institution + dual sign-off):** unchanged and
  untouched — the PMC-officer + institution-officer dual signature only ever
  engages on a real EMD release/refund/forfeit transaction. No EMD held →
  no transaction → no sign-off. That was already true.
- **Pipeline layer (staff escrow step):** this was the dead-stop. An
  auction-awarded bid has no EMD, yet it still parked at "Escrow agent —
  confirm receipt" needing a separate login for a meaningless click.

**The change (`auction_live.py` award endpoint):** when the awarded bid has
no EMD due, it is now created directly at **`escrow_accepted`** with two
system-stamped `workflow_history` entries ("Auto-cleared: no EMD due" /
"Auto-cleared: no EMD held, so no escrow sign-off is required"), plus
`escrow_auto_cleared: true` for auditability. The next-step notification
goes straight to the **admin/tender desk** (flag to certifier) instead of
the escrow agent. EMD-bearing bids keep the full manual escrow step —
nothing changes for them.

Frontend: the Award-winner toast and button tooltip now reflect the actual
landing stage.

**E2E verified in preview:** create → bid → close → award → bid
`BID-AUC-…` at `escrow_accepted` with both system history entries and
`escrow_auto_cleared: true`; re-award idempotent; test data cleaned.

**Note on your existing prod bid:** `BID-AUC-A03BF7` was awarded before this
fix, so it still sits at `emd_paid`. One-time action: sign in to the staff
portal as `escrow@pmcmanagers.com / Escrow@123` and click Accept — or leave
it and re-run the award on a fresh auction to see the new flow. Every new
auction award from v53f onward auto-clears.

## Deploy

1. **Backend** — `pmc-backend-v53f.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53f-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
