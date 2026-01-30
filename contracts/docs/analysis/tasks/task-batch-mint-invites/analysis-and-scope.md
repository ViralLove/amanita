# Этап 1: Анализ и рамки — task-batch-mint-invites

**Дата:** 2026-01-30  
**Метод:** @.cursor/commands/run-analysis.md (только факты из кода)  
**Документ постановки:** task-implement-batch-mint-invites.md

---

## 1. Проверка фактов из постановки по коду

### 1.1 Интерфейс ISpiralEngine — только одиночный mintInvite

**Файл:** `contracts/interfaces/ISpiralEngine.sol`  
**Строки:** 136–146 (факт: 142–146 — сигнатура)

```solidity
function mintInvite(
    string memory inviteCode,
    uint256 expiry
) external returns (uint256 tokenId);
```

**Подтверждено:** в интерфейсе нет `mintInviteBatch`. Публичный API — только один инвайт за вызов.

---

### 1.2 Реализация SpiralEngineLogic — одна tx = один инвайт

**Файл:** `contracts/SpiralEngineLogic.sol`  
**Строки:** 294–339

- Сигнатура: `function mintInvite(string calldata inviteCode, uint256 expiry) external whenNotPaused nonReentrant onlyRole(SELLER_ROLE) override returns (uint256)`.
- Проверки: `EmptyInviteCode`, `InviteCodeAlreadyExists` (custom errors).
- Логика: `_tokenIdCounter++`, `_mint(msg.sender, tokenId)`, запись в `inviteCodeToTokenId`, `inviteCodeExists`, `tokenIdToInviteCode`, `inviteExpiry`, `inviteCreatedAt`, `inviteMinter`, `inviteFirstOwner`, `userInvites[msg.sender].push(tokenId)`, `userInviteCount`, `totalInvitesMinted`, `emit InviteMinted(...)`.
- Модификаторы: `whenNotPaused`, `nonReentrant`, `onlyRole(SELLER_ROLE)`, `override`.

**Подтверждено:** вся логика инвайта сосредоточена в одной функции; дублирования состояния между вызовами нет; batch можно реализовать циклом по той же логике (один `nonReentrant` на всю batch).

---

### 1.3 Использование в scripts

**Файл:** `scripts/lib/actions/InviteActions.js`  
**Строки:** 674–682 (цикл), 680 — вызов

- Цикл: `for (let j = 0; j < invites.length; j++)` (invites.length = 12).
- Вызов: `currentSpiralEngineWithSigner.mintInvite(invite, expiry, { nonce: nonce++, ... })`.
- Загрузка контракта: `this.contractManager.loadUUPSContract('SpiralEngine')` (стр. 373, 596 и др.).

**Подтверждено:** скрипт делает 12 отдельных транзакций; после появления `mintInviteBatch` вызов batch — отдельная задача (вне scope этого таска).

**Файл:** `scripts/lib/upload_utils.js` стр. 128: `'SpiralEngine': 'SpiralEngineLogic'` — при загрузке «SpiralEngine» используется ABI SpiralEngineLogic. Значит, деплой — UUPS (Proxy + SpiralEngineLogic).

---

### 1.4 SpiralEngine.sol (standalone) vs UUPS

**Файл:** `contracts/SpiralEngine.sol` — отдельный контракт (ERC721, AccessControl, не UUPS), свой `mintInvite` на стр. 156.

В scripts везде используется `loadUUPSContract('SpiralEngine')` → Proxy + Logic. Standalone `SpiralEngine.sol` в деплое не участвует (legacy/альтернативный путь).

**Вывод:** в scope таска — только **ISpiralEngine** и **SpiralEngineLogic**. SpiralEngine.sol в постановке указан как «если экспортирует функции» — опционально; для текущего деплоя не обязательно.

---

### 1.5 Тесты контракта

- `contracts/tests/SpiralEngine.UUPS.smoke.test.js` — вызывает `mintInvite`, проверяет `InviteMinted`, EmptyInviteCode, InviteCodeAlreadyExists, pause, reentrancy, upgrade, gas.
- `contracts/tests/SpiralEngine.UUPS.comprehensive.test.js` — pause-блокировка `mintInvite`.
- Других тестов с `mintInvite` в contracts/tests несколько (roles, integration, circles, sanctions, upgrade, basic).

**Подтверждено:** есть эталон тестирования одиночного `mintInvite`; для batch нужен новый набор кейсов по AC (успех, пустой массив, разная длина, дубликат в batch, роль, пауза).

---

## 2. Gap (чего нет, что нужно сделать)

| Элемент | Статус в коде | Нужно |
|--------|----------------|--------|
| `mintInviteBatch` в ISpiralEngine | Нет | Добавить сигнатуру `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds)` |
| `mintInviteBatch` в SpiralEngineLogic | Нет | Реализовать с теми же проверками и модификаторами, что у `mintInvite`; лимит длины (например ≤ 50) |
| Внутренняя функция _mintInviteSingle | Нет (логика только в mintInvite) | Опционально: вынести общую логику в _mintInviteSingle и вызывать из mintInvite и из цикла batch |
| MAX_BATCH_SIZE | Нет | Ввести константу (например 50), проверять в mintInviteBatch |
| SpiralEngine.sol (standalone) | Есть свой mintInvite | Постановка: «если экспортирует» — опционально; в приоритете Logic + интерфейс |
| Тесты mintInviteBatch | Нет | Добавить: успешный batch, пустой массив, разная длина, дубликат в batch, не SELLER_ROLE, пауза |

---

## 3. Границы задачи (scope)

- **В scope:** ISpiralEngine.sol, SpiralEngineLogic.sol, тесты контракта (contracts/tests) на `mintInviteBatch`.
- **Вне scope:** вызов batch из scripts (InviteActions.js, Action 777) — отдельная задача.

---

## 4. Итог этапа 1

- Факты из постановки проверены по коду; расхождений нет.
- Gap зафиксирован: нет batch-функции в интерфейсе и Logic, нет тестов и лимита размера batch.
- Готов переходить к **Этапу 2: Решения до кода** (decision-points: сигнатура, один expiry на batch vs массив expiries, MAX_BATCH_SIZE, нужна ли _mintInviteSingle).

Останавливаюсь для фидбека оператора перед этапом 2.
