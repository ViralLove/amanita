#!/usr/bin/env sh
# Smoke checks for deployed arweave-uploader (HTTPS).
# Usage: from repo root, run ./scripts/smoke-deployed.sh
# Requires: DEPLOYED_URL в .env или константа по умолчанию. RELAY_AUTH_TOKEN не требуется (crystalize проверяется без Bearer).
# Без порта в URL — ходим по стандартному 443 (https).

set -e

# Load .env if present (DEPLOYED_URL, RELAY_AUTH_TOKEN)
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
fi

# Base URL: from env or constant (no trailing slash), без порта
if [ -n "$DEPLOYED_URL" ]; then
  case "$DEPLOYED_URL" in
    https://*) BASE_URL="$DEPLOYED_URL" ;;
    http://*)  BASE_URL="$DEPLOYED_URL" ;;
    *)         BASE_URL="https://${DEPLOYED_URL}" ;;
  esac
else
  BASE_URL="https://arweave-upload-production-888.up.railway.app"
fi

echo "Smoke target: $BASE_URL"
echo "--- 1) GET /health (retries for cold start) ---"
health_ok=0
health_attempt=1
health_max_attempts=5
health_sleep=3
while [ "$health_attempt" -le "$health_max_attempts" ]; do
  health_resp="$(curl -s -w "\n%{http_code}" --connect-timeout 10 --max-time 15 "$BASE_URL/health")"
  health_body="$(echo "$health_resp" | sed '$d')"
  health_code="$(echo "$health_resp" | tail -n 1)"
  echo "Attempt $health_attempt/$health_max_attempts: HTTP $health_code"
  if [ "$health_code" = "200" ]; then
    echo "$health_body" | head -c 200
    echo ""
    health_ok=1
    break
  fi
  echo "$health_body" | head -c 200
  echo ""
  if [ "$health_attempt" -lt "$health_max_attempts" ]; then
    echo "Retrying in ${health_sleep}s..."
    sleep "$health_sleep"
  fi
  health_attempt=$((health_attempt + 1))
done
if [ "$health_ok" -eq 0 ]; then
  echo "FAIL: /health expected 200 after $health_max_attempts attempts"
  exit 1
fi
echo "OK: /health"
echo ""

echo "--- 2) POST /v1/crystalize (ожидаем 400/401 без полного тела) ---"
crystalize_resp="$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/v1/crystalize" \
  -H "Content-Type: application/json" \
  -d '{}')"
crystalize_body="$(echo "$crystalize_resp" | sed '$d')"
crystalize_code="$(echo "$crystalize_resp" | tail -n 1)"
echo "HTTP $crystalize_code"
echo "$crystalize_body" | head -c 300
echo ""
if [ "$crystalize_code" != "400" ] && [ "$crystalize_code" != "401" ]; then
  echo "FAIL: /v1/crystalize ожидаем 400 (missing_field) или 401 (token_invalid), получили $crystalize_code"
  exit 1
fi
echo "OK: /v1/crystalize endpoint отвечает"
echo ""

# Step 3: real crystalize (optional)
if [ -n "$SMOKE_REAL" ] && { [ -n "$SMOKE_JWT_PRIVATE_KEY_PEM" ] || [ -n "$SMOKE_JWT_PRIVATE_KEY_FILE" ]; }; then
  echo "--- 3) POST /v1/crystalize (real payload, expect 200 + bundle_tx_id + arweave_url) ---"
  export DEPLOYED_URL="$BASE_URL"
  if node scripts/smoke-real-crystalize.js; then
    echo "OK: real crystalize"
  else
    echo "FAIL: real crystalize (see above)"
    exit 1
  fi
  echo ""
else
  echo "Real smoke skipped (set SMOKE_REAL=1 and SMOKE_JWT_PRIVATE_KEY_PEM or SMOKE_JWT_PRIVATE_KEY_FILE to enable)."
  echo ""
fi

echo "Smoke passed."
