## SpiralEngine, Amanita Passport и токены $LOVE / $LGOV / $AMANITA — Contract Layer MVP Scope (2026‑03‑15)

**Статус:** актуализированный MVP‑scope для контрактного слоя Amanita:  
- SpiralEngine (инвайты, роли, анти‑сибил);  
- SBT‑стек и Amanita Passport (души, DID, recovery);  
- social mining на базе LoveDoPostNFT + LoveEmissionEngine;  
- двухтокенная модель $LOVECOIN / $LGOV и отдельный seller‑token $AMANITA.  

**Источники таргет‑состояния:**  
- `docs/concept/Network-Economy.md`  
- `docs/tech/SpiralEngine Roles Security Policy.md`  
- `docs/tech/Anti Sybil Policy.md`  
- `contracts/docs/Amanita-SBT-Architecture/*.md` (01–10)  
- `contracts/docs/LoveEmissionEngine.md`, `contracts/docs/LovecoinTokens.md`  

Этот документ описывает **минимальный контрактный функционал**, который должен быть реализован и честно задокументирован в **MVP релизе экосистемы Amanita**, с учётом:

- спиральности через инвайты (SpiralEngine);  
- SBT как ончейн‑слоя для Amanita Passport;  
- social mining через LoveDoPostNFT + LoveEmissionEngine;  
- токеномики трёх токенов: $LOVECOIN, $LGOV, $AMANITA.  

Всё, что выходит за эти границы (continuous LGOV mining, сложные recommendation‑индексы, multi‑chain Passport, B2‑ключи и т.п.), фиксируется как **target‑state / post‑MVP**.

---

## 1. Спиральность и доступ: SpiralEngine как InviteGraph

### 1.1. Базовая модель SpiralEngine в MVP

**Контракт:** `SpiralEngineLogic` (+ Proxy/UUPS).  
**Роль:** социальный граф доступа и доверия, через который вообще становится возможным:

- участие в экосистеме (user с инвайтом);  
- выполнение ролей (Activator, Seller);  
- участие в social mining (через связку с LoveDo и InviteGraph в LoveEmissionEngine).

**Что обязательно в MVP (уже есть в коде и соответствует Anti Sybil / Roles Policy):**

- **Инвайты как soulbound‑единицы доступа** (в текущей реализации — ERC721 с запретом transfer; далее возможен переход на «инвайты как лог» по отдельному таску):  
  - уникальный `inviteCode`;  
  - 1 использованный инвайт → 1 активированный пользователь;  
  - лимит «круг 12» для новых инвайтов от активированного.  
- **Граф активаций:**  
  - `usedInviteByUser[user]` — какой инвайт использовал;  
  - `userActivator[user]` — кто активировал;  
  - `sellerNominator[seller]` — кто номинировал продавца.  
- **Anti‑Sybil инварианты InviteGraph (Anti Sybil Policy §4.1–4.4):**  
  - без `usedInviteByUser[user] != 0` пользователь не считается участником экосистемы и не может быть activator/seller;  
  - superlikes и социальные сигналы ограничены одним кругом доверия (`inviterOfAuthor == inviterOfLiker`);  
  - InviteGraph используется для наследования репутации и ответственности (activation tree).

### 1.2. Роли Activator и Seller (Roles Policy → MVP)

**Activator (ACTIVATOR_ROLE) — MVP:**

- при успешной `activateUser` SpiralEngine:  
  - устанавливает `usedInviteByUser[user] != 0`;  
  - назначает пользователю `ACTIVATOR_ROLE` (базовый уровень);  
- права:  
  - активировать новых пользователей в своём круге;  
  - создавать активности в `ActivityRegistry` (activity creator = activator).

**Не входит в MVP, но зафиксировано в Roles Policy как target:**  
- уровни активаторов L0/L1/L2, метрики `activationViolations`, `activitiesReported`, сложная деградация прав — только в политике, не в коде MVP.

**Seller (SELLER_ROLE) — MVP:**

- выдаётся **только адресам с ролью админа** (через `ADMIN_ROLE` / owner), без on‑chain recommendation‑индексов и stake‑кампаний;  
- инвариант: без `usedInviteByUser[user] != 0` и без `ACTIVATOR_ROLE` пользователь SELLER не получает;  
- **каждая выдача SELLER фиксируется событием** `SellerRoleGranted(address indexed user, address indexed nominator, uint256 timestamp)` — оффчейн‑системы могут подписываться на него для аудита и мониторинга назначений;  
- правовые/рисковые проверки, контент‑проверка и т.д. остаются в оффчейн‑процессах и `Contracts Security Architecture`.

**Target‑состояние для Seller (Roles Policy):**  
- пятишаговый путь (LoveDo‑челленджи, LGOV‑stake, proof‑of‑producer, recommendation index, probation), stake & slash, graph‑diversity фильтры — **не в коде MVP**, но учитываются при проектировании следующих фаз.

---

## 2. Души (SBT) и Amanita Passport

### 2.1. Контракты SBT‑стека

- `SoulboundCore` — ядро SBT (EIP‑5192):  
  - хранит владельцев душ и supply;  
  - transfer/approve запрещены;  
  - смена владельца только через `executeRecovery` от `SoulRecovery`.  
- `SoulMetadata` — хранит тип, версию, JSON‑атрибуты (level, reputation и др.) и ipfsHash по `tokenId`.  
- `SoulIdentity` — мост и фасад:  
  - чтение уровня/репутации/метаданных через `SoulMetadata`;  
  - хранение DID и external identities;  
  - предоставление агрегированного профиля (`getSoulProfile`).  
- `SoulRecovery` — recovery‑слой:  
  - guardian на `tokenId`;  
  - двухфазный recovery (initiate + confirm) с задержками GUARDIAN_DELAY и RECOVERY_DELAY;  
  - в Anti Sybil Policy рассматривается как механизм «переноса души на новый адрес».

### 2.2. Один активированный пользователь → одна душа (Passport foundation)

**MVP‑инвариант:**  
каждый пользователь, для которого `SpiralEngineLogic.activateUser` успешно завершён и `usedInviteByUser[user] != 0`, имеет **ровно одну SBT‑душу** в `SoulboundCore`, которая далее служит технической основой Amanita Passport.

**Реализация (SBT-INV-1, выполнено):**

- ончейн: при `activateUser` контракт **SpiralEngine** (Logic) вызывает `SoulboundCore.mintSoul(user)` при условии `soulboundCore != address(0)` и `soulboundCore.balanceOf(user) == 0`;  
- **MINTER_ROLE** в SoulboundCore выдаётся **только адресу контракта SpiralEngine** (proxy); активированным пользователям MINTER_ROLE не выдаётся;  
- при деплое: выдать SoulboundCore.MINTER_ROLE адресу SpiralEngine proxy и вызвать SpiralEngine.setSoulboundCore(soulboundCore).

### 2.3. Профиль души и Amanita Passport (один community, одна сеть)

**On‑chain профиль души через `SoulIdentity`:**

- level / reputation — через `SoulMetadata.attributes` (упрощённый парсинг в MVP допустим, пока логика не завязана на точные значения);  
- DID и внешние идентичности (включая X) — через `userIdentities` и `linkExternalIdentity`;  
- guardians и recovery — после делегирования из `SoulIdentity` в `SoulRecovery` (см. `task-delegate-soul-identity-recovery-to-soul-recovery`).

**Amanita Passport MVP (view‑слой):**

- `displayName` и `@community:handle` (например, `@spiral:moss-architect`) — реализуются по `task-implement-passport-display-name-handle` (решение ончейн vs оффчейн внутри таска);  
- `soulRef` = `{ chainId, soulboundCore, tokenId }` — ссылка на душу;  
- основная `DID` (например, `did:spiral:...`) — из `SoulIdentity`;  
- `externalIdentities.x` — опциональная привязка X (handle, profileUrl и т.п.) как external identity (см. `task-document-passport-x-integration`).

**Вне MVP, но в архитектуре (SBT‑архитектура + Anti Sybil / Roles Policy):**

- multi‑chain и multi‑community Passport;  
- временные ключи (B2) и расширенный recovery‑поток;  
- Privado DID / VC‑слой (`07-privado-did-credential-schema.md` и др.).

---

## 3. Social Mining: LoveDoPostNFT + LoveEmissionEngine

### 3.1. LoveDoPostNFT как слой social proof

**Контракт:** `LoveDoPostNFT.sol`.  
**Роль:** децентрализованный слой social proof, фиксирующий реальные отзывы и суперлайки:

- структура поста включает автора (`author`), адрес продавца (`sellerTo`), linkedSeller, счётчик `superlikes`, `timestamp`;  
- лимиты по активности (Anti Sybil Policy §4.3):  
  - `MAX_MONTHLY_POSTS_PER_USER = 8`;  
  - `MAX_SUPERLIKES_PER_MONTH = 8`;  
  - `MAX_MENTIONS_PER_SELLER = 8`;  
- `addSuperlike(tokenId, expectedNonce)` обеспечивает:  
  - nonce‑защиту от фронтраннинга;  
  - проверку ролей (`hasSellerRole` для sellerTo, после согласования источника — AmanitaRegistry или SpiralEngine, см. `task-fix-lovedo-emission-interface`);  
  - работу в пределах InviteGraph (social proximity).

### 3.2. LoveEmissionEngine и двухтокенная модель $LOVECOIN / $LGOV

**Контракт:** `LoveEmissionEngine.sol`.  
**Роль:** реализация Loveconomy social mining в соответствии с `Network-Economy.md` и Anti Sybil Policy.

- На каждый валидный superlike:  
  - `loveAccrued[seller] += EMISSION_RATE;` → накопленные $LOVECOIN;  
  - `lgovAccrued[seller] += EMISSION_RATE;` → pending $LGOV.  
- `$LOVECOIN`:  
  - utility‑токен (Lovecoin.sol);  
  - claimable через `claimLOVECOIN()`;  
  - используется как «бюджет скидок/поощрений» для продавцов, ограниченный намайненным (см. Network‑Economy: финансовая ответственность).  
- `$LGOV`:  
  - governance‑токен (AmanitaGovToken.sol / AGOV в коде);  
  - активируется через `claimLGOV()` при выполнении порога `LOVE_DO_THRESHOLD` (≥ 8 постов);  
  - текущая модель — **one‑shot activation** (`lgovClaimed`).

**MVP‑позиция (Anti Sybil Policy + Network‑Economy):**

- one‑shot модель LGOV **оставляется в MVP как есть**, но задокументирована как временный компромисс;  
- целевая continuous‑модель (reputation‑gated, без one‑shot) вынесена в `task-fix-loveemission-lgov-continuous-governance` и не входит в этот scope.

### 3.3. Anti‑Sybil‑ограничения на social‑уровне

Согласно Anti Sybil Policy (§4.1–4.4), в коде уже реализованы и входят в MVP:

- **InviteGraph Identity Structure:** `usedInviteByUser[user] != 0` для участия;  
- **Circle‑based interaction limits:** superlikes только при совпадении корня круга (`inviterOfAuthor == inviterOfLiker`);  
- **Monthly Activity Limits:** лимиты постов/superlikes/mentions в LoveDoPostNFT;  
- **Reputation Threshold for Governance:** порог 8 LoveDo‑постов перед claimLGOV.

Сложные механики (graph‑diversity индексы, stake‑обязательства, cluster‑аналитика, decay / repWeight) остаются на уровне политик и последующих фаз.

---

## 4. $AMANITA как seller‑loyalty токен

### 4.1. Экономическая роль ($AMANITA vs $LOVECOIN / $LGOV)

**Контракт:** `AmanitaToken.sol` (symbol: AMANITA).  
**Роль:** токен лояльности продавцов в `Network-Economy.md`:

- децентрализованная эмиссия продавцами/сервисами по факту продажи товаров/услуг;  
- MINTER_ROLE → возможность минтить AMANITA пропорционально «sold values»;  
- BURN при погашении (redeem) в loyalty‑программах.

**Разделение осей:**

- $LOVECOIN — social mining utility (LoveEmissionEngine + LoveDo);  
- $LGOV — governance;  
- $AMANITA — seller‑loyalty, завязанный на выручку и программы лояльности.

### 4.2. MVP‑границы по $AMANITA

В рамках контрактного MVP:

- AmanitaToken развёрнут с корректными MINTER/BURNER‑ролями;  
- его использование не ломает инварианты Anti‑Sybil и не смешивает свои потоки с LoveEmissionEngine;  
- документация (`Network-Economy.md`, `LovecoinTokens.md`) чётко объясняет, что $AMANITA — отдельная система от $LOVECOIN / $LGOV.

Детальные сценарии использования ($AMANITA + WooCommerce, кросс‑sellerские акции и т.п.) — поверх этого слоя, не требуются для выполнения контрактного MVP.

---

## 5. Governance‑параметры и управление ими в MVP

### 5.1. Что зашито в код и входит в MVP

- `LOVE_DO_THRESHOLD`, `EMISSION_RATE`, лимиты LoveDo;  
- флаги и роли: `lgovClaimed`, `usedInviteByUser`, `ACTIVATOR_ROLE`, `SELLER_ROLE`;  
- правила доступа на основе InviteGraph (без инвайта — нет ролей и участия в emission).

Управление параметрами в MVP — через код (константы/конфиг) и обновление архитектурных документов, а не через on‑chain голосования.

### 5.2. Что явно вне MVP, но должно быть учтено

- on‑chain конфиг‑контракты с возможностью голосования LGOV по параметрам;  
- continuous governance‑майнинг и репутационные веса (target‑модель в Anti Sybil Policy);  
- graph‑diversity индексы, stake/slash‑слои и cluster‑аналитика как on‑chain механики.

---

## 6. Обзор MVP‑scope по слоям

### 6.1. Что реально получает пользователь в первом релизе

- **Спиральный доступ:** InviteGraph + роли Activator/Seller, без инвайта — нет участия.  
- **Ончейн‑душу:** одну SBT‑душу на активированного пользователя (основа для Amanita Passport).  
- **Профиль Passport MVP:** адрес + душа + DID + (после выполнения тасков) displayName/handle и, опционально, привязка X.  
- **Social mining:** LoveDoPostNFT + LoveEmissionEngine — суперлайки формируют $LOVECOIN и pending $LGOV с репутационным порогом; работают антисибил‑лимиты.  
- **Seller‑loyalty токен:** $AMANITA готов к использованию в программах лояльности.

### 6.2. Что остаётся архитектурным долгом / пост‑MVP

- continuous LGOV‑майнинг (Model 2);  
- seller‑recommendation индексы и stake/slash‑слои;  
- on‑chain graph‑diversity и cluster‑санкции;  
- multi‑chain и federated Amanita Passport;  
- временные ключи (B2), расширенный recovery, VC‑слой;  
- on‑chain конфиг‑контракты и голосование LGOV.

---

## 7. Как использовать этот документ

Этот документ — **единый scope для контрактного MVP**:

- при ревью кода и тестов — сверять реализованное поведение с описанными инвариантами;  
- при постановке/проверке тасков — чётко разделять «входит в MVP» и «target‑state»;  
- при коммуникации с продуктовой/экосистемной стороной — объяснять границы возможностей первого релиза без избыточных обещаний.

Любая новая функциональность, выходящая за рамки этого scope, должна оформляться как отдельная задача в `contracts/docs/analysis/tasks/` и включаться в соответствующие индексы (`sbt-index.md`, `social-mining-index.md`, `security-tasks-index.md`, `tests-tasks-index.md`) **до** того, как будет считаться частью MVP.

## SpiralEngine & LGOV Security — MVP Scope (2026-03-12)

**Статус:** MVP scope (что реализуем в первом релизе)  
**Источники таргет-состояния:**  
- `docs/tech/SpiralEngine Roles Security Policy.md`  
- `docs/tech/Anti Sybil Policy.md`  
- `contracts/docs/LoveEmissionEngine.md`, `contracts/docs/LovecoinTokens.md`  

Этот документ фиксирует **минимальный объём функционала**, который входит в MVP по безопасности ролей SpiralEngine и governance‑майнинга `LGOV`. Всё остальное из таргет-политик — последующие фазы.

---

## 1. SpiralEngine: роли Activator & Seller — MVP

### 1.1. Activator

**MVP:**
- Автоматическая выдача `ACTIVATOR_ROLE` при `activateUser`:
  - условие: `usedInviteByUser[user]` установлен (пользователь активирован по инвайту);
  - `ACTIVATOR_ROLE` даёт право:
    - активировать других (в рамках уже существующей логики);
    - создавать активности в `ActivityRegistry` (activity creator = activator).

**Не входит в MVP (останется концептом):**
- Уровни активаторов (L0/L1/L2).
- Метрики `activationViolations`, `activitiesReported` и понижение уровня.

### 1.2. Seller

**MVP:**
- `SELLER_ROLE` **выдаётся только админом** (адреса с `ADMIN_ROLE` / деплоящий аккаунт):
  - только через `ADMIN_ROLE` / деплоящий аккаунт;
  - без on-chain индекса рекомендаций и stake‑кампаний.
- **Каждая выдача фиксируется событием** `SellerRoleGranted(address indexed user, address indexed nominator, uint256 timestamp)` — оффчейн может подписываться на него для аудита и мониторинга.
- Базовые инварианты:
  - без `usedInviteByUser[user] != 0` и без `ACTIVATOR_ROLE` пользователь **не может** стать SELLER.

**Не входит в MVP (target-state):**
- Пять челленджей на путь к SELLER (LoveDo‑путь, stake‑кампания, proof‑of‑producer, индекс 8, probation).
- Реализация recommendation index `I(C)` и `circleDecay` на уровне кода.
- Stake & slash `LGOV` для рекомендателей и probation‑логика.

---

## 2. LGOV Governance Mining — MVP

### 2.1. Модель клейма LGOV

**MVP (текущее on-chain поведение):**
- `LoveEmissionEngine`:
  - копит `lgovAccrued[addr]` при суперлайках (`emitForSuperlike`);
  - реализует **одноразовый `claimLGOV()`**:
    - проверяет `LOVE_DO_THRESHOLD` (≥ 8 LoveDo‑постов);
    - мчит накопленное `lgovAccrued[addr]`;
    - ставит `lgovClaimed[addr] = true`;
    - повторные вызовы ревертятся (`already claimed`).
- Это поведение **оставляем в MVP как есть**, но:
  - задокументировано как **временная мера**, конфликтующая с философией;
  - таргет‑модель continuous mining описана и вынесена в отдельный таск:
    - `contracts/docs/analysis/tasks/task-fix-loveemission-lgov-continuous-governance/task-fix-loveemission-lgov-continuous-governance.md`.

**Не входит в MVP:**
- Переход к continuous, reputation‑gated governance‑майнингу (Model 2).
- Любые ограничения по graph diversity для `LGOV` на уровне контракта.

### 2.2. Параметры и трекинг

**MVP:**
- Используем уже существующие параметры и структуры:
  - `LOVE_DO_THRESHOLD = 8`;
  - `EMISSION_RATE = 1 ether`;
  - `lgovAccrued`, `lgovClaimed`, `loveAccrued`.
- Добавляем / поддерживаем:
  - документацию, честно описывающую one‑shot модель (`LovecoinTokens.md`, `LoveEmissionEngine.md`, `Anti Sybil Policy.md`);
  - метрики в аналитике:
    - распределение `LGOV` по адресам;
    - долю адресов, сделавших `claimLGOV()`.

**Не входит в MVP:**
- on-chain graph‑diversity‑фильтры для `LGOV` (только off‑chain аналитика в будущем).
- репутационные веса в эмиссии (пока 1 superlike = 1 `LGOV`).

---

## 3. Anti-Sybil механики — что входит в MVP

### 3.1. То, что уже реализовано и считается частью MVP

- **InviteGraph** как обязательный слой:
  - все пользователи с инвайтом (`usedInviteByUser[user] != 0`);
  - без инвайта нет ни `ACTIVATOR_ROLE`, ни `SELLER_ROLE`.
- **Circle-based limits** в LoveEmissionEngine:
  - superlike возможен только при `inviterOfAuthor == inviterOfLiker`.
- **Monthly limits** в LoveDoPostNFT:
  - `MAX_MONTHLY_POSTS_PER_USER`, `MAX_SUPERLIKES_PER_MONTH`, `MAX_MENTIONS_PER_SELLER`.
- **Reputation gate для LGOV**:
  - `LOVE_DO_THRESHOLD = 8`;
  - `claimLGOV()` доступен только после 8+ постов.

### 3.2. Что остаётся только в политике (не в MVP‑коде)

Из `Anti Sybil Policy` **в MVP НЕ вносим в код**:

- LGOV‑bonding / stake‑обязательства для governance unlock, Seller, recommenders.
- Graph diversity правила (`N_branches_min`, `T_diversity`) как on-chain фильтр.
- Репутационные веса `repWeight` и decay с `exp(-λ t)` в коде эмиссии/ролей.
- On-chain cluster‑sanctions и автоматизированные меры против кластеров.

Но **эти элементы учтены**:

- в архитектуре;
- в формулировке задач следующего этапа;
- и должны учитываться при дизайне UI/аналитики (dashboards, off‑chain алерты).

---

## 4. SpiralEngine & Sellers — MVP vs Target

### 4.1. MVP поведение

- Роль `SELLER_ROLE`:
  - выдаётся **только админом**, ручным управлением;
  - правовые/рисковые ограничения (что можно продавать) выносятся в:
    - off‑chain ревью кандидатов;
    - сводку в `Contracts Security Architecture.md`.
- Никаких автоматизированных:
  - индексов рекомендаций;
  - stake‑кампаний;
  - probation‑периодов на уровне смарт‑контрактов.

### 4.2. Target-state (для ориентира)

В `SpiralEngine Roles Security Policy` остаётся описанным target‑pipeline:

- 5 челленджей (LoveDo‑путь, LGOV stake, proof‑of‑producer, recommendation index 8, probation).
- Формулы:
  - \( W_r = stake[r] \cdot repWeight[r] \cdot circleWeight[d(r)] \)
  - \( I(C) = \sum_r W_r \), порог `T` ≈ 8.
- Stake & slash, снижение `repWeight[r]` при нарушениях.

MVP‑док (этот файл) фиксирует, что **в первый релиз** из этого набора берём только:

- ручной grant SELLER через ADMIN;
- базовые инварианты вокруг инвайтов и `ACTIVATOR_ROLE`.

---

## 5. Governance & параметры — MVP

**В MVP:**

- Параметры:
  - `LOVE_DO_THRESHOLD`, `EMISSION_RATE`, лимиты LoveDo, базовые роли/флаги (`lgovClaimed`, `usedInviteByUser`, `ACTIVATOR_ROLE`, `SELLER_ROLE`).
- Управляются:
  - через код (константы / конфиг), без on-chain конфиг‑контракта;
  - через обновление архитектурных документов.

**Не в MVP (но в таргете):**

- On-chain конфиг‑контракт для:
  - `circleDecay`, `T_seller`, `N_branches_min`, `λ` и др.;
  - голосование LGOV за изменение параметров.

---

## 6. Следующие шаги после MVP (outline)

После стабилизации MVP целесообразны следующие блоки задач:

1. **LGOV Model 2 (continuous governance‑mining)**  
   - реализация нового `claimLGOV()` без one‑shot флага, по таску `task-fix-loveemission-lgov-continuous-governance`;
   - тесты и миграционная стратегия для уже активировавших LGOV.

2. **Seller Recommendation & Stake Layer**  
   - реализация recommendation index `I(C)` и stake‑кампаний;
   - probation‑период и stake‑slash.

3. **Reputation Metrics & Decay**  
   - сбор и экспонирование `repScore`, `repWeight`, violation‑метрик;
   - off‑chain мониторинг decay, затем — on-chain/конфигурируемые параметры.

4. **Graph Diversity & Cluster Analytics**  
   - dashboards по кластерности, diversity и LGOV‑распределению;
   - подготовка к мягким лимитам и governance‑эскалациям.

Этот документ должен использоваться как **рамка для планирования релизов**:  
он фиксирует, что именно пользователь может ожидать от **MVP‑версии безопасности**, и какие части остаются в зоне **архитектурного debt / следующих релизов**.

