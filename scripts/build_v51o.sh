#!/usr/bin/env bash
# PMC v51o — Admin mobile UI defects fix
#
# Fixes four defects spotted on real-phone screenshots (390px):
#   1. Admin → Vendors page (mobile) — toolbar overflowed as four tall
#      squeezed strips. .vendors-toolbar now wraps 2-up, keeping buttons
#      touch-sized and legible.
#   2. Admin → Bidding Ops row cards — on mobile the checkbox clipped the
#      bid info and the action buttons sat on one squeezed line. Checkbox
#      now spans the full card height on the left, action buttons wrap.
#   3. Admin → Bidding Ops tabs — row previously overflowed right because
#      the segmented control was forced to nowrap. The .bo-bar .pmc-seg
#      now wraps and the counts (3 Awarded etc.) now always match the
#      rows actually rendered under each tab — tab counts are recomputed
#      in paint() from the DOM, respecting hide-test and the search box.
#   4. Admin hamburger drawer — last items (Masters, Events & alerts,
#      Stakeholder reports) were unreachable because the drawer used
#      100vh which on iOS Safari extends below the visible area. Drawer
#      now uses 100dvh + touch scrolling + 96px bottom padding, so every
#      sidebar item is reachable with a scroll.
set -eu
VER="v51o"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false yarn build 2>&1 | tail -3
# No source maps in production bundle
find "$ROOT/frontend/build" -name '*.map' -delete 2>/dev/null || true
cd "$ROOT/frontend/build"
rm -f "$DL/pmc-frontend-${VER}-prod-build.zip"
zip -qr "$DL/pmc-frontend-${VER}-prod-build.zip" . -x 'downloads/*' -x 'downloads'
cd "$ROOT"
rm -f "$DL/pmc-backend-${VER}.zip"
zip -qr "$DL/pmc-backend-${VER}.zip" backend Dockerfile Dockerrun.aws.json .platform \
    -x 'backend/__pycache__/*' -x 'backend/**/__pycache__/*' \
    -x 'backend/*.pyc' -x 'backend/**/*.pyc' \
    -x 'backend/.env' -x 'backend/venv/*' \
    -x 'backend/.pytest_cache/*' -x 'backend/tests/*' -x 'backend/keys/*' 2>/dev/null || true
cat > "$DL/DOWNLOAD_${VER}.md" << 'EOF'
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
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
