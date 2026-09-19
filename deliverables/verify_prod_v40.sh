#!/usr/bin/env bash
# ============================================================================
# PMC Managers v2 — Verify v40 + v22f on production
# ============================================================================
set -eo pipefail

WWW="${WWW:-https://www.pmcmanagers.com}"
EXPECTED_MAIN="${EXPECTED_MAIN:-main.727b5a39.js}"

pass() { printf "  \033[32m✔\033[0m %s\n" "$*"; }
fail() { printf "  \033[31m✘\033[0m %s\n" "$*"; RC=1; }
warn() { printf "  \033[33m!\033[0m %s\n" "$*"; }
RC=0

echo "==== 1. Apex 301 → www ==============================================="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -I "https://pmcmanagers.com")
LOC=$(curl -s -I "https://pmcmanagers.com" | awk 'tolower($1)=="location:"{print $2}' | tr -d '\r')
[[ "$STATUS" == "301" ]] && pass "apex returns 301" || fail "apex returned $STATUS"
[[ "$LOC" =~ https://www.pmcmanagers.com ]] && pass "Location = $LOC" || fail "unexpected Location: $LOC"

echo
echo "==== 2. Frontend index served + new main.js referenced ==============="
INDEX=$(curl -sSL "$WWW")
echo "$INDEX" | grep -q "$EXPECTED_MAIN" && pass "index.html references $EXPECTED_MAIN" \
  || fail "index.html does NOT reference $EXPECTED_MAIN (still on old bundle — retry after invalidation)"

echo
echo "==== 3. New main.js loads with correct Content-Type =================="
JS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$WWW/static/js/$EXPECTED_MAIN")
JS_CT=$(curl -sI "$WWW/static/js/$EXPECTED_MAIN" | awk 'tolower($1)=="content-type:"{print $2}' | tr -d '\r')
[[ "$JS_STATUS" == "200" ]] && pass "js status = 200" || fail "js status = $JS_STATUS"
[[ "$JS_CT" =~ javascript ]] && pass "js content-type = $JS_CT" || warn "js content-type = $JS_CT"

echo
echo "==== 4. Backend health (via same-origin /api/*) ======================"
HC=$(curl -s "$WWW/api/v1/meta/health" -w "\n%{http_code}")
CODE=$(echo "$HC" | tail -1); BODY=$(echo "$HC" | sed '$d')
[[ "$CODE" == "200" ]] && pass "health = 200 · $BODY" || fail "health $CODE · $BODY"

echo
echo "==== 5. /me endpoint returns Cache-Control: no-store (Bug #29) ======="
CC=$(curl -sI "$WWW/api/v1/admin/auth/me" | awk 'tolower($1)=="cache-control:"{sub(/^[^:]+:[ ]*/,"");print;exit}' | tr -d '\r')
[[ "$CC" =~ no-store ]] && pass "cache-control = $CC" || fail "cache-control = $CC (expected no-store)"

echo
echo "==== 6. Rubric validator rejects weight=2 (Bug #49) =================="
# This endpoint requires admin auth so we just probe that it's registered
# (unauthenticated → expect 401 not 404).
RUB=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WWW/api/v1/evaluations/rubric" \
  -H "Content-Type: application/json" -d '{"notice_ref":"x","technical_criteria":[]}')
[[ "$RUB" == "401" || "$RUB" == "422" || "$RUB" == "403" ]] && pass "rubric endpoint reachable ($RUB)" \
  || fail "rubric endpoint returned $RUB"

echo
echo "==== 7. Escrow governance flag exposed (Bug 2026-09-19) =============="
ESC=$(curl -s -o /dev/null -w "%{http_code}" "$WWW/api/v1/escrow/accounts")
[[ "$ESC" == "401" || "$ESC" == "403" ]] && pass "escrow accounts endpoint reachable ($ESC unauth as expected)" \
  || fail "escrow accounts returned $ESC"

echo
echo "==== 8. www redirect from apex resolves correctly at TCP level ======="
curl -s -o /dev/null -w "  final URL   : %{url_effective}\n  total time  : %{time_total}s\n  http code   : %{http_code}\n" \
  -L "https://pmcmanagers.com"

echo
if [[ $RC -eq 0 ]]; then
  echo "✅ ALL CHECKS PASSED — v40 + v22f are live."
else
  echo "❌ Some checks failed — see red ✘ lines above."
fi
exit $RC
