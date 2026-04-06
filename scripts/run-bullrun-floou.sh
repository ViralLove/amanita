#!/usr/bin/env bash
# Обёртка: канонический скрипт — scripts/shell/run-bullrun-floou.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/shell/run-bullrun-floou.sh" "$@"
