// docs/spec/12_security_hardening.md

# 12_security_hardening — Security hardening

## Цель
Снизить attack surface: зависимости, runtime, логи, обработка ошибок, защита секретов.

## Инварианты
- Supply-chain контроль: lockfile, запрет опасных install scripts.
- Нет секретов в логах/аналитике/краш-репортах.
- Минимальный набор разрешений приложения.
- Фичи включаются флагами, чувствительные — по умолчанию выключены.

## MVP
- Dependency policy: allowlist scripts, pinned versions.
- Runtime hardening: lockdown (если реально).
- Logging: redaction.

## Артефакты
- `SECURITY.md` (политики)
- `docs/security/dependency-policy.md`

## Тесты
- Lint rule: “no secrets in logs”.
- CI check: audit + deny scripts.