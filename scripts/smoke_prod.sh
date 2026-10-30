#!/usr/bin/env bash
# Production smoke verification script for Render deployed instance (A10)
# Usage: ./scripts/smoke_prod.sh <URL>
# Example: ./scripts/smoke_prod.sh https://aicte-1-59pn.onrender.com

set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <URL>"
  echo "Example: $0 https://aicte-1-59pn.onrender.com"
  exit 1
fi

BASE_URL="${1%/}"
FAILED=0

echo "================================================================="
echo "       AICTE FDR PORTAL - PRODUCTION SMOKE CHECK (A10)"
echo "Target: ${BASE_URL}"
echo "================================================================="

# Helper function
check_status() {
  local desc="$1"
  local url="$2"
  local expected="$3"
  local extra_args="${4:-}"

  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 ${extra_args} "${url}" || echo "000")
  if [ "$code" = "$expected" ]; then
    printf "  [PASS] %-42s (HTTP %s)\n" "$desc" "$code"
  else
    printf "  [FAIL] %-42s (Expected %s, got HTTP %s)\n" "$desc" "$expected" "$code"
    FAILED=$((FAILED + 1))
  fi
}

# 1. Liveness Probe
check_status "1. Liveness Probe (/health)" "${BASE_URL}/health" "200"

# 2. Readiness Probe
check_status "2. Readiness Probe (/ready)" "${BASE_URL}/ready" "200"
READY_JSON=$(curl -s --max-time 15 "${BASE_URL}/ready" || echo "{}")
READY_BUILD=$(echo "${READY_JSON}" | grep -o '"build":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
echo "     -> Active deployment build: ${READY_BUILD}"

# 3. Demo Login
LOGIN_RESP=$(curl -s -w "\n%{http_code}" --max-time 15 -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=inst.north1@example.com&password=AdminSecure2026!" \
  "${BASE_URL}/api/v1/login/access-token" || echo -e "\n000")

LOGIN_CODE=$(echo "$LOGIN_RESP" | tail -n 1)
if [ "$LOGIN_CODE" = "200" ]; then
  printf "  [PASS] %-42s (HTTP %s)\n" "3. Demo Login (inst.north1)" "$LOGIN_CODE"
else
  printf "  [FAIL] %-42s (Expected 200, got HTTP %s)\n" "3. Demo Login (inst.north1)" "$LOGIN_CODE"
  FAILED=$((FAILED + 1))
fi

# 4. Protected Route without Token (Expect 401 or 403)
PROT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "${BASE_URL}/api/v1/instruments/" || echo "000")
if [ "$PROT_CODE" = "401" ] || [ "$PROT_CODE" = "403" ]; then
  printf "  [PASS] %-42s (HTTP %s)\n" "4. Protected Route Auth Block" "$PROT_CODE"
else
  printf "  [FAIL] %-42s (Expected 401/403, got HTTP %s)\n" "4. Protected Route Auth Block" "$PROT_CODE"
  FAILED=$((FAILED + 1))
fi

# 5. Security Headers Check
HEADERS=$(curl -s -I --max-time 15 "${BASE_URL}/health" || true)
CHECK_HEADER() {
  local header_name="$1"
  if echo "$HEADERS" | grep -iq "^${header_name}:"; then
    printf "  [PASS] Security Header: %-32s (Present)\n" "$header_name"
  else
    printf "  [FAIL] Security Header: %-32s (Missing)\n" "$header_name"
    FAILED=$((FAILED + 1))
  fi
}

CHECK_HEADER "x-content-type-options"
CHECK_HEADER "x-frame-options"
CHECK_HEADER "referrer-policy"

echo "================================================================="
if [ $FAILED -eq 0 ]; then
  echo "RESULT: ALL PRODUCTION SMOKE CHECKS PASSED [GREEN]"
  exit 0
else
  echo "RESULT: ${FAILED} CHECKS FAILED [RED]"
  exit 1
fi
