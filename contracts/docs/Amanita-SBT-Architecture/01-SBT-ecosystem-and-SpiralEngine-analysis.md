# SBT-экосистема и связь с SpiralEngine — глубокий анализ реализации

**Версия:** 1.0  
**Дата:** 2025-01-30  
**Методика:** только факты из кода (run-analysis), без предположений в разделах SSOT.  
**Назначение:** точка входа для следующего диалога/исследования; продолжение концепта «наша система SBT и её реализация».

---

## Вводная: как я понимаю систему

В проекте Amanita реализованы **две связанные, но разные токенные линии**:

1. **SpiralEngine (Invite NFT)** — контракт инвайтов: минтинг и активация пользователей через коды приглашений. Токены инвайтов **soulbound** (не передаются, нет approve). Это ERC721 с кастомными ошибками `TransfersNotAllowed` и `ApprovalsNotAllowed`. SpiralEngine **не минтит** токены «души» в SoulboundCore; он только при необходимости **читает** уровень/репутацию/DID через контракт SoulIdentity.

2. **SBT-экосистема «души»** — отдельный набор контрактов: **SoulboundCore** (ядро SBT по EIP-5192), **SoulMetadata** (метаданные токенов), **SoulIdentity** (мост + DID + уровень/репутация), **SoulRecovery** (восстановление доступа через guardian). Токены здесь — «души» (Soul), минтинг только через SoulboundCore (например, `mintSoul(to)`). Связь с SpiralEngine: только **чтение** (getSoulLevel, getSoulReputation, getSoulIdentity и т.д.) через поле `soulIdentity` в SpiralEngineLogic.

**Примечание о названиях:** В коде нет контракта с именем **SoulCode**. Ядро SBT — контракт **SoulboundCore**; если под «SoulCode» подразумевалось другое имя для этого ядра или для идентификатора/типа токена — в данном документе под «ядром SBT» везде имеется в виду **SoulboundCore**.

Этот документ занимается **исследованием текущей реализации SBT-экосистемы и её связи с SpiralEngine**: что где реализовано, какие контракты за что отвечают, где заглушки и опциональные интеграции (Recovery, Integration). Продолжение работы (тесты, доработка recovery/DID и т.д.) может опираться на этот анализ как на единую точку истины по коду.

---

## 1. SoulboundCore — ядро SBT

**Файл:** `contracts/SoulboundCore.sol`

**Роль:** минимальная ERC721-совместимая реализация Soulbound Token (EIP-5192): токены «души», всегда заблокированы, без передачи и без approve.

**Факты из кода:**

- **Хранилище:** `_owners`, `_balances`, `_nextTokenId`, `_totalSupply`; опциональные адреса: `_metadataContract`, `_recoveryContract`, `_integrationContract`.
- **Минтинг:** только владелец контракта: `mintSoul(address to)`, `mintSoulBatch(address to, uint256 amount)`. При минте эмитится `SoulMinted` и `Locked`; при наличии `_integrationContract` вызывается `ISoulIntegration(_integrationContract).notifySoulCreated(tokenId, owner)`.
- **Трансфер и approve:** все варианты `transferFrom` / `safeTransferFrom` и `approve` / `setApprovalForAll` — **revert** с сообщением `"SBT: transfer not allowed"` или `"SBT: approval not allowed"`. `getApproved` всегда `address(0)`, `isApprovedForAll` всегда `false`. `locked(uint256)` всегда `true`.
- **Восстановление:** единственный способ сменить владельца — вызов `executeRecovery(uint256 tokenId, address newOwner)`. Разрешён **только** с адреса `_recoveryContract`. Проверяется `ISoulRecovery(_recoveryContract).canConfirmRecovery(tokenId)`. Внутри — перенос владения и при необходимости вызов `ISoulIntegration(_integrationContract).notifySoulRecovered(tokenId, oldOwner, newOwner)`.
- **Метаданные:** `tokenURI(tokenId)` при наличии `_metadataContract` запрашивает URI у `ISoulMetadata(_metadataContract).getTokenURI(tokenId)`; иначе — дефолтный JSON.
- **Управление контрактами:** только owner: `setMetadataContract`, `setRecoveryContract`, `setIntegrationContract` (и соответствующие getters).
- **Burn:** `burnSoul(tokenId)` — разрешён владельцу токена или владельцу контракта.

**Связи:** SoulboundCore не знает о SpiralEngine. Его вызывают SoulMetadata, SoulRecovery (и опционально SoulIntegration). SoulIdentity обращается к нему через интерфейс (balanceOf, ownerOf, getTotalSupply, getNextTokenId, exists).

---

## 2. SoulMetadata — метаданные SBT

**Файл:** `contracts/SoulMetadata.sol`

**Роль:** хранение и выдача метаданных для токенов SoulboundCore (тип, версия, атрибуты, IPFS).

**Факты из кода:**

- **Зависимость:** в конструкторе принимает адрес SoulboundCore; хранится как `immutable soulboundCore`.
- **Структура:** `SoulData { metadataType, version, attributes, ipfsHash }`; маппинг `tokenId → SoulData`; маппинг инициализации.
- **Доступ:** инициализация/обновление — только владелец токена или владелец SoulboundCore (`onlyTokenOwnerOrContractOwner`). Проверка существования токена — `tokenExists` через `soulboundCore.exists(tokenId)`.
- **Функции:** `initializeMetadata`, `updateMetadata`, `getMetadata`, `getTokenURI`, `isInitialized`; пакетное обновление `updateMetadataBatch`.
- **Связи:** SoulIdentity читает и пишет метаданные через SoulMetadata (getMetadata, updateMetadata, initializeMetadata) для уровня, репутации и атрибутов. SoulboundCore запрашивает только `getTokenURI(tokenId)` для отображения URI.

---

## 3. SoulIdentity — мост к SBT и DID

**Файл:** `contracts/SoulIdentity.sol`

**Роль:** мост между «внешним миром» (в т.ч. SpiralEngine) и экосистемой SoulboundCore + SoulMetadata: уровень души, репутация, DID, профиль. Реализует интерфейс ISoulIdentity (в т.ч. EIP-5192 view-методы); approve/transfer — заглушки с revert.

**Факты из кода:**

- **Зависимости:** конструктор принимает адреса SoulboundCore и SoulMetadata; роли: `DEFAULT_ADMIN_ROLE`, `SPIRAL_ENGINE_ROLE`.
- **Поиск токена пользователя:** `_getUserTokenId(address user)` — перебор по SoulboundCore (balanceOf, getTotalSupply, ownerOf(i) до 1000), возвращает первый найденный tokenId или 0.
- **Уровень и репутация:** `getSoulLevel` / `getSoulReputation` — через SoulMetadata.getMetadata(tokenId), парсинг атрибутов. В коде парсинг JSON — заглушки: `_parseLevel` и `_parseReputation` возвращают 1 и 100. Обновление — `updateSoulLevel` / `updateSoulReputation` только с ролью `SPIRAL_ENGINE_ROLE`, запись через SoulMetadata.
- **DID:** `linkSoulIdentity(string did)` — требует у отправителя наличие SBT (tokenId > 0); добавляет запись в `userIdentities[msg.sender]` (тип `"did:spiral"`). `getSoulIdentity(user)` возвращает значение основной идентичности; `unlinkSoulIdentity` удаляет did:spiral записи.
- **Guardians и recovery:** `addTrustedGuardian`, `removeTrustedGuardian`, `getTrustedGuardians`, `isTrustedGuardian`, `initiateRecovery`, `completeRecovery`, `isRecoveryInProgress` — **заглушки** (пустые массивы, false, пустые вызовы с комментарием «TODO: Делегировать к SoulRecovery»). Полный профиль `getSoulProfile` возвращает guardians = `new address[](0)`.
- **Временные ключи:** `createTemporaryKey`, `getTemporaryKey`, `isTemporaryKeyValid` — заглушки (возврат address(0), false).
- **ERC5192 / approve / transfer:** `locked(uint256)` всегда true; `approve` / `setApprovalForAll` — revert `"SoulIdentity: soulbound tokens cannot be approved"`; `getApproved` / `isApprovedForAll` — 0 и false.
- **SBT metadata:** `getSBTMetadata`, `getSBTVersion`, `getSBTType`, `getSBTAttributes`, `isSBT` — делегирование к SoulMetadata или SoulboundCore.exists. `updateSBTMetadata` / `updateSBTVersion` — заглушки (TODO).

**Связи:** SpiralEngineLogic хранит адрес SoulIdentity и вызывает только view и вызовы, не меняющие владение: getSoulLevel, getSoulReputation, getSoulIdentity, getSoulVerificationLevel, getSoulProfile. SpiralEngine **не минтит** души и **не вызывает** mintSoul на SoulboundCore — минтинг души в тестах делается явно через SoulboundCore от имени owner.

---

## 4. SoulRecovery — восстановление доступа к SBT

**Файл:** `contracts/SoulRecovery.sol`

**Роль:** единственный контракт, который по смыслу может **менять владельца** токена SoulboundCore: через guardian и двухфазный процесс (initiate → confirm после задержки).

**Факты из кода:**

- **Зависимость:** конструктор принимает только адрес SoulboundCore (`immutable soulboundCore`). Связь «SoulboundCore знает SoulRecovery» задаётся **снаружи**: владелец SoulboundCore вызывает `setRecoveryContract(soulRecoveryAddress)`.
- **Модель:** один guardian на один tokenId. Структуры: `GuardianInfo { guardian, setTimestamp, isActive }`, `RecoveryInfo { newOwner, guardian, initiatedAt, isActive }`. Константы: `GUARDIAN_DELAY = 7 days`, `RECOVERY_DELAY = 24 hours`.
- **Установка guardian:** `setGuardian(uint256 tokenId, address guardian)` — только владелец токена (`onlyTokenOwner`). Ограничения: guardian не 0, не сам отправитель, не текущий владелец токена.
- **Инициация восстановления:** `initiateRecovery(tokenId, newOwner)` — только активный guardian этого tokenId (`onlyGuardian`). Условия: newOwner не 0 и не текущий владелец; нет активного recovery; прошло не менее GUARDIAN_DELAY с момента setGuardian.
- **Подтверждение восстановления:** `confirmRecovery(tokenId)` — только guardian, инициировавший recovery; не раньше чем через RECOVERY_DELAY после initiate. Внутри вызывается `soulboundCore.executeRecovery(tokenId, newOwner)`; затем очистка `_recoveries[tokenId]`.
- **Отмена:** `cancelRecovery(tokenId)` — только владелец токена; сбрасывает активный recovery.
- **View:** `getGuardianInfo`, `getGuardian`, `hasActiveGuardian`, `getRecoveryInfo`, `isRecoveryActive`, `canConfirmRecovery`, `getRecoveryTimeLeft`.

**Связи:** SoulboundCore выполняет смену владельца только через `executeRecovery`, вызываемый из SoulRecovery. SoulIdentity **не вызывает** SoulRecovery: методы guardians/recovery в SoulIdentity — заглушки, интеграция «SoulIdentity ↔ SoulRecovery» не реализована. В текущих тестах SBT (SpiralEngine.sbt.test.js) SoulRecovery не деплоится и не регистрируется в SoulboundCore.

---

## 5. SpiralEngine и SpiralEngineLogic — инвайты и чтение души

**Файлы:** `contracts/SpiralEngineLogic.sol`, `contracts/SpiralEngine.sol`, `contracts/SpiralEngineProxy.sol`

**Роль:** бизнес-логика инвайтов (mint invite, activate user) и **только чтение** данных души через SoulIdentity. Собственные токены — NFT инвайтов (ERC721), soulbound (revert на transfer/approve).

**Факты из кода:**

- **Два типа токенов в системе:**
  - **Инвайт-NFT** (SpiralEngineLogic): свои `_mint`, `inviteCodeToTokenId`, `tokenIdToInviteCode`, `inviteExpiry`, `isInviteUsed`, `usedInviteByUser` и т.д. Владелец инвайта — тот, кто его заминтил или кому он передан при activateUser (новые 12 инвайтов минятся на `user`).
  - **Души (Soul)** — не принадлежат SpiralEngine; живут в SoulboundCore. SpiralEngine о них только **читает** через SoulIdentity.
- **SoulIdentity:** одно поле `ISoulIdentity public soulIdentity`; установка только с `ADMIN_ROLE`: `setSoulIdentity(address)`. Если soulIdentity == 0, все view (getSoulLevel, getSoulReputation, getSoulIdentity, getSoulVerificationLevel, getSoulProfile) revert с `SoulIdentityNotSet()`.
- **SBT-поведение собственных токенов:** `locked(uint256)` всегда true; `approve` / `setApprovalForAll` → `ApprovalsNotAllowed()`; `transferFrom` / safeTransferFrom → `TransfersNotAllowed()`.
- **activateUser:** не вызывает SoulIdentity и не минтит SoulboundCore; только использует инвайт (isInviteUsed, usedInviteByUser), минтит 12 новых инвайт-NFT пользователю и обновляет маппинги/счётчики.

**Связи:** SpiralEngine → SoulIdentity (только вызовы чтения). SoulIdentity → SoulboundCore (ownerOf, balanceOf, exists, getTotalSupply, getNextTokenId) и SoulMetadata (getMetadata, updateMetadata, initializeMetadata). Цепочка минтинга души в проде/тестах задаётся вне SpiralEngine (например, скрипт или отдельный контракт вызывает SoulboundCore.mintSoul).

---

## 6. SoulIntegration (опционально)

**Файл:** `contracts/SoulIntegration.sol` (в репозитории есть)

**Роль:** интерфейс в SoulboundCore для уведомлений о создании души и о восстановлении. SoulboundCore вызывает `notifySoulCreated(tokenId, owner)` при минте и `notifySoulRecovered(tokenId, oldOwner, newOwner)` при executeRecovery, если `_integrationContract` установлен. Реализация и использование — за пределами данного разбора; для понимания SBT и SpiralEngine достаточно того, что это опциональный обратный вызов.

---

## 7. Сводная схема связей (факты из кода)

```
SpiralEngine (Logic)
  │
  ├── собственные NFT инвайтов (ERC721, soulbound: TransfersNotAllowed, ApprovalsNotAllowed)
  │
  └── soulIdentity: ISoulIdentity
        │
        ├── getSoulLevel(user)     → SoulMetadata.getMetadata(tokenId), парсинг
        ├── getSoulReputation(user) → то же
        ├── getSoulIdentity(user)   → userIdentities[user]
        ├── getSoulProfile(user)    → level, reputation, identity, guardians=[] (stub)
        └── approve/transfer        → revert (SoulIdentity)

SoulIdentity
  │
  ├── soulboundCore: ISoulboundCore  → balanceOf, ownerOf, exists, getTotalSupply, getNextTokenId
  ├── soulMetadata: ISoulMetadata    → getMetadata, updateMetadata, initializeMetadata
  ├── addTrustedGuardian / recovery  → заглушки (не вызывают SoulRecovery)
  └── temporary keys                → заглушки

SoulboundCore
  │
  ├── _metadataContract   → getTokenURI (SoulMetadata)
  ├── _recoveryContract   → только executeRecovery(caller must be this)
  └── _integrationContract→ notifySoulCreated, notifySoulRecovered

SoulRecovery
  │
  └── soulboundCore.executeRecovery(tokenId, newOwner)  ← единственный способ смены владельца SBT
```

**Разделение ответственности:**

- **Кто минтит инвайты:** SpiralEngineLogic (mintInvite, activateUser).
- **Кто минтит души:** только SoulboundCore.mintSoul; вызывающий — owner контракта (в тестах — deployer).
- **Кто может перевести душу другому владельцу:** только через SoulRecovery.confirmRecovery → SoulboundCore.executeRecovery (при предварительно установленном setRecoveryContract).
- **Где живут DID и «профиль души»:** SoulIdentity (userIdentities, level/reputation через SoulMetadata).

---

## 8. Заглушки и незавершённые зоны (для продолжения исследования)

- SoulIdentity: addTrustedGuardian, removeTrustedGuardian, getTrustedGuardians, initiateRecovery, completeRecovery — не вызывают SoulRecovery; getSoulProfile возвращает пустой массив guardians.
- SoulIdentity: _parseLevel, _parseReputation — всегда 1 и 100; полноценный парсинг JSON не реализован.
- SoulIdentity: createTemporaryKey, getTemporaryKey, isTemporaryKeyValid — заглушки.
- SoulIdentity: updateSBTMetadata, updateSBTVersion — TODO.
- В тестах SBT (SpiralEngine.sbt.test.js) SoulRecovery не деплоится и не подключается к SoulboundCore; recovery-сценарии для deep-тестов пока помечены как smoke/TODO.

Документ можно использовать как продолжение концепта «наша реализация SBT» в следующем диалоге: уточнение сценариев, тесты, интеграция SoulRecovery в setup, или доработка DID/guardians/temporary keys.
