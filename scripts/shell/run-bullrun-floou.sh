#!/usr/bin/env bash
#
# Bullrun Floou: поднять стек (local) или только mock-runner (remote), затем
# POST /activities/draft телом из scripts/floou-draft-request.json, дождаться цикла
# подписей в mock-runner, GET /activities/{id}. Блокчейн-нода — отдельно.
#
# Контракт скрипта (что имеет смысл задавать снаружи):
#   FLOOU_MODE — local (дефолт) | remote
#   USER_ID    — UUID для X-User-Id (дефолт ниже)
# Остальное (BOT_URL, ARWEAVE_SERVICE_URL, …) — в scripts/.env (подхватывается автоматически) или export в shell.
# Для local — .env в bot/ и arweave-uploader при старте дочерних процессов.
#
# Тело draft: фиксированный файл  scripts/floou-draft-request.json  (шаблон: .example)
#   local:  нет файла / битый JSON → встроенное тело
#   remote: файл обязателен (валидный JSON)
#
# Мануал: scripts/docs/bullrun-floou-manual.md
#
# Лог-артефакт: scripts/logs/{S1}.{S2}.{S3}.{S4}.{S5}.{S6}-{ddMMyyyyHHmm}.txt — отключить: FLOOU_LOG_DISABLE=true
# Доп. флаги: FLOOU_STRICT, --strict, FLOOU_SUBMIT_TIMEOUT_SEC
#

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [ -f "$REPO_ROOT/scripts/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$REPO_ROOT/scripts/.env"
  set +a
fi

FLOOU_DRAFT_FILE="$REPO_ROOT/scripts/floou-draft-request.json"

for _floou_arg in "$@"; do
  case "$_floou_arg" in
    --strict) export FLOOU_STRICT=true ;;
  esac
done

export BOT_PORT="${BOT_PORT:-8000}"
export UPLOADER_PORT="${UPLOADER_PORT:-3000}"
export BOT_URL="${BOT_URL:-http://127.0.0.1:$BOT_PORT}"
export ARWEAVE_SERVICE_URL="${ARWEAVE_SERVICE_URL:-http://127.0.0.1:$UPLOADER_PORT}"
export USER_ID="${USER_ID:-00000000-0000-0000-0000-000000000001}"
export EDGE_TO_BACKEND_SECRET="${EDGE_TO_BACKEND_SECRET:-mock-edge-to-backend-secret}"

# Совпадает с bot: GPT_ACTIONS_BEARER_SECRET — middleware на /activities и /reference (см. gpt_actions_bearer.py).
# Задайте в scripts/.env тот же секрет, что в bot/.env, иначе curl без Bearer получит 401.
FLOOU_BOT_CURL_AUTH=()
if [ -n "${GPT_ACTIONS_BEARER_SECRET:-}" ]; then
  FLOOU_BOT_CURL_AUTH=(-H "Authorization: Bearer ${GPT_ACTIONS_BEARER_SECRET}")
fi

export BACKEND_URL="$BOT_URL"
export PORT="$UPLOADER_PORT"

_floou_mode_raw="${FLOOU_MODE:-local}"
case "$_floou_mode_raw" in
  local|LOCAL|Local) export FLOOU_MODE=local ;;
  remote|REMOTE|Remote) export FLOOU_MODE=remote ;;
  *)
    echo "floou: неизвестный FLOOU_MODE='$_floou_mode_raw' (ожидается local или remote)" >&2
    exit 1
    ;;
esac

# remote без явных URL в scripts/.env → остаются дефолты localhost; оркестратор не стартует bot/uploader, но ждёт /health там — обычно зависание
if [ "$FLOOU_MODE" = "remote" ]; then
  case "${BOT_URL:-}" in
    http://127.0.0.1*|http://localhost*)
      echo "floou: [remote] BOT_URL всё ещё localhost ($BOT_URL) — задайте BOT_URL и ARWEAVE_SERVICE_URL в scripts/.env (удалённые базы). Иначе скрипт ждёт /health там, где сервисов нет." >&2
      ;;
  esac
  case "${ARWEAVE_SERVICE_URL:-}" in
    http://127.0.0.1*|http://localhost*)
      echo "floou: [remote] ARWEAVE_SERVICE_URL всё ещё localhost ($ARWEAVE_SERVICE_URL) — см. scripts/.env." >&2
      ;;
  esac
fi

FLOOU_SUBMIT_TIMEOUT_SEC="${FLOOU_SUBMIT_TIMEOUT_SEC:-90}"
# Сколько секунд ждать /health у Bot и uploader (медленный импорт + Web3)
FLOOU_SERVICE_READY_SEC="${FLOOU_SERVICE_READY_SEC:-30}"

# --- Logging artifact (see decision-points in task folder) ---
FLOOU_LOG_DIR="$REPO_ROOT/scripts/logs"
FLOOU_LOG_FILE=""
FLOOU_TMP_LOGS=""
BOT_LOG=""
UP_LOG=""
WAL_LOG=""

floou_is_log_enabled() {
  case "${FLOOU_LOG_DISABLE:-}" in
    1|true|TRUE|yes|Yes|y|Y) return 1 ;;
    *) return 0 ;;
  esac
}

floou_gen_log_filename() {
  REPO_ROOT="$REPO_ROOT" python3 -c '
import os, re, time, random
repo = os.environ["REPO_ROOT"]
log_dir = os.path.join(repo, "scripts", "logs")
os.makedirs(log_dir, exist_ok=True)
fmt = "%d%m%Y%H%M"
ts = time.strftime(fmt, time.localtime())
pid = os.getpid()
rng = random.Random((pid ^ int(time.time()) ^ 0xC0FFEE) & 0xFFFFFFFF)
segments = [str(rng.randint(1, 999999)) for _ in range(6)]
pat = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+-[0-9]{12}\.txt$")
for bump in range(0, 100000):
    segs = segments[:-1] + [str(int(segments[-1]) + bump)]
    name = ".".join(segs) + "-" + ts + ".txt"
    if not pat.match(name):
        continue
    path = os.path.join(log_dir, name)
    if not os.path.exists(path):
        print(path)
        break
else:
    raise SystemExit("floou: could not allocate log filename")
'
}

floou_write_log_header() {
  [ -n "$FLOOU_LOG_FILE" ] || return 0
  {
    echo "=== Bullrun Floou run log ==="
    echo "log_timezone: local ($(date +%Z 2>/dev/null || echo "?"))"
    echo "started_at_local: $(date -Iseconds 2>/dev/null || date)"
    echo "shell: ${SHELL:-}"
    echo "uname: $(uname -s 2>/dev/null) $(uname -r 2>/dev/null)"
    echo "BOT_URL=$BOT_URL"
    echo "ARWEAVE_SERVICE_URL=$ARWEAVE_SERVICE_URL"
    echo "USER_ID=$USER_ID"
    echo "FLOOU_SUBMIT_TIMEOUT_SEC=$FLOOU_SUBMIT_TIMEOUT_SEC"
    echo "FLOOU_SERVICE_READY_SEC=$FLOOU_SERVICE_READY_SEC"
    echo "FLOOU_MODE=${FLOOU_MODE:-}"
    echo "FLOOU_STRICT=${FLOOU_STRICT:-}"
    echo "FLOOU_LOG_DISABLE=${FLOOU_LOG_DISABLE:-}"
    echo "GPT_ACTIONS_BEARER_SECRET_for_curl=$([ -n "${GPT_ACTIONS_BEARER_SECRET:-}" ] && echo set || echo unset)"
    echo ""
    echo "=== Chronology (orchestrator) ==="
  } >"$FLOOU_LOG_FILE"
}

# Короткая строка в консоль + полная строка в артефакт (если включён лог)
floou_msg() {
  if [ -n "$FLOOU_LOG_FILE" ]; then
    printf '%s\n' "$@" | tee -a "$FLOOU_LOG_FILE" >&1
  else
    printf '%s\n' "$@"
  fi
}

floou_file_append_file_section() {
  local title="$1"
  local path="$2"
  [ -n "$FLOOU_LOG_FILE" ] || return 0
  [ -f "$path" ] || return 0
  echo "" >>"$FLOOU_LOG_FILE"
  echo "=== $title ===" >>"$FLOOU_LOG_FILE"
  cat "$path" >>"$FLOOU_LOG_FILE"
}

floou_json_file_ok() {
  python3 -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" "$1" 2>/dev/null
}

# Задаёт FLOOU_DRAFT_BODY_FILE или FLOOU_DRAFT_INLINE; в remote при отсутствии/невалидности — exit 1
floou_select_draft_body() {
  FLOOU_DRAFT_BODY_FILE=""
  FLOOU_DRAFT_INLINE=""
  local p="$FLOOU_DRAFT_FILE"
  if [ -f "$p" ] && [ -s "$p" ] && floou_json_file_ok "$p"; then
    FLOOU_DRAFT_BODY_FILE="$p"
    floou_msg "📎 Тело draft: файл $p"
    return 0
  fi
  if [ "$FLOOU_MODE" = "remote" ]; then
    if [ ! -f "$p" ] || [ ! -s "$p" ]; then
      floou_msg "❌ remote: нужен непустой JSON для POST /activities/draft: $p"
    else
      floou_msg "❌ remote: файл не является валидным JSON: $p"
    fi
    exit 1
  fi
  floou_msg "ℹ️ local: нет валидного JSON в $p — встроенное тело draft (как в прежних версиях скрипта)."
  FLOOU_DRAFT_INLINE='{"activity_type":"event","title":"Full Floou from script","short_summary":"E2E local run"}'
}

stop_children() {
  echo ""
  echo "Остановка сервисов..."
  [ -n "$WALLET_PID" ] && kill "$WALLET_PID" 2>/dev/null || true
  [ -n "$UPLOADER_PID" ] && kill "$UPLOADER_PID" 2>/dev/null || true
  [ -n "$BOT_PID" ] && kill "$BOT_PID" 2>/dev/null || true
  [ -n "$WALLET_PID" ] && wait "$WALLET_PID" 2>/dev/null || true
  [ -n "$UPLOADER_PID" ] && wait "$UPLOADER_PID" 2>/dev/null || true
  [ -n "$BOT_PID" ] && wait "$BOT_PID" 2>/dev/null || true
}

floou_epilogue() {
  local ec=$?
  stop_children
  rm -f "${FLOOU_DONE_MARKER_FILE:-}"
  if floou_is_log_enabled && [ -n "${FLOOU_LOG_FILE:-}" ] && [ -f "$FLOOU_LOG_FILE" ]; then
    {
      echo ""
      echo "=== Appendix: child process logs (full stdout/stderr) ==="
      echo ""
      echo "--- Bot ---"
      if [ -n "${BOT_LOG:-}" ] && [ -f "$BOT_LOG" ]; then cat "$BOT_LOG"; else echo "(empty)"; fi
      echo ""
      echo "--- arweave-uploader ---"
      if [ -n "${UP_LOG:-}" ] && [ -f "$UP_LOG" ]; then cat "$UP_LOG"; else echo "(empty)"; fi
      echo ""
      echo "--- wallet-mock ---"
      if [ -n "${WAL_LOG:-}" ] && [ -f "$WAL_LOG" ]; then cat "$WAL_LOG"; else echo "(empty)"; fi
      echo ""
      echo "=== Result summary ==="
      echo "exit_code: $ec"
      echo "ended_at_local: $(date -Iseconds 2>/dev/null || date)"
      if [ "$ec" -eq 0 ]; then
        echo "status_line: success"
      elif [ "$ec" -eq 130 ]; then
        echo "status_line: interrupted (SIGINT/SIGTERM)"
      else
        echo "status_line: failure"
      fi
      echo "artifact_path: $FLOOU_LOG_FILE"
    } >>"$FLOOU_LOG_FILE"
    rm -rf "${FLOOU_TMP_LOGS:-}" 2>/dev/null || true
  fi
  builtin exit "$ec"
}

on_signal() {
  exit 130
}
trap on_signal SIGINT SIGTERM
trap floou_epilogue EXIT

if floou_is_log_enabled; then
  FLOOU_LOG_FILE=""
  _floou_log_path=""
  _floou_log_path="$(floou_gen_log_filename 2>/dev/null)" || true
  if [ -n "$_floou_log_path" ]; then
    FLOOU_LOG_FILE="$_floou_log_path"
    FLOOU_TMP_LOGS="$(mktemp -d "${TMPDIR:-/tmp}/floou-logs.XXXXXX")" || FLOOU_TMP_LOGS=""
    if [ -n "$FLOOU_TMP_LOGS" ]; then
      BOT_LOG="$FLOOU_TMP_LOGS/bot.log"
      UP_LOG="$FLOOU_TMP_LOGS/uploader.log"
      WAL_LOG="$FLOOU_TMP_LOGS/wallet.log"
    else
      FLOOU_LOG_FILE=""
    fi
  fi
  floou_write_log_header
fi

floou_msg "📌 Bullrun Floou — FLOOU_MODE=$FLOOU_MODE  USER_ID=$USER_ID"
floou_msg "  draft: $FLOOU_DRAFT_FILE (см. .example)"
floou_msg "  BOT_URL=$BOT_URL  ARWEAVE_SERVICE_URL=$ARWEAVE_SERVICE_URL"
floou_msg "  FLOOU_STRICT=${FLOOU_STRICT:-off}"
if [ -n "$FLOOU_LOG_FILE" ]; then
  floou_msg "  📎 Полный лог: $FLOOU_LOG_FILE"
else
  floou_msg "  📎 Файл лога отключён (FLOOU_LOG_DISABLE или ошибка инициализации)"
fi

FLOOU_DRAFT_CREATED=0

BOT_PID=""
UPLOADER_PID=""
WALLET_PID=""
FLOOU_DONE_MARKER_FILE=""

# Structured summary + optional strict validation (см. scripts/docs/DEBUG_DEPLOY.md).
floou_emit_summary() {
  local _marker="${1:-}"
  local _skip_strict="${2:-0}"
  export FLOOU_DRAFT_CREATED="${FLOOU_DRAFT_CREATED:-0}"
  export FLOOU_STRICT="${FLOOU_STRICT:-}"
  export FLOOU_SKIP_STRICT="$_skip_strict"
  python3 - "$_marker" <<'PY'
import json, os, sys

mp = sys.argv[1] if len(sys.argv) > 1 else ""
strict = os.environ.get("FLOOU_STRICT", "").strip().lower() in ("1", "true", "yes", "y")
skip_strict = os.environ.get("FLOOU_SKIP_STRICT") == "1"
draft = os.environ.get("FLOOU_DRAFT_CREATED") == "1"
m = {}
if mp and os.path.isfile(mp) and os.path.getsize(mp) > 0:
    try:
        with open(mp, encoding="utf-8") as f:
            m = json.load(f)
    except Exception:
        m = {}
co = m.get("crystalize_ok")
cb = m.get("callback_ok")
so = m.get("submit_ok")
if so is None:
    so = m.get("ok")
th = m.get("tx_hash")
summary = {
    "draft_created": draft,
    "crystalize_ok": True if co is True else (False if co is False else None),
    "callback_ok": True if cb is True else (False if cb is False else None),
    "submit_ok": bool(so) if so is not None else False,
    "tx_hash": th if isinstance(th, str) and th.strip() else None,
}
print("")
print("=== FLOOU_SUMMARY_JSON ===")
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
print("=== FLOOU_SUMMARY_PLAIN ===")
for k in ("draft_created", "crystalize_ok", "callback_ok", "submit_ok", "tx_hash"):
    print(f"{k}: {summary[k]}")
if strict and not skip_strict:
    errs = []
    if not draft:
        errs.append("draft_created")
    if co is not True:
        errs.append("crystalize_ok")
    if cb is not True:
        errs.append("callback_ok")
    if so is not True:
        errs.append("submit_ok")
    if not (isinstance(th, str) and th.strip()):
        errs.append("tx_hash")
    if errs:
        print("=== FLOOU_STRICT_FAIL === " + ",".join(errs), file=sys.stderr)
        sys.exit(1)
sys.exit(0)
PY
}

if [ "$FLOOU_MODE" = "remote" ]; then
  if [ ! -f "$FLOOU_DRAFT_FILE" ] || [ ! -s "$FLOOU_DRAFT_FILE" ]; then
    floou_msg "❌ remote: до старта mock-runner нужен непустой JSON: $FLOOU_DRAFT_FILE"
    exit 1
  fi
  if ! floou_json_file_ok "$FLOOU_DRAFT_FILE"; then
    floou_msg "❌ remote: файл не является валидным JSON: $FLOOU_DRAFT_FILE"
    exit 1
  fi
fi

if [ "$FLOOU_MODE" = "local" ]; then
  # ---------------------------------------------------------------------------
  # 1) Запуск Bot (uvicorn). .env подхватывается из bot/
  # ---------------------------------------------------------------------------
  floou_msg "⏳ [1/3] Запуск Bot на порту $BOT_PORT..."
  if [ -n "$BOT_LOG" ]; then
    (
      exec >>"$BOT_LOG" 2>&1
      cd "$REPO_ROOT/bot"
      [ -f .env ] && set -a && . ./.env && set +a
      export EDGE_TO_BACKEND_SECRET
      exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port "$BOT_PORT"
    ) &
  else
    (
      cd "$REPO_ROOT/bot"
      [ -f .env ] && set -a && . ./.env && set +a
      export EDGE_TO_BACKEND_SECRET
      exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port "$BOT_PORT"
    ) &
  fi
  BOT_PID=$!

  # ---------------------------------------------------------------------------
  # 2) Запуск arweave-uploader
  # ---------------------------------------------------------------------------
  floou_msg "⏳ [2/3] Запуск arweave-uploader на порту $UPLOADER_PORT..."
  if [ -n "$UP_LOG" ]; then
    (
      exec >>"$UP_LOG" 2>&1
      cd "$REPO_ROOT/arweave-uploader"
      [ -f .env ] && set -a && . ./.env && set +a
      export PORT BACKEND_URL EDGE_TO_BACKEND_SECRET
      exec node dist/server.js
    ) &
  else
    (
      cd "$REPO_ROOT/arweave-uploader"
      [ -f .env ] && set -a && . ./.env && set +a
      export PORT BACKEND_URL EDGE_TO_BACKEND_SECRET
      exec node dist/server.js
    ) &
  fi
  UPLOADER_PID=$!
else
  floou_msg "⏭️  [remote] Локальные Bot и arweave-uploader не запускаются (BOT_URL=$BOT_URL)."
fi

FLOOU_DONE_MARKER_FILE="$(mktemp)"
export FLOOU_DONE_MARKER_FILE

# ---------------------------------------------------------------------------
# Запуск wallet-mock (всегда локально)
# ---------------------------------------------------------------------------
if [ "$FLOOU_MODE" = "local" ]; then
  floou_msg "⏳ [3/3] Запуск wallet-mock runner..."
else
  floou_msg "⏳ [1/1] Запуск wallet-mock runner (remote)..."
fi
if [ -n "$WAL_LOG" ]; then
  (
    exec >>"$WAL_LOG" 2>&1
    cd "$REPO_ROOT/wallet/mock-runner"
    export BOT_URL ARWEAVE_SERVICE_URL USER_ID FLOOU_DONE_MARKER_FILE
    export POLL_INTERVAL_MS="${POLL_INTERVAL_MS:-1500}"
    export WALLET_MOCK_ARWEAVE_SIGN_MODE="${WALLET_MOCK_ARWEAVE_SIGN_MODE:-local-valid}"
    export ARWEAVE_UPLOADER_PATH="${ARWEAVE_UPLOADER_PATH:-$REPO_ROOT/arweave-uploader}"
    export WALLET_AUTH_MODE="${WALLET_AUTH_MODE:-challenge_signature}"
    export WALLET_ALLOW_LEGACY_X_USER_ID="${WALLET_ALLOW_LEGACY_X_USER_ID:-true}"
    export WALLET_MOCK_PRIVATE_KEY="${WALLET_MOCK_PRIVATE_KEY:-}"
    export WALLET_MOCK_ADDRESS="${WALLET_MOCK_ADDRESS:-}"
    export WALLET_MOCK_ARWEAVE_PRIVATE_KEY="${WALLET_MOCK_ARWEAVE_PRIVATE_KEY:-}"
    export WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE="${WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE:-}"
    exec node index.js
  ) &
else
  (
    cd "$REPO_ROOT/wallet/mock-runner"
    export BOT_URL ARWEAVE_SERVICE_URL USER_ID FLOOU_DONE_MARKER_FILE
    export POLL_INTERVAL_MS="${POLL_INTERVAL_MS:-1500}"
    export WALLET_MOCK_ARWEAVE_SIGN_MODE="${WALLET_MOCK_ARWEAVE_SIGN_MODE:-local-valid}"
    export ARWEAVE_UPLOADER_PATH="${ARWEAVE_UPLOADER_PATH:-$REPO_ROOT/arweave-uploader}"
    export WALLET_AUTH_MODE="${WALLET_AUTH_MODE:-challenge_signature}"
    export WALLET_ALLOW_LEGACY_X_USER_ID="${WALLET_ALLOW_LEGACY_X_USER_ID:-true}"
    export WALLET_MOCK_PRIVATE_KEY="${WALLET_MOCK_PRIVATE_KEY:-}"
    export WALLET_MOCK_ADDRESS="${WALLET_MOCK_ADDRESS:-}"
    export WALLET_MOCK_ARWEAVE_PRIVATE_KEY="${WALLET_MOCK_ARWEAVE_PRIVATE_KEY:-}"
    export WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE="${WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE:-}"
    exec node index.js
  ) &
fi
WALLET_PID=$!

# ---------------------------------------------------------------------------
# Ожидание готовности Bot и Uploader
# ---------------------------------------------------------------------------
floou_msg "⏳ Ожидание готовности Bot ($BOT_URL)..."
i=0
while [ "$i" -lt "$FLOOU_SERVICE_READY_SEC" ]; do
  i=$((i + 1))
  if curl -s -o /dev/null -w "%{http_code}" "$BOT_URL/health" 2>/dev/null | grep -q 200; then
    floou_msg "✅ Bot готов."
    break
  fi
  if [ "$i" -ge "$FLOOU_SERVICE_READY_SEC" ]; then
    floou_msg "❌ Таймаут ожидания Bot."
    floou_emit_summary "${FLOOU_DONE_MARKER_FILE:-}" 1 2>&1 | { [ -n "$FLOOU_LOG_FILE" ] && tee -a "$FLOOU_LOG_FILE" || cat; } || true
    exit 1
  fi
  sleep 1
done

floou_msg "⏳ Ожидание готовности arweave-uploader ($ARWEAVE_SERVICE_URL)..."
i=0
while [ "$i" -lt "$FLOOU_SERVICE_READY_SEC" ]; do
  i=$((i + 1))
  if curl -s -o /dev/null -w "%{http_code}" "$ARWEAVE_SERVICE_URL/health" 2>/dev/null | grep -q 200; then
    floou_msg "✅ Uploader готов."
    break
  fi
  if [ "$i" -ge "$FLOOU_SERVICE_READY_SEC" ]; then
    floou_msg "❌ Таймаут ожидания Uploader."
    floou_emit_summary "${FLOOU_DONE_MARKER_FILE:-}" 1 2>&1 | { [ -n "$FLOOU_LOG_FILE" ] && tee -a "$FLOOU_LOG_FILE" || cat; } || true
    exit 1
  fi
  sleep 1
done

# ---------------------------------------------------------------------------
# 4) POST /activities/draft
# ---------------------------------------------------------------------------
floou_msg ""
floou_msg "📌 Точка входа: POST /activities/draft"

floou_select_draft_body

DRAFT_RESPONSE="$(mktemp)"
DRAFT_RESP_HDR="$(mktemp)"
floou_msg ""
floou_msg "=== curl POST /activities/draft (request) ==="
floou_msg "  URL: $BOT_URL/activities/draft"
floou_msg "  -H Content-Type: application/json"
floou_msg "  -H X-User-Id: $USER_ID"
if [ "${#FLOOU_BOT_CURL_AUTH[@]}" -gt 0 ]; then
  floou_msg "  -H Authorization: Bearer *** (GPT_ACTIONS_BEARER_SECRET в scripts/.env)"
else
  floou_msg "  -H Authorization: (нет) — при непустом секрете на стороне bot ожидайте 401"
fi
if [ -n "$FLOOU_DRAFT_BODY_FILE" ]; then
  _sz="$(wc -c <"$FLOOU_DRAFT_BODY_FILE" 2>/dev/null | tr -d ' ')"
  floou_msg "  --data-binary @$FLOOU_DRAFT_BODY_FILE (${_sz:-?} bytes)"
else
  floou_msg "  -d <inline JSON>"
fi

if [ -n "$FLOOU_DRAFT_BODY_FILE" ]; then
  HTTP_CODE="$(curl -sS -D "$DRAFT_RESP_HDR" -o "$DRAFT_RESPONSE" -w "%{http_code}" \
    -X POST "$BOT_URL/activities/draft" \
    -H "Content-Type: application/json" \
    -H "X-User-Id: $USER_ID" \
    "${FLOOU_BOT_CURL_AUTH[@]}" \
    --data-binary @"$FLOOU_DRAFT_BODY_FILE")" || HTTP_CODE="000"
else
  HTTP_CODE="$(curl -sS -D "$DRAFT_RESP_HDR" -o "$DRAFT_RESPONSE" -w "%{http_code}" \
    -X POST "$BOT_URL/activities/draft" \
    -H "Content-Type: application/json" \
    -H "X-User-Id: $USER_ID" \
    "${FLOOU_BOT_CURL_AUTH[@]}" \
    -d "$FLOOU_DRAFT_INLINE")" || HTTP_CODE="000"
fi

if [ -n "$FLOOU_LOG_FILE" ]; then
  floou_file_append_file_section "Draft curl: response headers (-D)" "$DRAFT_RESP_HDR"
else
  echo "=== Draft curl: response headers (-D) ==="
  cat "$DRAFT_RESP_HDR"
fi
rm -f "$DRAFT_RESP_HDR"

if [ "$HTTP_CODE" -ne 201 ]; then
  floou_msg "❌ Draft: HTTP $HTTP_CODE"
  floou_file_append_file_section "Draft error response body" "$DRAFT_RESPONSE"
  if [ -z "$FLOOU_LOG_FILE" ]; then
    cat "$DRAFT_RESPONSE" | python3 -m json.tool 2>/dev/null || cat "$DRAFT_RESPONSE"
  fi
  rm -f "$DRAFT_RESPONSE"
  floou_emit_summary "${FLOOU_DONE_MARKER_FILE:-}" 1 2>&1 | { [ -n "$FLOOU_LOG_FILE" ] && tee -a "$FLOOU_LOG_FILE" || cat; } || true
  exit 1
fi

FLOOU_DRAFT_CREATED=1

ACTIVITY_ID="$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
print(d.get('activity', {}).get('activity_id', ''))
" "$DRAFT_RESPONSE" 2>/dev/null)"
UPLOAD_ID="$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
print(d.get('upload_id', ''))
" "$DRAFT_RESPONSE" 2>/dev/null)"

floou_msg "✅ Draft создан (HTTP 201) activity_id=$ACTIVITY_ID upload_id=$UPLOAD_ID"
floou_file_append_file_section "Draft response JSON" "$DRAFT_RESPONSE"
if [ -z "$FLOOU_LOG_FILE" ]; then
  echo ""
  echo "Ответ draft:"
  python3 -m json.tool <"$DRAFT_RESPONSE" 2>/dev/null || cat "$DRAFT_RESPONSE"
fi
rm -f "$DRAFT_RESPONSE"

# ---------------------------------------------------------------------------
# 5) Ожидание маркера submit
# ---------------------------------------------------------------------------
floou_msg ""
floou_msg "⏳ Ожидание цикла подписей (до ${FLOOU_SUBMIT_TIMEOUT_SEC} с)…"

deadline=$(( $(date +%s) + FLOOU_SUBMIT_TIMEOUT_SEC ))
floou_ok=0
while true; do
  if [ -s "$FLOOU_DONE_MARKER_FILE" ]; then
    if python3 -c "
import json, sys
p = sys.argv[1]
with open(p) as f:
    d = json.load(f)
sys.exit(0 if d.get('ok') is True else 1)
" "$FLOOU_DONE_MARKER_FILE" 2>/dev/null; then
      floou_msg "✅ Submit подтверждён (маркер ok)."
      floou_ok=1
      break
    fi
  fi
  now=$(date +%s)
  if [ "$now" -ge "$deadline" ]; then
    floou_msg "❌ Таймаут ожидания submit (${FLOOU_SUBMIT_TIMEOUT_SEC} с)."
    floou_emit_summary "${FLOOU_DONE_MARKER_FILE:-}" 1 2>&1 | { [ -n "$FLOOU_LOG_FILE" ] && tee -a "$FLOOU_LOG_FILE" || cat; } || true
    exit 1
  fi
  sleep 1
done

if [ "$floou_ok" -ne 1 ]; then
  floou_emit_summary "${FLOOU_DONE_MARKER_FILE:-}" 1 2>&1 | { [ -n "$FLOOU_LOG_FILE" ] && tee -a "$FLOOU_LOG_FILE" || cat; } || true
  exit 1
fi

# ---------------------------------------------------------------------------
# 6) Итог: GET activity
# ---------------------------------------------------------------------------
floou_msg ""
floou_msg "📌 Итог загрузки (GET /activities/{id})"

ACTIVITY_JSON=""
if [ -n "$ACTIVITY_ID" ]; then
  ACT_GET_HDR="$(mktemp)"
  ACT_GET_BODY="$(mktemp)"
  floou_msg "=== curl GET /activities/$ACTIVITY_ID ==="
  floou_msg "  URL: $BOT_URL/activities/$ACTIVITY_ID"
  floou_msg "  -H X-User-Id: $USER_ID"
  if [ "${#FLOOU_BOT_CURL_AUTH[@]}" -gt 0 ]; then
    floou_msg "  -H Authorization: Bearer ***"
  fi
  _GET_CODE="$(curl -sS -D "$ACT_GET_HDR" -o "$ACT_GET_BODY" -w "%{http_code}" \
    -H "X-User-Id: $USER_ID" \
    "${FLOOU_BOT_CURL_AUTH[@]}" \
    "$BOT_URL/activities/$ACTIVITY_ID")" || _GET_CODE="000"
  floou_file_append_file_section "GET activity: response headers" "$ACT_GET_HDR"
  floou_msg "  HTTP $_GET_CODE"
  ACTIVITY_JSON="$(cat "$ACT_GET_BODY" 2>/dev/null)" || ACTIVITY_JSON=""
  rm -f "$ACT_GET_HDR" "$ACT_GET_BODY"
  if echo "$ACTIVITY_JSON" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    floou_msg "✅ Activity получена: $ACTIVITY_ID"
    if [ -n "$FLOOU_LOG_FILE" ]; then
      echo "" >>"$FLOOU_LOG_FILE"
      echo "=== Activity JSON (GET /activities/$ACTIVITY_ID) ===" >>"$FLOOU_LOG_FILE"
      printf '%s\n' "$ACTIVITY_JSON" >>"$FLOOU_LOG_FILE"
    else
      echo "$ACTIVITY_JSON" | python3 -m json.tool 2>/dev/null || echo "$ACTIVITY_JSON"
    fi
  else
    floou_msg "⚠️ Activity: ответ не JSON или ошибка сети."
  fi
fi

floou_msg ""
floou_msg "Кратко: sign_arweave → crystalize → callback → sign_contract → submit."
floou_msg "Коды выхода: 0 успех; 1 ошибка; 130 прерывание."

SUMMARY_RC=0
if [ -n "$FLOOU_LOG_FILE" ]; then
  set +e
  set -o pipefail
  floou_emit_summary "$FLOOU_DONE_MARKER_FILE" 0 2>&1 | tee -a "$FLOOU_LOG_FILE"
  SUMMARY_RC=${PIPESTATUS[0]}
  set +o pipefail
  set -e
else
  floou_emit_summary "$FLOOU_DONE_MARKER_FILE" 0 || SUMMARY_RC=$?
fi

if [ "$SUMMARY_RC" -eq 0 ]; then
  floou_msg ""
  floou_msg "✅ Bullrun Floou complete"
  floou_msg "  • Цикл подписей и strict-summary (если включён) — ок."
  if [ -n "$FLOOU_LOG_FILE" ]; then
    floou_msg "  • Полный протокол и логи сервисов: $FLOOU_LOG_FILE"
  fi
else
  floou_msg ""
  floou_msg "❌ Strict-проверка не пройдена (см. FLOOU_STRICT_FAIL выше)."
fi

rm -f "$FLOOU_DONE_MARKER_FILE"
exit "$SUMMARY_RC"
