# Аудит: идентичность, DID, инвайт vs SBT, SoulboundCore, метаданные, избыточность и дыры

**Версия:** 1.0  
**Дата:** 2026-03-14  
**Методика:** run-analysis — только факты из кода; выводы по адекватности, ролям, избыточности и рискам.

---

## 1. Как создаётся идентичность и окно для интеграции с DID

### 1.1 Факты из кода

**Создание «души» (SBT):**

- `contracts/SoulboundCore.sol`: минтинг только владельцем контракта: `mintSoul(address to)`, `mintSoulBatch(address to, uint256 amount)` (строки 202, 222). SpiralEngine и SoulIdentity **не вызывают** mintSoul; в коде нет автоматического минта души при активации пользователя.
- Вывод: идентичность в смысле «наличие SBT» создаётся **вне** SpiralEngine — тем, у кого есть право owner на SoulboundCore (скрипт, бэкенд, отдельный контракт). Нет ончейн-связки «активация в SpiralEngine → минтинг души».

**Условие для DID:**

- `contracts/SoulIdentity.sol`:
  - `linkSoulIdentity(string did)` (стр. 246–266): требуется `_getUserTokenId(msg.sender) > 0`, иначе revert. DID привязывается к `msg.sender` в `userIdentities[msg.sender]` (тип `"did:spiral"`).
  - `linkExternalIdentity(user, identityType, identityValue, verified)` (стр. 165–204): только `SPIRAL_ENGINE_ROLE`; требуется `_getUserTokenId(user) > 0`. Запись в `userIdentities[user]`, поддержка типов `"did:spiral"`, `"did:polygon"` и др., верификация и `verifiedBy`.
- Вывод: **окно для интеграции с DID** — «есть SBT» (tokenId по владельцу в SoulboundCore). Два пути: (1) сам пользователь вызывает `linkSoulIdentity(did)` при наличии SBT; (2) оркестратор с `SPIRAL_ENGINE_ROLE` вызывает `linkExternalIdentity(user, ...)`.

**Где хранится идентичность (DID):**

- Только в SoulIdentity: `userIdentities[user]` (массив ExternalIdentity), `primaryIdentityIndex[user]`, `identityTypeToIndex[user][identityType]`. SoulboundCore и SoulMetadata **не хранят** DID; SoulMetadata хранит только тип метаданных, версию, атрибуты (JSON) и ipfsHash по tokenId.

### 1.2 Адекватность

- **Плюсы:** Чёткое условие «сначала SBT — потом DID»; разделение self-service (linkSoulIdentity) и доверенного ввода (linkExternalIdentity); несколько типов идентичностей и основная идентичность.
- **Дыра:** Нет ончейн-правила «когда минтить душу». Связь «активация в SpiralEngine → появление SBT» не зашита в контракты; возможна рассинхронизация (активированный пользователь без души или душа без активации). Для интеграций с DID важно явно зафиксировать процесс (например, оркестратор после activateUser вызывает mintSoul и при необходимости linkExternalIdentity) и/или рассмотреть автоматизацию (например, SoulIntegration или отдельный контракт по событию UserActivated).

---

## 2. Инвайт: роль SBT или отдельный контракт?

### 2.1 Факты из кода

**SpiralEngine (инвайт-NFT):**

- `contracts/SpiralEngineLogic.sol`: собственный ERC721 — свой `_mint`, `_tokenIdCounter`, маппинги инвайтов (`inviteCodeToTokenId`, `tokenIdToInviteCode`, `inviteExpiry`, `isInviteUsed`, `usedInviteByUser`, `userActivator`, `activatedBy` и т.д.). Токены инвайтов **soulbound**: `transferFrom`, `approve`, `setApprovalForAll` — revert с кастомными ошибками `TransfersNotAllowed`, `ApprovalsNotAllowed` (стр. 114–117, 802–817); `locked(uint256)` всегда true (стр. 792).
- Контракт **не** реализует EIP-5192 явно через один интерфейс «SBT», но поведение совпадает: нет передачи, нет approve.

**SoulboundCore (душа-SBT):**

- Отдельный контракт; ERC721 + EIP-5192; свои `_owners`, `_balances`, `mintSoul`/`burnSoul`; transfer/approve — revert с сообщениями `"SBT: transfer not allowed"` / `"SBT: approval not allowed"`.
- SpiralEngine **не минтит** в SoulboundCore и **не держит** токены SoulboundCore; только читает SoulIdentity (getSoulLevel, getSoulReputation, getSoulIdentity, getSoulProfile).

**Итог по коду:** инвайт и душа — **два отдельных контракта и два типа токенов**. Инвайт выполняет **поведенческую** роль SBT (soulbound), но не является токеном из SoulboundCore и не участвует в DID/level/reputation.

### 2.2 Оценка разделения

- **Разделение оправдано:**
  - Разная семантика: инвайт — «вход в граф и круг 12», душа — «идентичность, уровень, репутация, DID». Один адрес может быть активирован (иметь использованный инвайт и свои 12 инвайтов), но ещё не иметь души, или наоборот при ручном минте души.
  - Разные жизненные циклы: инвайты минятся при activateUser (12 новых на пользователя); душа — одна (или ограниченно) на адрес, минтится отдельно.
  - Меньше связности: SpiralEngine не зависит от деплоя SoulboundCore; можно использовать движок инвайтов без SBT-экосистемы (soulIdentity = 0).
- **Минус:** Два «soulbound»-источника (инвайт и душа); для внешних интеграций и документации нужно явно различать «invite NFT» и «soul SBT». Риск путаницы «инвайт = SBT» — стоит в документации чётко писать: инвайт — soulbound NFT движка; SBT души — SoulboundCore.

---

## 3. Роль SoulboundCore и организация хранения метаданных

### 3.1 SoulboundCore

**Факты из кода (`contracts/SoulboundCore.sol`):**

- **Роль:** единственный источник правды о **владении** токенами «души»: `_owners[tokenId]`, `_balances[owner]`, `_nextTokenId`, `_totalSupply`. Минтинг и сжигание только через этот контракт; смена владельца только через `executeRecovery` (вызов из SoulRecovery).
- **Метаданные:** не хранит атрибуты/тип/версию; только при наличии `_metadataContract` запрашивает `getTokenURI(tokenId)` у этого контракта (стр. 98–109). Иначе возвращает дефолтный JSON (стр. 410–418).
- **Связи:** опционально хранит адреса `_metadataContract`, `_recoveryContract`, `_integrationContract`; управление только owner контракта.

**Вывод:** SoulboundCore — ядро владения SBT (EIP-5192, non-transferable). Метаданные не в нём, а в отдельном контракте.

### 3.2 Хранение метаданных: SoulMetadata

**Факты из кода (`contracts/SoulMetadata.sol`):**

- **Структура на tokenId:** `SoulData { metadataType, version, attributes, ipfsHash }` (стр. 40–44). Маппинг `tokenId → SoulData`; маппинг инициализации.
- **Типы метаданных (по коду и комментариям):** `metadataType` — строка, в коде встречается значение `"identity"` (SoulIdentity при инициализации метаданных для level/reputation, стр. 130, 152). В комментарии указаны примеры: «identity», «achievement», «reputation» (стр. 41).
- **Атрибуты:** строка `attributes` — JSON; в SoulIdentity туда пишутся `level` и `reputation` (например `'{"level":1,"reputation":100}'`). Парсинг в SoulIdentity — заглушки (_parseLevel, _parseReputation возвращают 1 и 100).
- **Доступ на запись:** только владелец токена или владелец SoulboundCore (`onlyTokenOwnerOrContractOwner`: стр. 71–79). То есть вызовы `initializeMetadata` / `updateMetadata` допустимы от `soulboundCore.ownerOf(tokenId)` или от `soulboundCore.owner()`.
- **Кто реально пишет:** SoulIdentity вызывает `soulMetadata.updateMetadata(tokenId, ...)` и `soulMetadata.initializeMetadata(tokenId, "identity", ...)` (стр. 126, 130, 149, 152). При этом в SoulMetadata `msg.sender` — адрес SoulIdentity. Чтобы проверка прошла, должен выполняться `msg.sender == contractOwner`, т.е. **SoulboundCore.owner() должен быть равен адресу SoulIdentity** (или деплой должен быть устроен так, чтобы запись в SoulMetadata шла от владельца SoulboundCore). Иначе вызовы updateSoulLevel/updateSoulReputation приведут к revert в SoulMetadata.

**Вывод:** Метаданные организованы в одном контракте (SoulMetadata) по tokenId; типы — строка (identity/achievement/reputation и т.д.); уровень и репутация зашиты в JSON в `attributes`. Для работы SoulIdentity с метаданными нужна корректная настройка владельца SoulboundCore (например, owner = SoulIdentity).

---

## 4. Избыточность данных и контрактов

### 4.1 Дублирование и разделение данных

- **Владение SBT:** только SoulboundCore (`_owners`, `_balances`). Дублирования нет.
- **Level / reputation:** хранятся только в SoulMetadata в виде JSON в `attributes`; SoulIdentity читает их через getMetadata и пишет через updateMetadata/initializeMetadata. В SoulIdentity нет своего кэша level/reputation по пользователю — избыточности нет.
- **DID и внешние идентичности:** только в SoulIdentity (`userIdentities`, `primaryIdentityIndex`, `identityTypeToIndex`). SoulMetadata не хранит DID — разделение корректное: метаданные токена (тип, версия, атрибуты) в SoulMetadata; привязка адреса к внешним идентификаторам (DID) в SoulIdentity.
- **«Профиль» пользователя:** getSoulProfile в SoulIdentity собирает level, reputation, identity из разных источников (SoulMetadata через getSoulLevel/getSoulReputation, userIdentities); guardians пока заглушка (пустой массив). Единого «профиля» в одном хранилище нет — это агрегация, не дублирование.

**Возможная избыточность:**

- Два способа привязки DID: `linkSoulIdentity(did)` (self-service, тип `"did:spiral"`) и `linkExternalIdentity(user, "did:spiral", value, verified)`. Оба пишут в один массив `userIdentities`; типы могут пересекаться. Это не дублирование хранилища, но два API для одной сущности (legacy + расширенный) — стоит документировать, чтобы не плодить дубликаты записей по одному типу.

### 4.2 Избыточность контрактов

- SoulboundCore, SoulMetadata, SoulIdentity, SoulRecovery, SoulIntegration — роли разные: владение, метаданные токена, мост/DID/профиль, восстановление, уведомления. Объединять SoulMetadata и SoulIdentity в один контракт увеличило бы сложность и смешивало бы «данные токена» и «данные по адресу (DID)». Текущее разделение обосновано.
- SpiralEngine и SoulboundCore — два контракта с soulbound-токенами; как выше, семантика разная (инвайты vs души), объединение не рекомендуется.

---

## 5. Дыры архитектуры: удобство и безопасность

### 5.1 Удобство и целостность

- **Нет ончейн-связки «активация → душа»:** когда и кто минтит SBT, в контрактах не определено. Риск: активированные пользователи без души не могут привязать DID; возможна рассинхронизация с реестрами (ProductRegistry, ActivityRegistry), если те начнут проверять наличие души. Рекомендация: зафиксировать процесс (оркестратор/скрипт после activateUser вызывает mintSoul и при необходимости linkExternalIdentity) или ввести явный контракт/слой, реагирующий на активацию.
- **Поиск tokenId по пользователю:** `_getUserTokenId(user)` перебором по всем tokenId до min(totalSupply, 1000) (SoulIdentity.sol, стр. 307–321). При большом totalSupply газ растёт; при totalSupply > 1000 пользователь с единственным токеном с id > 1000 не будет найден (вернётся 0). Дыра: лимит 1000 и O(n) по газовой стоимости; для масштабирования нужен индекс «user → tokenId» (например, в SoulboundCore или в SoulIdentity при минте через callback).
- **Парсинг level/reputation:** _parseLevel и _parseReputation — заглушки (всегда 1 и 100). Фактические значения из JSON не используются; обновление в SoulMetadata при этом пишется. Дыра: ончейн-логика не может опереться на реальные level/reputation до реализации парсинга (или выноса числовых полей в отдельные storage).

### 5.2 Безопасность

- **SoulMetadata и вызовы от SoulIdentity:** как выше, для успешного вызова SoulIdentity к SoulMetadata необходимо, чтобы SoulboundCore.owner() был настроен так, чтобы msg.sender (SoulIdentity) считался разрешённым (например, owner = SoulIdentity). Иначе любой вызов updateSoulLevel/updateSoulReputation приведёт к revert. Это не дыра безопасности, но **критичная зависимость деплоя**; при неправильной настройке функциональность уровня/репутации не работает.
- **Централизация:** если SoulIdentity является владельцем SoulboundCore, то ключи SoulIdentity дают возможность минтить/сжигать души (через вызовы в SoulboundCore от owner) и управлять контрактами SoulboundCore (setMetadataContract, setRecoveryContract, setIntegrationContract). Нужно явно учитывать в модели угроз и, при необходимости, разделить роли (например, owner SoulboundCore — мультисиг, а SoulIdentity — только вызывающий с отдельными правами на запись в SoulMetadata через whitelist).
- **Guardians и recovery в SoulIdentity:** методы addTrustedGuardian, getTrustedGuardians, initiateRecovery, completeRecovery — заглушки; реальная логика только в SoulRecovery. Пользователь, ожидающий единую точку входа в SoulIdentity, не видит реальных guardians и не может инициировать recovery через SoulIdentity. Дыра удобства и согласованности; закрытие — интеграция SoulIdentity ↔ SoulRecovery (таск уже обозначен в других документах).
- **Один guardian на tokenId в SoulRecovery:** при компрометации этого guardian восстановление может инициировать только он; нет порога из нескольких доверенных лиц. Ограничение дизайна, не баг — при необходимости усложнять модель (m-of-n) потребуется изменение контракта.

### 5.3 Сводка по дырам

| Область | Дыра | Серьёзность |
|--------|------|--------------|
| Жизненный цикл | Нет ончейн-правила «когда минтить душу»; рассинхронизация с активацией | Средняя (удобство, целостность) |
| Масштаб | _getUserTokenId перебор до 1000; O(n) газ; пользователи с tokenId > 1000 не видны | Средняя (газ, лимит) |
| Данные | Парсинг level/reputation — заглушки; ончейн не использует реальные значения | Низкая (функциональность) |
| Деплой | SoulMetadata принимает запись только от tokenOwner или SoulboundCore.owner(); зависимость от настройки owner | Высокая (работоспособность) |
| Единая точка входа | Guardians/recovery в SoulIdentity не связаны с SoulRecovery | Средняя (удобство) |
| Роли | SoulIdentity как owner SoulboundCore — концентрация полномочий | Зависит от модели угроз |

---

## 6. Краткие выводы

- **Идентичность и DID:** создание идентичности (SBT) не привязано ончейн к активации; окно для DID — наличие SBT; хранение DID только в SoulIdentity. Адекватно при явно заданном процессе минта души и интеграции; дыра — отсутствие автоматической связки «активация → душа».
- **Инвайт vs SBT:** инвайт — отдельный soulbound NFT в SpiralEngine; душа — отдельный SBT в SoulboundCore. Разделение обосновано; важно не смешивать в документации и интеграциях.
- **SoulboundCore:** ядро владения SBT; метаданные не хранит, только запрашивает tokenURI у SoulMetadata.
- **Метаданные:** в SoulMetadata по tokenId (metadataType, version, attributes JSON, ipfsHash); типы — identity/achievement/reputation и т.д.; level/reputation в attributes; запись — только от владельца токена или от владельца SoulboundCore (критична настройка owner для вызовов из SoulIdentity).
- **Избыточность:** явного дублирования данных нет; два API для DID (linkSoulIdentity и linkExternalIdentity) — один массив, документировать использование.
- **Дыры:** приоритетно — настройка деплоя для SoulMetadata и лимит/газ _getUserTokenId; затем — связка активация/душа, интеграция SoulIdentity↔SoulRecovery, парсинг level/reputation.

Документ можно использовать для решений по доработке архитектуры и следующих тасков (индекс user→tokenId, интеграция SoulIdentity↔SoulRecovery, парсинг атрибутов, процесс «активация → душа»).
