#!/usr/bin/env bash
# Обёртка: канонический скрипт — scripts/shell/sync_artifacts_to_bot.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/shell/sync_artifacts_to_bot.sh" "$@"
