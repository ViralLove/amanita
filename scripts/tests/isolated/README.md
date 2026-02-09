# Isolated hypothesis-driven tests

Изолированные тесты для воспроизведения проблемных ситуаций и проверки гипотез по методологии [hypothesis-driven-error-analysis](../../../docs/methodology/hypothesis-driven-error-analysis.md).

## Назначение

- **Воспроизвести** ситуацию ошибки в контролируемой среде (моки).
- **Сопоставить** поведение с гипотезами (A1/A2, B1, C1 и т.д.).
- **Запуск:** `npx mocha scripts/tests/isolated/*.test.js --require scripts/tests/setup.js`

## Файлы

| Файл | Описание |
|------|----------|
| `rpc-tx-after-switch-receipt-hypothesis.test.js` | Воспроизведение сценария Action 777 tx3: send на primary → rate limit → switch → send на alternate → poll receipt. Проверяет ожидаемое поведение при гипотезах A1/A2 (receipt = null на обоих RPC) и B1 (receipt появляется на alternate при повторном опросе). |
| `README.md` | Этот файл. |

## Связь с анализом

- **Контекст:** [rpc-retry-action777-tx3-not-in-chain-analysis-2026-01-30.md](../../docs/analysis/rpc-retry-action777-tx3-not-in-chain-analysis-2026-01-30.md)
- **Диагностика на реальной сети:** опционально запустить `scripts/utility/diagnostic-rpc-receipt-after-switch.js` (см. описание в скрипте) для сбора данных: на каком RPC и когда появляется receipt после отправки tx через alternate.
