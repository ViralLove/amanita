# Amanita Passport — минимально необходимый функционал (MVP scope)

**Версия:** 1.0  
**Дата:** 2026-03-14  
**Методика:** run-analysis; целостное понимание архитектуры SBT (документы 01–09) и планируемых интеграций.  
**Назначение:** зафиксировать минимальный объём функциональности, достаточный для объявления «Amanita Passport MVP» и для согласования границ с тасками и интеграциями.

Связанные документы: [00-INDEX.md](./00-INDEX.md), [08-personhood-driven-federated-identity-model.md](./08-personhood-driven-federated-identity-model.md), [06-identity-did-invite-sbt-metadata-audit.md](./06-identity-did-invite-sbt-metadata-audit.md), [04-critical-audit-goals.md](./04-critical-audit-goals.md), [09-x-love-do-feasibility-analysis.md](./09-x-love-do-feasibility-analysis.md).

---

## 1. Исходные решения и границы MVP

- **Passport** в целевой модели (док. 08) — оркестрационный слой над community identities: DID per community, showcase community, федеративная репутация, X как интерфейс.
- **MVP** здесь — минимальный шаг к «работающему Passport», без реализации всего целевого видения. То есть: один контекст (одно сообщество, одна сеть), одна душа на пользователя, один читаемый профиль и явные точки интеграции с SpiralEngine, LoveDo и X.
- **Биометрия** не входит в протокольную идентичность (только local key unlock). **Multi Chain** и **федерация нескольких сообществ** в одном Passport — за рамками MVP (см. раздел 5).

---

## 2. Минимально необходимый функционал Passport MVP

### 2.1 Контрактный слой (без изменений целевой архитектуры)

| Компонент | Роль в MVP | Ограничения / решения |
|-----------|------------|------------------------|
| **SoulboundCore** | Владение SBT (душа), EIP-5192, единственный способ смены владельца — recovery. | Без изменений. |
| **SoulMetadata** | Хранение типа, версии, атрибутов (level, reputation в JSON). | Без изменений. Заглушки парсинга level/reputation в SoulIdentity для MVP допустимы (значения 1 и 100), если ончейн-логика не использует их в правилах. |
| **SoulIdentity** | Условие «есть SBT» для DID; привязка одной основной идентичности и при необходимости external identity (X). Профиль: getSoulProfile (level, reputation, identity, displayName, handle). **displayName** и **handle** хранятся ончейн в SoulIdentity (маппинги по адресу); установка — setDisplayName/setHandle только владельцем души; чтение — getSoulProfile или getDisplayName/getHandle. Формат handle: @communityId:localHandle (напр. @spiral:user), макс. 32 байт; displayName макс. 64 байт. | Guardians / recovery в SoulIdentity — заглушки; реальная логика в SoulRecovery. |
| **SoulRecovery** | Восстановление доступа: guardian → initiateRecovery(newOwner) → confirmRecovery; смена владельца SBT на новый адрес. | Модель «перенос на newOwner» входит в MVP; модель «доверенные лица хранят ключи» — вне MVP. |
| **SpiralEngine** | Инвайты, активация, роли, номинация, санкции. Не минтит души; при необходимости читает SoulIdentity (getSoulLevel, getSoulReputation и т.д.). | В MVP бизнес-правила движка **не обязаны** использовать level/reputation; связь «после активации должна появиться душа» обеспечивается процессом/оркестрацией (см. п. 2.2). |

### 2.2 Связь «активация → душа» (критично для MVP)

- **Проблема (аудит 06):** в коде нет ончейн-правила «когда минтить душу»; возможна рассинхронизация (активирован без души или душа без активации).
- **MVP-требование:** для каждого активированного пользователя (usedInviteByUser > 0) должна существовать ровно одна душа (SBT) в SoulboundCore, привязанная к этому адресу.
- **Реализация:** канонический ончейн-путь — таск [task-implement-invites-log-soul-on-activation](../analysis/tasks/task-implement-invites-log-soul-on-activation/task-implement-invites-log-soul-on-activation.md): при активации пользователя (activateUser) минтится душа в SoulboundCore (один SBT на активированного). Все решения по инвайтам (лог vs NFT) и минтеру души — внутри этого таска; для MVP достаточно его выполнения и гарантии «активирован ⇒ есть soul».

### 2.3 Профиль Passport (агрегация для одного сообщества)

Минимальный **читаемый профиль** Passport MVP (один community, одна сеть):

- **Идентификатор:** адрес владельца + при необходимости soul tokenId (для однозначности и ссылок).
- **Публичное представление:** displayName, community-prefixed handle (например `@spiral:handle`); в MVP один community = один handle/displayName.
- **Душа:** tokenId, level, reputation (из SoulMetadata через SoulIdentity; допускаются заглушки значений).
- **DID:** одна основная идентичность (linkSoulIdentity / linkExternalIdentity), возвращаемая getSoulIdentity.
- **Внешние идентичности (опционально):** X — xHandle, profileUrl; только как external identity link, не как trust root (док. 08, 09).

Источник данных: ончейн (SoulboundCore, SoulMetadata, SoulIdentity, SpiralEngine). **displayName** и **handle** — ончейн в SoulIdentity (маппинги по адресу владельца души); чтение через getSoulProfile(user) или getDisplayName(user)/getHandle(user); установка владельцем души через setDisplayName/setHandle (таск SBT-PAS-1).

### 2.4 Интеграции в границах MVP

| Интеграция | Включено в MVP | Ограничение |
|------------|----------------|-------------|
| **SpiralEngine** | Активация, инвайты, роли (SELLER, ACTIVATOR), usedInviteByUser. После активации — процесс минта души. | Level/reputation души не используются в правилах движка (активация, санкции, grantSellerRole). |
| **LoveDo / LoveEmission** | После выполнения таска [task-fix-lovedo-emission-interface](../analysis/tasks/task-fix-lovedo-emission-interface/task-fix-lovedo-emission-interface.md): автор LoveDo, superlikes и эмиссия согласованы с контрактами. Passport может отображать «автор отзывов / superlikes» как часть активности. | X likes не являются ончейн superlikes; только доверительный superlike внутри invite-circle (док. 09). |
| **X** | Опциональная привязка X-аккаунта к Passport (external identity); Passport URL + preview cards для discovery; при необходимости Sign in with X. | X не source of truth для репутации; X post → LoveDo token и X likes → superlikes не входят в MVP как автоматический ончейн-поток. |

---

## 3. Точки решений внутри MVP (где нужны явные решения)

- **Когда и кто минтит душу:** оркестратор по событию активации vs контракт/колбэк при activateUser (см. таск invites-log-soul-on-activation).
- **Где хранить displayName и handle:** решение принято (SBT-PAS-1): ончейн в SoulIdentity (маппинги displayNameByUser, handleByUser по адресу); setDisplayName/setHandle — только владелец души; формат handle @communityId:localHandle, лимиты 64/32 байт.
- **Единая точка входа recovery:** оставить только SoulRecovery для MVP или к MVP завершить делегирование из SoulIdentity в SoulRecovery (addTrustedGuardian, getTrustedGuardians, initiateRecovery, completeRecovery).
- **Индекс user → tokenId:** SoulIdentity._getUserTokenId перебором до 1000 (аудит 06). Для маленького сообщества достаточно для MVP; при росте — таск на индекс (user → tokenId при минте) или увеличение лимита и документирование риска.

---

## 4. Критерии приёмки Passport MVP (DoD)

- [ ] Для любого активированного в SpiralEngine пользователя существует ровно одна душа (SBT) в SoulboundCore, привязанная к его адресу; процесс «активация → минт души» зафиксирован и выполняется.
- [ ] Passport-профиль (один community) читаем: displayName, handle, soul (tokenId, level, reputation), основная DID; при необходимости — external identity (X).
- [ ] Восстановление доступа к душе возможно через SoulRecovery (guardian → newOwner) и документировано; при необходимости — единая точка входа через SoulIdentity (Phase 2).
- [ ] LoveDo/LoveEmission: интерфейс выровнен (таск task-fix-lovedo-emission-interface выполнен); superlike и эмиссия работают без расхождений с LoveDoPostNFT.
- [ ] X: опциональная привязка к Passport и использование X как discovery/превью — документированы; нет зависимости Passport от X как от источника репутации.
- [ ] Документация: границы MVP (один community, одна сеть), точки решений и список «вне MVP» актуальны и доступны команде.

---

## 5. Явно вне MVP (не блокирует объявление Passport MVP)

- **Multi Chain Amanita Passport:** один Passport — несколько сетей / chainId; кросс-чейн верификация или мост (док. 04).
- **Федерация нескольких сообществ:** несколько community DIDs в одном Passport, showcase community, федеративная репутация по сообществам (док. 08).
- **B2 / временный ключ:** createTemporaryKey, делегирование без смены владельца души (док. 05; таск task-implement-sbt-temporary-key-delegation).
- **Использование level/reputation в правилах SpiralEngine:** допуск по уровню души, влияние репутации на санкции или роли.
- **X как source of truth:** автоматическое отождествление X likes с on-chain superlikes; X-only репутация (док. 09).
- **Полная схема VC / issuing node для Privado DID:** выдача верифицируемых credentials по док. 07 — опционально; MVP может ограничиться ончейн-данными и простым профилем без VC.
- **Обязательная биометрия или real-name:** не входят в модель (док. 08).

---

## 6. Связь с тасками и индексами

- **Таск «активация → душа»:** [task-implement-invites-log-soul-on-activation](../analysis/tasks/task-implement-invites-log-soul-on-activation/task-implement-invites-log-soul-on-activation.md) — критичен для выполнения DoD «активирован ⇒ есть soul».
- **Таск выравнивания LoveDo/Emission:** [task-fix-lovedo-emission-interface](../analysis/tasks/task-fix-lovedo-emission-interface/task-fix-lovedo-emission-interface.md) — нужен для интеграции Passport с LoveDo/superlikes в MVP.
- **Индекс SBT/Passport тасков:** [sbt-index.md](../analysis/tasks/sbt-index.md); индекс social mining: [social-mining-index.md](../analysis/tasks/social-mining-index.md).

После добавления новых тасков, напрямую влияющих на Passport MVP (например, хранение displayName/handle ончейн, делегирование SoulIdentity → SoulRecovery), их стоит отразить в этом документе и в соответствующем индексе.

---

## 7. Итог

**Amanita Passport MVP** — минимально необходимый функционал для «работающего Passport» на базе целостной SBT-архитектуры и планируемых интеграций:

- один community, одна сеть;
- одна душа на активированного пользователя (процесс «активация → душа» зафиксирован и выполняется);
- читаемый профиль: displayName, handle, soul, DID, опционально X;
- восстановление доступа через SoulRecovery (guardian → newOwner);
- выровненный LoveDo/LoveEmission и опциональный X как интерфейс/discovery.

Всё, что выходит за эти границы (multi-chain, федерация сообществ, B2, использование level/reputation в правилах движка, X как source of truth), остаётся за рамками MVP и не блокирует объявление Passport MVP при выполнении критериев раздела 4.
