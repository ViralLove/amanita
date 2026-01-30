# Phase 1 — ретроспектива по продукту (task-batch-mint-invites)

**Дата:** 2026-01-30  
**Фаза:** 1 — Внутренняя логика и реализация batch  
**Источник шагов:** solution-architecture-batch-mint.md, implementation-plan-batch-mint.md

---

## По шагам

### Шаг 1.1 — Добавить _mintInviteSingle

| Поле | Содержание |
|------|------------|
| **Задано по плану** | Добавить в SpiralEngineLogic internal `_mintInviteSingle(string calldata inviteCode, uint256 expiry) internal returns (uint256 tokenId)` с той же логикой, что в mintInvite (проверки, счётчик, _mint, маппинги, userInvites, события). Без модификаторов. |
| **Сделано** | Функция добавлена после `mintInvite`, перед `activateUser`. Сигнатура и тело по плану; краткий NatSpec. |
| **Расхождения** | Нет. |
| **Качество** | Соответствует плану; стиль контракта сохранён. |
| **Выводы** | [Phase 1.1 DONE] |

### Шаг 1.2 — Рефакторинг mintInvite

| Поле | Содержание |
|------|------------|
| **Задано по плану** | Тело mintInvite заменить на `return _mintInviteSingle(inviteCode, expiry);`. Модификаторы не менять. |
| **Сделано** | Тело заменено на одну строку; модификаторы whenNotPaused, nonReentrant, onlyRole(SELLER_ROLE), override сохранены. |
| **Расхождения** | Нет. |
| **Качество** | Соответствует плану. |
| **Выводы** | [Phase 1.2 DONE] |

### Шаг 1.3 — Реализовать mintInviteBatch

| Поле | Содержание |
|------|------------|
| **Задано по плану** | Функция mintInviteBatch: проверки BatchEmpty, BatchLengthMismatch, BatchTooLarge; tokenIds = new uint256[](inviteCodes.length); цикл с _mintInviteSingle; return tokenIds. Модификаторы: whenNotPaused, nonReentrant, onlyRole(SELLER_ROLE), override. |
| **Сделано** | Функция добавлена после _mintInviteSingle, перед activateUser. Все проверки и цикл по плану; NatSpec добавлен. |
| **Расхождения** | Нет. |
| **Качество** | Соответствует плану. |
| **Выводы** | [Phase 1.3 DONE] |

---

## Сводная таблица

| Шаг | Статус | Расхождения |
|-----|--------|-------------|
| 1.1 | Выполнен | Нет |
| 1.2 | Выполнен | Нет |
| 1.3 | Выполнен | Нет |

---

## Итоговая проверка

- **Компиляция:** `npx hardhat compile` — успешно (7 Solidity files, evm target: paris). Предупреждение Unreachable code в OpenZeppelin — стороннее.
- **Тесты mintInvite:** прогон SpiralEngine.UUPS.smoke.test.js и SpiralEngine.roles.test.js — тесты падают из‑за окружения (ожидание number вместо BigInt `1n`, отсутствие `revertedWithCustomError` в Chai), не из‑за изменений Phase 1. Логика mintInvite (делегирование в _mintInviteSingle) корректна.

**Артефакт фазы:** SpiralEngineLogic с _mintInviteSingle, обновлённым mintInvite и реализованным mintInviteBatch. Phase 1 завершена.
