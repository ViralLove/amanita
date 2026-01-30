# Solution architecture — task-batch-mint-invites

**Дата:** 2026-01-30  
**Этап:** 3 — Архитектура решения  
**Решения:** см. decision-points-batch-mint.md (DP1=A, DP2=B, DP3=A, DP4=A)

---

## 1. Целевая модель

- **Сигнатура:** `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds)`.
- **Валидация:** `inviteCodes.length == expiries.length`, `inviteCodes.length > 0`, `inviteCodes.length <= MAX_BATCH_SIZE` (50).
- **Логика:** один вход в контракт (один `nonReentrant`), цикл по индексу; для каждого индекса — та же логика, что в `mintInvite`, через внутреннюю `_mintInviteSingle(inviteCode, expiry)`; эмит `InviteMinted` на каждый инвайт; возврат массива `tokenIds`.
- **Обратная совместимость:** `mintInvite` остаётся; после рефакторинга вызывает `_mintInviteSingle` и возвращает один tokenId. Новых state-переменных не вводим; `MAX_BATCH_SIZE` — константа, на storage layout не влияет; `__gap` не трогаем.

---

## 2. Изменяемые артефакты

| Артефакт | Изменения |
|----------|------------|
| `contracts/interfaces/ISpiralEngine.sol` | Добавить сигнатуру `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds);` |
| `contracts/SpiralEngineLogic.sol` | Константа `MAX_BATCH_SIZE = 50`; custom errors при необходимости (пустой batch, разная длина, превышение лимита); внутренняя `_mintInviteSingle`; рефакторинг `mintInvite` → вызов `_mintInviteSingle`; реализация `mintInviteBatch`. |
| `contracts/tests/` | Новый или расширенный тест-файл: успешный batch (2–3, 12), пустой массив, разная длина, дубликат в batch, не SELLER_ROLE, пауза. |
| `contracts/docs/SpiralEngine.md` (при наличии) | Описание batch-функции и лимита (P2). |

**SpiralEngine.sol (standalone):** не меняем (DP4=A).

---

## 3. Фазы и шаги

### Phase 0: Интерфейс и константа

| Шаг | Действие | Артефакт | Критерий проверки |
|-----|----------|----------|-------------------|
| 0.1 | Добавить в ISpiralEngine сигнатуру `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds);` | ISpiralEngine.sol | Компиляция contracts без ошибок |
| 0.2 | В SpiralEngineLogic добавить `uint256 public constant MAX_BATCH_SIZE = 50;` и при необходимости custom errors: `BatchLengthMismatch`, `BatchEmpty`, `BatchTooLarge` | SpiralEngineLogic.sol | Компиляция, константа видна в ABI |

**Артефакт фазы:** интерфейс и константа зафиксированы; Logic пока без реализации batch (вызов batch будет revert до Phase 1).

---

### Phase 1: Внутренняя логика и реализация batch

| Шаг | Действие | Артефакт | Критерий проверки |
|-----|----------|----------|-------------------|
| 1.1 | Добавить в SpiralEngineLogic внутреннюю `_mintInviteSingle(string calldata inviteCode, uint256 expiry) internal returns (uint256 tokenId)` с той же логикой, что сейчас в теле `mintInvite` (проверки EmptyInviteCode, InviteCodeAlreadyExists; счётчик, _mint, маппинги, userInvites, события). Без модификаторов (вызов только из mintInvite и mintInviteBatch). | SpiralEngineLogic.sol | Компиляция |
| 1.2 | Рефакторинг `mintInvite`: тело заменить на `return _mintInviteSingle(inviteCode, expiry);`. Модификаторы оставить: whenNotPaused, nonReentrant, onlyRole(SELLER_ROLE), override. | SpiralEngineLogic.sol | Существующие тесты mintInvite проходят (smoke, comprehensive) |
| 1.3 | Реализовать `mintInviteBatch`: проверки длины массивов (== между собой, > 0, <= MAX_BATCH_SIZE); цикл по i; для каждого вызов `_mintInviteSingle(inviteCodes[i], expiries[i])`; собирать tokenIds в memory-массив; return tokenIds. Модификаторы: whenNotPaused, nonReentrant, onlyRole(SELLER_ROLE), override. | SpiralEngineLogic.sol | Компиляция; ручная проверка или минимальный тест (batch из 2) |

**Артефакт фазы:** SpiralEngineLogic с _mintInviteSingle, обновлённым mintInvite и работающим mintInviteBatch; старые тесты зелёные.

---

### Phase 2: Тесты mintInviteBatch

| Шаг | Действие | Артефакт | Критерий проверки |
|-----|----------|----------|-------------------|
| 2.1 | Добавить тесты mintInviteBatch: успешный batch из 2–3 инвайтов; успешный batch из 12; пустой массив (revert); разная длина inviteCodes/expiries (revert); дубликат inviteCode внутри одного batch (revert); вызов не от SELLER_ROLE (revert); при паузе (revert). Проверять события InviteMinted и состояние (userInvites, totalInvitesMinted). | contracts/tests/ (новый файл или SpiralEngine.UUPS.smoke.test.js / отдельный SpiralEngine.batch.test.js) | Все новые тесты проходят; test-qualification по правилу |
| 2.2 | При необходимости: тест с batch размером MAX_BATCH_SIZE (50) для проверки лимита газа. | тот же тест-файл | Тест проходит или пропущен с обоснованием |

**Артефакт фазы:** отчёт квалификации тестов в папке таска (по run-phase / test-qualification).

---

### Phase 3: Документация

| Шаг | Действие | Артефакт | Критерий проверки |
|-----|----------|----------|-------------------|
| 3.1 | NatSpec для `mintInviteBatch` и при необходимости для `_mintInviteSingle` (internal — кратко). | SpiralEngineLogic.sol | Компиляция, читаемый NatSpec |
| 3.2 | При наличии contracts/docs/SpiralEngine.md — добавить описание batch-функции и MAX_BATCH_SIZE. | contracts/docs/ | Документ обновлён |

**Артефакт фазы:** актуальный NatSpec и при необходимости обновлённый docs.

---

## 4. Порядок выполнения и проверки

1. Выполнить Phase 0 → компиляция.
2. Выполнить Phase 1 → компиляция + прогон существующих тестов SpiralEngine (smoke/comprehensive).
3. Выполнить Phase 2 → полный прогон новых и существующих тестов; квалификация по test-qualification.
4. Выполнить Phase 3 → финальная проверка документации.

После каждой фазы — ретроспектива по продукту/процессу в папке таска (по run-phase). Коммиты — по согласованию с оператором (git-commit-prompt + git-commit).

---

## 5. Риски и митигация

| Риск | Митигация |
|------|-----------|
| Газ batch из 50 близок к лимиту блока | MAX_BATCH_SIZE = 50; при необходимости уменьшить или добавить тест на 50 и зафиксировать газ. |
| Storage layout | Новых state-переменных не вводим; только константа и внутренняя функция; __gap не трогаем. |
| Рассинхрон mintInvite и batch | Вся логика в _mintInviteSingle; mintInvite и batch вызывают только её. |

После утверждения архитектуры — переходим к **Этапу 4: Реализация по фазам** (Phase 0 → Phase 1 → Phase 2 → Phase 3).
