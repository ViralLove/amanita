# Task: implement — batch mint инвайтов в SpiralEngine (одна tx на N инвайтов)

**Идентификатор:** task-batch-mint-invites  
**Фокус:** contracts/ (SpiralEngine)  
**Контекст:** RPC-надежность Action 777; 12 отдельных tx при минтинге инвайтов повышают риск потери tx при переключении RPC. Batch в контракте — одна tx на 12 инвайтов.  
**Дата анализа:** 2026-01-30  
**Методология:** @docs/methodology/task-standard.md, @.cursor/commands/run-analysis.md (analysis.mdc)

---

## Метаданные

| Поле | Значение |
|------|----------|
| **Приоритет** | P1 |
| **Сложность** | M |
| **Оценка времени** | 0.5–1 день |
| **Зависимости** | Нет (контракт уже UUPS, storage layout известен) |
| **Тэги** | spiral-engine, invites, batch-mint, gas, rpc-reliability |
| **Статус** | draft |

**Границы задачи:** В scope только контракт (SpiralEngineLogic, интерфейс, тесты контракта). Вызов batch из scripts (InviteActions.js, Action 777) — отдельная задача/фаза.

---

## 1. Цель (Purpose)

Добавить в SpiralEngine функцию **batch-минта инвайтов**: одна транзакция создаёт несколько инвайтов (например, 12) с теми же гарантиями, что и одиночный `mintInvite` (валидация, события, роли, пауза, reentrancy).

**Почему это важно (риск):** Сейчас Action 777 шлёт 12 отдельных tx (`mintInvite` в цикле). При rate limit или переключении RPC часть tx может не попасть в сеть (receipt null на всех RPC), из-за чего «застревает» цепочка nonce. Одна batch-tx устраняет эту проблему для одной серии инвайтов и снижает нагрузку на RPC.

**Что НЕ входит в scope:** Изменение скриптов/InviteActions (вызов новой batch-функции вместо цикла) — отдельная задача.

---

## 2. Факты из кода (Code Facts / SSOT)

### 2.1 Интерфейс: только одиночный mintInvite

- **Файл:** `contracts/interfaces/ISpiralEngine.sol`
  - Строки 142–146:
    ```solidity
    function mintInvite(
        string memory inviteCode,
        uint256 expiry
    ) external returns (uint256 tokenId);
    ```
  - **Факт:** Публичный API содержит только минт одного инвайта за вызов.

### 2.2 Реализация: одна tx = один инвайт

- **Файл:** `contracts/SpiralEngineLogic.sol`
  - Строки 294–340: `function mintInvite(string calldata inviteCode, uint256 expiry) external … returns (uint256)`:
    - Проверки: `EmptyInviteCode`, `InviteCodeAlreadyExists`
    - Инкремент `_tokenIdCounter`, `_mint(msg.sender, tokenId)`
    - Запись: `inviteCodeToTokenId`, `inviteCodeExists`, `tokenIdToInviteCode`, `inviteExpiry`, `inviteCreatedAt`, `inviteMinter`, `inviteFirstOwner`
    - Обновление: `userInvites[msg.sender].push(tokenId)`, `userInviteCount`, `totalInvitesMinted`
    - Событие: `InviteMinted(msg.sender, tokenId, inviteCode, expiry)`
  - **Факт:** Вся логика инвайта изолирована в одной функции; повторение по массивам даёт batch без изменения контрактного state-модели.

### 2.3 Модификаторы и защита

- **Файл:** `contracts/SpiralEngineLogic.sol`
  - `mintInvite` использует: `whenNotPaused`, `nonReentrant`, `onlyRole(SELLER_ROLE)`, `override`
  - **Факт:** Batch-функция должна использовать те же модификаторы (один вход в контракт, один nonReentrant на всю batch).

### 2.4 Использование в scripts

- **Файл:** `scripts/lib/actions/InviteActions.js`
  - Строки 674–682: цикл по `invites.length` (12), каждый вызов `currentSpiralEngineWithSigner.mintInvite(invite, expiry, { nonce: nonce++, ... })`
  - **Факт:** Скрипт ожидает возможность вызвать минт нескольких инвайтов; после появления batch можно вызывать одну tx (вызов batch из scripts — вне этой задачи).

---

## 3. Gap / Проблема (Gap Analysis)

- В контракте **нет** функции, принимающей массивы `inviteCodes[]` и `expiries[]` и выполняющей минт нескольких инвайтов в одной транзакции.
- Следствие: скрипты вынуждены слать N транзакций (N=12), что увеличивает зависимость от RPC и риск потери части tx при переключении нод.

---

## 4. AC/DoD (Acceptance Criteria / Definition of Done)

- [ ] **(P0)** В `ISpiralEngine` объявлена функция `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds)` (или эквивалент с одним общим `expiry` для всех — см. решение).
- [ ] **(P0)** В `SpiralEngineLogic` реализована эта функция с теми же проверками на инвайт, что и в `mintInvite` (не пустой код, код не существует), с теми же модификаторами (`whenNotPaused`, `nonReentrant`, `onlyRole(SELLER_ROLE)`).
- [ ] **(P0)** Для каждого элемента массивов вызывается по сути та же логика, что и в `mintInvite` (счётчик, _mint, маппинги, userInvites, события), без дублирования состояния между вызовами (один reentrancy guard на всю batch).
- [ ] **(P0)** Требование: `inviteCodes.length == expiries.length` и `inviteCodes.length > 0` (и при необходимости верхняя граница, например ≤ 50, чтобы уложиться в лимит газа).
- [ ] **(P1)** В `SpiralEngine.sol` (фасад, если используется) добавлена соответствующая сигнатура/делегирование.
- [ ] **(P1)** Добавлены unit-тесты контракта: успешный batch из нескольких инвайтов; пустой массив; несовпадение длин массивов; дубликат inviteCode внутри batch; вызов не от SELLER_ROLE; при паузе batch не выполняется.
- [ ] **(P2)** Документация (NatSpec) и при необходимости `contracts/docs/` обновлены с описанием batch-функции и лимитов.

---

## 5. Где менять код (Code Changes Location)

| Файл | Изменения |
|------|------------|
| `contracts/interfaces/ISpiralEngine.sol` | Добавить сигнатуру `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds);` |
| `contracts/SpiralEngineLogic.sol` | Добавить реализацию `mintInviteBatch`: цикл по массивам, вызов общей логики минта одного инвайта (внутренняя функция или inline), эмит событий, возврат `tokenIds[]`. Не добавлять новые state-переменные; при добавлении — уменьшать `__gap`. |
| `contracts/SpiralEngine.sol` | Если есть фасад с перечислением функций — добавить `mintInviteBatch` (override/делегирование в Logic). |
| `contracts/tests/` | Новый или существующий тест-файл для SpiralEngine: тесты на `mintInviteBatch` (успех, валидация массивов, роли, пауза, дубликаты). |

---

## 6. План выполнения (Execution Plan)

1. **Интерфейс**  
   В `ISpiralEngine.sol` добавить `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds);`. Проверить компиляцию.

2. **Внутренняя логика одного инвайта (опционально)**  
   В `SpiralEngineLogic.sol` при необходимости вынести общую часть `mintInvite` во внутреннюю функцию `_mintInviteSingle(string calldata inviteCode, uint256 expiry) returns (uint256 tokenId)` и вызывать её из `mintInvite` и из цикла `mintInviteBatch`, чтобы не дублировать код. Альтернатива: inline-логика в цикле batch.

3. **Реализация mintInviteBatch**  
   В `SpiralEngineLogic.sol` реализовать `mintInviteBatch`: проверка `inviteCodes.length == expiries.length && inviteCodes.length > 0` (и при необходимости `inviteCodes.length <= MAX_BATCH_SIZE`). Цикл: для каждого индекса те же проверки и запись, что в `mintInvite`; сбор `tokenIds[]`; возврат массива. Модификаторы: `whenNotPaused`, `nonReentrant`, `onlyRole(SELLER_ROLE)`, `override`.

4. **Фасад SpiralEngine.sol**  
   Если контракт `SpiralEngine.sol` экспортирует функции — добавить `mintInviteBatch` с делегированием в Logic.

5. **Тесты**  
   Написать тесты: batch из 2–3 инвайтов; batch из 12; пустой массив (revert); разная длина массивов (revert); дубликат inviteCode в одном batch (revert); вызов не от SELLER (revert); при паузе (revert). Проверить события и состояние (userInvites, totalInvitesMinted).

6. **Документация**  
   Обновить NatSpec и при необходимости `contracts/docs/` (описание batch, лимит размера batch).

---

## 7. Команды проверки (Verification Commands)

```bash
# Сборка контрактов
cd contracts && npx hardhat compile

# Запуск тестов SpiralEngine (подставить актуальный тест-файл)
cd contracts && npx hardhat test tests/SpiralEngine*.test.js --grep "batch\|mintInviteBatch"

# При наличии smoke/qualification
cd contracts && npx hardhat test tests/SpiralEngine.UUPS.smoke.test.js
```

---

## 8. Решение / архитектура (Solution Architecture)

- **Сигнатура:** `mintInviteBatch(string[] calldata inviteCodes, uint256[] calldata expiries) external returns (uint256[] memory tokenIds)`.
- **Валидация:** `inviteCodes.length == expiries.length`, `inviteCodes.length > 0`, при необходимости `inviteCodes.length <= MAX_BATCH_SIZE` (например 50; 12 достаточно для текущего Action 777).
- **Реализация:** Один вход в контракт (один `nonReentrant`), цикл по индексу; для каждого индекса — те же проверки и записи, что в `mintInvite`; эмит `InviteMinted` на каждый инвайт; возврат массива `tokenIds`. Дублирование кода убрать через внутреннюю `_mintInviteSingle` или общий блок.
- **Обратная совместимость:** `mintInvite` остаётся без изменений; существующие вызовы и скрипты не ломаются. Вызов batch из InviteActions — отдельная задача.

---

## 9. Риски и подводные камни (Risks & Pitfalls)

- **Газ:** Большая batch (например 50) может приближаться к лимиту блока. Ограничить `MAX_BATCH_SIZE` и покрыть тестом с максимальным размером.
- **Storage layout:** Не добавлять новые state-переменные в Logic без уменьшения `__gap`; batch не требует новых полей.
- **События:** Эмитить `InviteMinted` для каждого инвайта в batch, как в одиночном `mintInvite`, для совместимости с индексаторами и логами.
