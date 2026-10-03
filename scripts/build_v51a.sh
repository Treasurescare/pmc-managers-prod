#!/usr/bin/env bash
# PMC v51a — Masters tab bar realign + instant deactivate/reactivate
# (a) Masters tab bar: labels no longer wrap to two lines (whitespace-nowrap
#     + shrink-0), single horizontally-scrollable row, verbose "(moved →
#     Market)" labels shortened.
# (b) Legal entity types: optimistic toggle — Deactivate/Reactivate flips
#     the row instantly with rollback on failure; no hard refresh needed.
# (c) Backend: every /api/ response now carries Cache-Control: no-store so
#     CloudFront can never serve a stale pre-mutation list (the root cause
#     of "deactivate needed a hard refresh").
set -eu
VER="v51a"
ROOT="/app"
DL="$ROOT/frontend/public/downloads"
mkdir -p "$DL"
cd "$ROOT/frontend"
REACT_APP_BACKEND_URL="" yarn build 2>&1 | tail -3
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
# PMC Managers — Release v51a (cumulative v50m → v51a)

## Fixes in this build
- **Masters tab bar realigned**: tab labels no longer wrap onto two lines
  ("LEGAL ENTITY TYPES" etc.); single horizontally-scrollable row with
  consistent spacing. Verbose "(moved → Market)" suffixes removed.
- **Instant deactivate/reactivate**: Legal entity types (and the same
  class of bug anywhere) — the row flips immediately on click with
  rollback if the server call fails. Previously the refetch could return
  a CloudFront-cached pre-mutation list, forcing a hard refresh.
- **API cache safety (root cause)**: every /api/ response now sends
  `Cache-Control: no-store, no-cache, must-revalidate` so CloudFront can
  never serve a stale list after a mutation.

## Deploy (backend REQUIRED for the cache fix)
1. `pmc-backend-v51a.zip` → Elastic Beanstalk
2. `pmc-frontend-v51a-prod-build.zip` → S3 + CloudFront invalidate `/*`
EOF
ls -lh "$DL/pmc-frontend-${VER}-prod-build.zip" "$DL/pmc-backend-${VER}.zip" "$DL/DOWNLOAD_${VER}.md"
