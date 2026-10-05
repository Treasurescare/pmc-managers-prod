# PMC Managers — Release v51o (cumulative up to v51o)

## Fixes in this build (over v51n)

### Admin console — mobile defects you spotted

1. **Vendors page toolbar no longer distorts** — the Replace template /
   Download current / Bulk invite / Add & fill / Invite vendor strip
   previously stacked as 4 tall squeezed columns on a phone. The toolbar
   now wraps 2-up, buttons are centered and keep their 44px tap target.
2. **Bidding Ops row cards readable on a phone** — the row checkbox used
   to overlap the bid-info column; action buttons sat on one squeezed
   line. The checkbox now spans the full card height on the left, action
   buttons wrap into their own strip.
3. **Bidding Ops tab bar fits the viewport** — the 4-tab segmented control
   (Needs PMC / Waiting on supplier / Awarded / All) was forced to a
   single-row horizontal scroll and spilled off the right edge. It now
   wraps into two rows on mobile. Tab counts (e.g. "Awarded 3") were
   also drifting from the rows actually shown — the counts are now
   recomputed from the DOM so they always match the visible rows (and
   update as you toggle Hide test data or type in the search box).
4. **Hamburger drawer reaches Masters and the lower items** — the drawer
   used `height: 100vh`, which on iOS Safari extends below the visible
   area and trapped the last entries (Masters, Events & alerts,
   Stakeholder reports). The drawer now uses `100dvh` with touch
   scrolling and 96px bottom padding, so every sidebar item is reachable.

### Verified in preview (390×844)
- `scrollWidth === viewport (390)` on Vendors and Bidding Ops pages.
- Bidding Ops Awarded tab badge "3" = exactly 3 rows rendered when the
  tab is active.
- Drawer `scrollHeight > height` and `overflowY: auto`; Masters link
  becomes visible after scrolling.
- Desktop 1440 regression: tabs stay on one row, counts correct.

## Deploy
- Backend: unchanged since v51n — if you've already deployed
  `pmc-backend-v51n.zip`, you can re-use it. (A fresh `pmc-backend-v51o
  .zip` is included for convenience and is identical to v51n.)
- Frontend: `pmc-frontend-v51o-prod-build.zip` → S3, then CloudFront
  invalidate `/*`.

## Preview-only note
Preview DocuSign sandbox credentials are still expired
(`invalid_grant / issuer_not_found`); production credentials are not
affected by this release.
