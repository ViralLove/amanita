#!/usr/bin/env bash
# Проверка мок-эндпоинтов uploads (PUT status, POST callback).
# Запуск: из корня репо или bot/ при уже запущенном API на порту 8000.
# Пример: cd bot && (uvicorn api.main:app --host 127.0.0.1 --port 8000 &) && sleep 5 && bash tests/api/test_uploads_mock_curl.sh

set -e
BASE="${BASE_URL:-http://127.0.0.1:8000}"
SECRET="${EDGE_TO_BACKEND_SECRET:-mock-edge-to-backend-secret}"

echo "=== 1. PUT status с Bearer (ожидается 200) ==="
code=$(curl -s -o /tmp/upload_resp1.txt -w "%{http_code}" -X PUT "$BASE/v1/uploads/550e8400-e29b-41d4-a716-446655440000/status" \
  -H "Authorization: Bearer $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"status":"queued_for_publish"}')
cat /tmp/upload_resp1.txt
echo " -> HTTP $code"
test "$code" = "200" || { echo "FAIL: expected 200"; exit 1; }

echo ""
echo "=== 2. PUT status без Bearer (ожидается 401) ==="
code=$(curl -s -o /tmp/upload_resp2.txt -w "%{http_code}" -X PUT "$BASE/v1/uploads/550e8400-e29b-41d4-a716-446655440000/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"queued_for_publish"}')
cat /tmp/upload_resp2.txt
echo " -> HTTP $code"
test "$code" = "401" || { echo "FAIL: expected 401"; exit 1; }

echo ""
echo "=== 3. POST callback с Bearer (ожидается 200) ==="
code=$(curl -s -o /tmp/upload_resp3.txt -w "%{http_code}" -X POST "$BASE/v1/uploads/callback" \
  -H "Authorization: Bearer $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"upload_id":"550e8400-e29b-41d4-a716-446655440000","item_id":"abc123","bundle_tx_id":"0xdef","published_at":"2026-01-30T12:00:00Z"}')
cat /tmp/upload_resp3.txt
echo " -> HTTP $code"
test "$code" = "200" || { echo "FAIL: expected 200"; exit 1; }

echo ""
echo "=== 4. PUT status failed + failure_code (ожидается 200) ==="
code=$(curl -s -o /tmp/upload_resp4.txt -w "%{http_code}" -X PUT "$BASE/v1/uploads/550e8400-e29b-41d4-a716-446655440000/status" \
  -H "Authorization: Bearer $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"status":"failed","failure_code":"token_invalid"}')
cat /tmp/upload_resp4.txt
echo " -> HTTP $code"
test "$code" = "200" || { echo "FAIL: expected 200"; exit 1; }

echo ""
echo "=== 5. PUT невалидный body (ожидается 422) ==="
code=$(curl -s -o /tmp/upload_resp5.txt -w "%{http_code}" -X PUT "$BASE/v1/uploads/550e8400-e29b-41d4-a716-446655440000/status" \
  -H "Authorization: Bearer $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"status":"invalid"}')
cat /tmp/upload_resp5.txt
echo " -> HTTP $code"
test "$code" = "422" || { echo "FAIL: expected 422"; exit 1; }

echo ""
echo "All uploads mock checks passed."
