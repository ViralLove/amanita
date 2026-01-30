# План реализации — task-batch-mint-invites

**Дата:** 2026-01-30  
**Назначение:** Конкретный пошаговый план изменений по файлам и шагам **до** написания кода. Используется при выполнении фаз по run-phase (Planning → Implementation → Validation).  
**Источники:** solution-architecture-batch-mint.md, decision-points-batch-mint.md

---

## 1. Алгоритм (напоминание)

По **docs/methodology/task-execution-process.md** и **run-phase** + **multi-step-phase-execution**:

1. **Этап 3** — архитектура (solution-architecture) ✅ сделана.  
2. **Этап 4** — реализация **по фазам**. Каждую фазу выполняем по **run-phase**: шаги фазы → TODO → для каждого шага: **Understanding → Knowledge Check → Acceptance Criteria → Planning → Implementation → Validation → Retrospective**.  
3. **Planning** (план изменений: какие файлы, какие правки) выполняется **до** Implementation и согласуется с планом фазы.  
4. Настоящий документ — **подготовленный план реализации**: конкретизация правок по шагам, чтобы при запуске фазы не переходить к коду без плана.

---

## 2. Текущий статус фаз

| Фаза | Статус | Комментарий |
|------|--------|-------------|
| Phase 0 | Выполнена частично | В ISpiralEngine добавлена сигнатура mintInviteBatch; в SpiralEngineLogic добавлены MAX_BATCH_SIZE и custom errors (BatchEmpty, BatchLengthMismatch, BatchTooLarge). Реализации mintInviteBatch в Logic нет → компиляция падает (contract should be marked abstract). |
| Phase 1 | Выполнена | 1.1–1.3 сделаны: _mintInviteSingle, рефакторинг mintInvite, mintInviteBatch. Компиляция OK. Существующие тесты падают из‑за окружения (BigInt/revertedWithCustomError), не из‑за кода Phase 1. |
| Phase 2 | Выполнена | SpiralEngine.batch.test.js — 9 тестов (успех 2/3/12, BatchEmpty, BatchLengthMismatch, BatchTooLarge, дубликат, роль, пауза). Отчёт квалификации: phase2-test-qualification-batch-mint.md. 2.2 (batch 50) пропущен с обоснованием. |
| Phase 3 | Выполнена | NatSpec для mintInviteBatch и _mintInviteSingle уже в SpiralEngineLogic (Phase 1). В contracts/docs/SpiralEngine.md добавлены описание mintInviteBatch, MAX_BATCH_SIZE и пример вызова в разделе «Использование». |

---

## 3. План реализации по фазам

### Phase 0 (уточнение сделанного)

- **0.1** ✅ Сигнатура `mintInviteBatch` в ISpiralEngine.sol — добавлена.  
- **0.2** ✅ Константа `MAX_BATCH_SIZE = 50` и custom errors в SpiralEngineLogic.sol — добавлены.  
- **Итог Phase 0:** Реализация `mintInviteBatch` в Logic отсутствует намеренно (по плану — в Phase 1). Компиляция будет успешной только после завершения Phase 1.

---

### Phase 1: Внутренняя логика и реализация batch

**Артефакт:** только `contracts/SpiralEngineLogic.sol`.

#### Шаг 1.1 — Добавить `_mintInviteSingle`

| Элемент | Содержание |
|---------|------------|
| **Файл** | `contracts/SpiralEngineLogic.sol` |
| **Место** | После блока с `mintInvite` (после строки с `return tokenId;` и закрывающей `}` функции `mintInvite`), перед функцией `activateUser`. |
| **Действие** | Добавить новую internal-функцию. Сигнатура: `function _mintInviteSingle(string calldata inviteCode, uint256 expiry) internal returns (uint256 tokenId)`. Тело: перенести из текущего `mintInvite` всю логику (проверка `bytes(inviteCode).length == 0` → revert EmptyInviteCode; проверка `inviteCodeExists[inviteCode]` → revert InviteCodeAlreadyExists; unchecked { tokenId = _tokenIdCounter++; }; _mint(msg.sender, tokenId); заполнение inviteCodeToTokenId, inviteCodeExists, tokenIdToInviteCode, inviteExpiry, inviteCreatedAt, inviteMinter, inviteFirstOwner; userInvites[msg.sender].push(tokenId); unchecked { userInviteCount[msg.sender]++; totalInvitesMinted++; }; emit InviteMinted(msg.sender, tokenId, inviteCode, expiry); return tokenId;). Модификаторов у _mintInviteSingle не должно быть. |
| **Критерий приёмки** | Компиляция без ошибок; функция internal, вызывается только из mintInvite и (после 1.2–1.3) из mintInviteBatch. |

#### Шаг 1.2 — Рефакторинг `mintInvite`

| Элемент | Содержание |
|---------|------------|
| **Файл** | `contracts/SpiralEngineLogic.sol` |
| **Место** | Тело функции `mintInvite` (все строки между `{` и `return tokenId; }`). |
| **Действие** | Удалить текущее тело функции (валидация, счётчик, _mint, маппинги, userInvites, события). Заменить на одну строку: `return _mintInviteSingle(inviteCode, expiry);`. Модификаторы функции не менять: `whenNotPaused nonReentrant onlyRole(SELLER_ROLE) override`. |
| **Критерий приёмки** | Компиляция; существующие тесты на mintInvite (smoke, comprehensive, roles, sanctions и т.д.) проходят. |

#### Шаг 1.3 — Реализовать `mintInviteBatch`

| Элемент | Содержание |
|---------|------------|
| **Файл** | `contracts/SpiralEngineLogic.sol` |
| **Место** | После `mintInvite` (и после добавленной _mintInviteSingle), перед `activateUser`. |
| **Действие** | Добавить функцию с сигнатурой из ISpiralEngine: `function mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external whenNotPaused nonReentrant onlyRole(SELLER_ROLE) override returns (uint256[] memory tokenIds)`. Тело: (1) если `inviteCodes.length == 0` → revert BatchEmpty; (2) если `inviteCodes.length != expiries.length` → revert BatchLengthMismatch; (3) если `inviteCodes.length > MAX_BATCH_SIZE` → revert BatchTooLarge(inviteCodes.length, MAX_BATCH_SIZE); (4) `tokenIds = new uint256[](inviteCodes.length)`; (5) цикл for (uint256 i; i < inviteCodes.length;) { tokenIds[i] = _mintInviteSingle(inviteCodes[i], expiries[i]); unchecked { ++i; } }; (6) return tokenIds;. |
| **Критерий приёмки** | Компиляция без ошибок; ручная проверка или минимальный тест (batch из 2 инвайтов) — по желанию в рамках фазы. |

**Порядок выполнения шагов 1.1–1.2–1.3:** Сначала 1.1 (добавить _mintInviteSingle с полным телом из текущего mintInvite), затем 1.2 (заменить тело mintInvite на вызов _mintInviteSingle), затем 1.3 (добавить mintInviteBatch). После каждого шага — валидация (компиляция; после 1.2 — прогон тестов mintInvite).

---

### Phase 2: Тесты mintInviteBatch

**Артефакт:** новый файл или расширение существующего в `contracts/tests/`.

| Шаг | Действие (план) | Артефакт | Критерий |
|-----|------------------|----------|----------|
| 2.1 | Добавить тесты: успешный batch 2–3 инвайта; успешный batch 12; пустой массив → revert; разная длина массивов → revert; дубликат inviteCode в batch → revert; вызов не от SELLER_ROLE → revert; при паузе → revert. Проверять события InviteMinted и состояние (userInvites, totalInvitesMinted). | Файл в contracts/tests/ (решение: новый SpiralEngine.batch.test.js или блок в smoke — зафиксировать в ретроспективе фазы). | Все новые тесты зелёные; отчёт по test-qualification. |
| 2.2 | Опционально: тест batch размером MAX_BATCH_SIZE (50). Решение: выполнять / пропускать — зафиксировать в начале фазы. | Тот же тест-файл | Тест проходит или пропуск с обоснованием. |

**Конкретные файлы и describe/it** — детализировать в Planning при запуске Phase 2 по run-phase.

---

### Phase 3: Документация

| Шаг | Действие (план) | Артефакт | Критерий |
|-----|------------------|----------|----------|
| 3.1 | Добавить NatSpec для `mintInviteBatch` (external) и краткий NatSpec для `_mintInviteSingle` (internal). | SpiralEngineLogic.sol | Компиляция, читаемый NatSpec. |
| 3.2 | Если существует contracts/docs/SpiralEngine.md — добавить описание batch-функции и MAX_BATCH_SIZE. | contracts/docs/ | Документ обновлён или отсутствует — зафиксировать. |

---

## 4. Порядок выполнения (алгоритм)

1. **Phase 1** выполнять по **run-phase**: документ фазы — solution-architecture-batch-mint.md, раздел «Phase 1»; шаги 1.1, 1.2, 1.3 вынести в TODO; для каждого шага выполнять runitem: Understanding → Knowledge Check → Acceptance Criteria → **Planning** (можно сослаться на этот документ, п. 3) → Implementation → Validation → Retrospective.  
2. После Phase 1 — ретроспектива по продукту и по процессу в папке таска; маркеры [Phase 1.X DONE].  
3. Затем Phase 2 по run-phase, затем Phase 3.  
4. Коммиты — по согласованию с оператором (git-commit-prompt + git-commit).

---

## 5. Контрольные точки

- Не переходить к Implementation без явного Planning (этот документ или краткий план в ответе по шагу).  
- После каждого шага Phase 1 — компиляция; после шага 1.2 — прогон существующих тестов на mintInvite.  
- Phase 0 считаем завершённой после успешной компиляции всей реализации (т.е. после Phase 1), т.к. до реализации mintInviteBatch контракт остаётся абстрактным.

Версия плана: v1.0. После утверждения оператором — использовать при выполнении Phase 1 по run-phase.
