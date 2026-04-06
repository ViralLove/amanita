#!/usr/bin/env bash
#
# Только POST /activities/draft — тело из scripts/floou-draft-request.json (или FLOOU_DRAFT_JSON).
# Без оркестратора, без wallet-mock / uploader. Для ручной отладки следующих шагов.
#
# Переменные (scripts/.env или export):
#   BOT_URL — базовый URL API бота (дефолт: http://127.0.0.1:${BOT_PORT:-8000})
#   USER_ID — UUID для X-User-Id (дефолт: 00000000-0000-0000-0000-000000000001)
#   GPT_ACTIONS_BEARER_SECRET — если задан на боте, нужен тот же секрет (Authorization: Bearer)
#   FLOOU_DRAFT_JSON — путь к JSON-телу (дефолт: <repo>/scripts/floou-draft-request.json)
#   POST_FLOOU_DRAFT_VERBOSE=1 — печать заголовков ответа (-D) в stderr
#

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [ -f "$REPO_ROOT/scripts/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$REPO_ROOT/scripts/.env"
  set +a
else
  echo "post-floou-draft: нет $REPO_ROOT/scripts/.env — BOT_URL только из окружения или дефолт :8000" >&2
fi

export BOT_PORT="${BOT_PORT:-8000}"
# Пустой BOT_URL после .env даёт дефолт :8000 (${VAR:-…} считает пустую строку «как нет»).
export BOT_URL="${BOT_URL:-http://127.0.0.1:$BOT_PORT}"
export USER_ID="${USER_ID:-00000000-0000-0000-0000-000000000001}"

FLOOU_DRAFT_JSON="${FLOOU_DRAFT_JSON:-$REPO_ROOT/scripts/floou-draft-request.json}"

if [ ! -f "$FLOOU_DRAFT_JSON" ] || [ ! -s "$FLOOU_DRAFT_JSON" ]; then
  echo "post-floou-draft: нет файла тела или файл пуст: $FLOOU_DRAFT_JSON" >&2
  exit 1
fi

if ! python3 -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" "$FLOOU_DRAFT_JSON" 2>/dev/null; then
  echo "post-floou-draft: невалидный JSON: $FLOOU_DRAFT_JSON" >&2
  exit 1
fi

CURL_AUTH=()
if [ -n "${GPT_ACTIONS_BEARER_SECRET:-}" ]; then
  CURL_AUTH=(-H "Authorization: Bearer ${GPT_ACTIONS_BEARER_SECRET}")
fi

DRAFT_URL="${BOT_URL%/}/activities/draft"
echo "BOT_URL=$BOT_URL"
echo "POST $DRAFT_URL"
echo "  X-User-Id: $USER_ID"
if [ "${#CURL_AUTH[@]}" -gt 0 ]; then
  echo "  Authorization: Bearer ***"
else
  echo "  Authorization: (нет)"
fi
echo "  body: $FLOOU_DRAFT_JSON ($(wc -c <"$FLOOU_DRAFT_JSON" | tr -d ' ') bytes)"
echo ""

RESP_BODY="$(mktemp)"
RESP_HDR="$(mktemp)"
trap 'rm -f "$RESP_BODY" "$RESP_HDR"' EXIT

if [ "${POST_FLOOU_DRAFT_VERBOSE:-}" = "1" ]; then
  CURL_VERBOSE=(-v)
else
  CURL_VERBOSE=()
fi

HTTP_CODE="$(curl -sS "${CURL_VERBOSE[@]}" -D "$RESP_HDR" -o "$RESP_BODY" -w "%{http_code}" \
  -X POST "$DRAFT_URL" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  "${CURL_AUTH[@]}" \
  --data-binary @"$FLOOU_DRAFT_JSON")" || HTTP_CODE="000"

if [ "${POST_FLOOU_DRAFT_VERBOSE:-}" = "1" ]; then
  echo "=== response headers ===" >&2
  cat "$RESP_HDR" >&2
fi

echo "HTTP $HTTP_CODE"
if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool <"$RESP_BODY" 2>/dev/null || cat "$RESP_BODY"
else
  cat "$RESP_BODY"
fi
echo ""

if [ "$HTTP_CODE" != "201" ]; then
  exit 1
fi
