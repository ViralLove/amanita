# Структура JSON для Privado DID (ex Polygon ID) — Amanita Soul & Reputation

**Версия:** 1.0  
**Дата:** 2026-03-14  
**Назначение:** схема Verifiable Credential (VC) для идентичности и репутации в формате Privado ID (Polygon ID), согласованная с моделью данных контрактов (SoulboundCore, SoulMetadata, SoulIdentity) и с задачей reputation-driven multi-community ecosystem.

---

## 1. Связь с нашей моделью

- **Контракт:** SoulboundCore хранит владение SBT (tokenId → owner); SoulMetadata — metadataType, version, attributes (JSON: level, reputation), ipfsHash; SoulIdentity — привязка адрес ↔ DID и внешние идентичности (identityType, identityValue, verified).
- **Цель VC:** переносить «душу» и репутацию в DID-мир: один и тот же DID может предъявлять credential с level, reputation и ссылкой на ончейн-душу; несколько сообществ (communityId) в одной экосистеме (ecosystem).

---

## 2. Credential type и credentialSubject

**Тип credential:** `AmanitaSoulReputationCredential` (или коротко `SoulReputation`).

**credentialSubject** — минимальный набор полей, совместимый с контрактами и multi-community:

| Поле | Тип | Обязательность | Описание |
|------|-----|----------------|----------|
| `id` | string (URI) | required | DID субъекта (например `did:polygonid:polygon:amoy:...` или `did:privado:...`) |
| `soulChainId` | integer | required | chainId сети, где заминтирована душа (например 137 для Polygon Mainnet, 80002 для Amoy) |
| `soulContractAddress` | string | required | Адрес контракта SoulboundCore (checksum) |
| `soulTokenId` | string | required | tokenId SBT души (строка для совместимости с JSON, число в контракте) |
| `level` | integer | required | Уровень души (соответствует getSoulLevel в контракте) |
| `reputation` | integer | required | Репутация души (соответствует getSoulReputation) |
| `ecosystem` | string | required | Идентификатор экосистемы (например `"amanita"`) |
| `communityId` | string | optional | Идентификатор сообщества внутри экосистемы (reputation-driven multi-community) |
| `walletAddress` | string | optional | Адрес кошелька, привязанный к DID на момент выдачи (для верификации ончейн) |
| `activatedAt` | string (date-time) | optional | Время активации в SpiralEngine (ISO 8601) |
| `version` | integer | optional | Версия метаданных души (соответствует SoulData.version) |

Поля `soulChainId`, `soulContractAddress`, `soulTokenId` однозначно задают ончейн-душу; `level` и `reputation` могут дублировать контракт для оффчейн-проверок без чтения блокчейна. `communityId` и `ecosystem` поддерживают сценарий «несколько сообществ в одной экосистеме» и репутацию по сообществу.

---

## 3. Пример VC (Verifiable Credential) в формате Privado/Polygon ID

```json
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://raw.githubusercontent.com/amanita-ecosystem/schemas/main/amanita-soul-reputation.jsonld#AmanitaSoulReputationCredential"
  ],
  "id": "urn:uuid:...",
  "type": ["VerifiableCredential", "AmanitaSoulReputationCredential"],
  "issuer": "did:polygonid:polygon:amoy:...",
  "issuanceDate": "2026-03-14T12:00:00Z",
  "expirationDate": "2027-03-14T12:00:00Z",
  "credentialSchema": {
    "id": "https://raw.githubusercontent.com/amanita-ecosystem/schemas/main/amanita-soul-reputation.json",
    "type": "JsonSchemaValidator2018"
  },
  "credentialSubject": {
    "id": "did:polygonid:polygon:amoy:2qNBWSAsyvaGBpqQVHk3E4cgChaN6ogaZnYCQUyoRQ",
    "soulChainId": 80002,
    "soulContractAddress": "0x...",
    "soulTokenId": "1",
    "level": 1,
    "reputation": 100,
    "ecosystem": "amanita",
    "communityId": "spiral",
    "walletAddress": "0x...",
    "activatedAt": "2026-03-14T11:00:00Z",
    "version": 1
  },
  "credentialStatus": { ... },
  "proof": { ... }
}
```

---

## 4. JSON-LD Context (фрагмент для credentialSubject)

Файл `amanita-soul-reputation.jsonld` (публичный URL для Privado):

```json
{
  "@context": [
    { "@version": 1.1, "@protected": true },
    "https://www.w3.org/2018/credentials/v1",
    {
      "AmanitaSoulReputationCredential": {
        "@id": "https://raw.githubusercontent.com/amanita-ecosystem/schemas/main/amanita-soul-reputation.jsonld#AmanitaSoulReputationCredential",
        "@context": {
          "@version": 1.1,
          "@protected": true,
          "id": "@id",
          "type": "@type",
          "xsd": "http://www.w3.org/2001/XMLSchema#",
          "soulChainId": { "@id": "vocab:soulChainId", "@type": "xsd:integer" },
          "soulContractAddress": { "@id": "vocab:soulContractAddress", "@type": "xsd:string" },
          "soulTokenId": { "@id": "vocab:soulTokenId", "@type": "xsd:string" },
          "level": { "@id": "vocab:level", "@type": "xsd:integer" },
          "reputation": { "@id": "vocab:reputation", "@type": "xsd:integer" },
          "ecosystem": { "@id": "vocab:ecosystem", "@type": "xsd:string" },
          "communityId": { "@id": "vocab:communityId", "@type": "xsd:string" },
          "walletAddress": { "@id": "vocab:walletAddress", "@type": "xsd:string" },
          "activatedAt": { "@id": "vocab:activatedAt", "@type": "xsd:dateTime" },
          "version": { "@id": "vocab:version", "@type": "xsd:integer" }
        }
      }
    }
  ]
}
```

(В полной версии добавить `vocab` base URL в начало @context.)

---

## 5. JSON Schema для Issuer Node (Privado)

Файл `amanita-soul-reputation.json` (валидация credentialSubject):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "$metadata": {
    "uris": {
      "jsonLdContext": "https://raw.githubusercontent.com/amanita-ecosystem/schemas/main/amanita-soul-reputation.jsonld",
      "jsonSchema": "https://raw.githubusercontent.com/amanita-ecosystem/schemas/main/amanita-soul-reputation.json"
    }
  },
  "required": ["@context", "id", "type", "issuanceDate", "credentialSubject", "credentialSchema", "credentialStatus", "issuer"],
  "properties": {
    "@context": { "type": ["string", "array", "object"] },
    "id": { "type": "string" },
    "type": { "type": ["string", "array"], "items": { "type": "string" } },
    "issuer": { "type": ["string", "object"], "format": "uri", "required": ["id"], "properties": { "id": { "type": "string", "format": "uri" } } },
    "issuanceDate": { "type": "string", "format": "date-time" },
    "expirationDate": { "type": "string", "format": "date-time" },
    "credentialSchema": { "type": "object", "required": ["id", "type"], "properties": { "id": { "type": "string", "format": "uri" }, "type": { "type": "string" } } },
    "credentialStatus": { "type": "object" },
    "credentialSubject": {
      "type": "object",
      "required": ["id", "soulChainId", "soulContractAddress", "soulTokenId", "level", "reputation", "ecosystem"],
      "properties": {
        "id": { "title": "Credential Subject ID (DID)", "type": "string", "format": "uri" },
        "soulChainId": { "type": "integer", "description": "Chain ID where SoulboundCore is deployed" },
        "soulContractAddress": { "type": "string", "pattern": "^0x[a-fA-F0-9]{40}$", "description": "SoulboundCore contract address" },
        "soulTokenId": { "type": "string", "description": "SBT token ID (string representation)" },
        "level": { "type": "integer", "minimum": 0, "description": "Soul level (on-chain getSoulLevel)" },
        "reputation": { "type": "integer", "minimum": 0, "description": "Soul reputation (on-chain getSoulReputation)" },
        "ecosystem": { "type": "string", "description": "Ecosystem identifier (e.g. amanita)" },
        "communityId": { "type": "string", "description": "Community within ecosystem (reputation-driven multi-community)" },
        "walletAddress": { "type": "string", "pattern": "^0x[a-fA-F0-9]{40}$" },
        "activatedAt": { "type": "string", "format": "date-time" },
        "version": { "type": "integer", "minimum": 0 }
      }
    }
  }
}
```

---

## 6. Соответствие контрактам и multi-community

- **SoulboundCore:** `soulContractAddress` + `soulTokenId` + `soulChainId` задают единственную душу в нашей архитектуре; по ним можно проверить ownerOf на нужной сети.
- **SoulMetadata / SoulIdentity:** `level` и `reputation` соответствуют getSoulLevel/getSoulReputation; `version` — SoulData.version. Привязка DID к адресу в контракте (linkExternalIdentity) может хранить тот же DID, что и `credentialSubject.id`.
- **Reputation-driven multi-community:** поле `ecosystem` (одна экосистема, например Amanita) и опциональное `communityId` (конкретное сообщество внутри неё) позволяют выдавать разные credential для разных сообществ и строить репутацию по communityId без изменения контракта; контракт при необходимости может хранить communityId в метаданных или в атрибутах (отдельная доработка).

Документ можно использовать как основу для регистрации схемы в Privado ID (Schema Builder / репозиторий схем) и для выдачи VC при минтинге души или обновлении level/reputation.

---

## 7. Процесс issuing (выдача credential)

1. **Ончейн-событие:** в сообществе пользователь активируется (SpiralEngine.activateUser), минтится душа в SoulboundCore этого сообщества (свой адрес контракта, свой chainId).
2. **Запрос VC:** бэкенд сообщества (или кошелёк пользователя) вызывает API Issuer Node с данными для credentialSubject: DID пользователя (id), soulChainId, soulContractAddress, soulTokenId, level, reputation, ecosystem, communityId.
3. **Issuer Node:** проверяет (по необходимости) ончейн: ownerOf(soulContractAddress, soulTokenId) на soulChainId совпадает с адресом, от имени которого запрошен credential; подписывает VC по зарегистрированной схеме AmanitaSoulReputationCredential; публикует состояние в State Contract (Privado/Polygon), при использовании RHS — обновляет revocation.
4. **Выдача:** VC возвращается держателю (кошелёк / хранилище в Privado ID). Держатель может предъявлять VC верификаторам без раскрытия всех полей (ZK).

Схема и JSON-LD контекст — общие для всех сообществ протокола; данные в credentialSubject (адреса контрактов, communityId) различаются по сообществу.

---

## 8. Кто может становиться issuing node

- **Любое сообщество (круг), следующее протоколу:** тот, кто разворачивает свой набор контрактов (SpiralEngine, SoulboundCore, SoulMetadata, SoulIdentity и т.д.) и хочет выдавать Verifiable Credentials по схеме Amanita Soul & Reputation, поднимает **свой** Issuer Node (Privado ID Issuer Node).
- **Требования к Issuer Node (по документации Privado ID):** запуск экземпляра Issuer Node (Docker, Go 1.19+, Makefile), настройка KMS (Local Storage только для тестов; для продакшена — HashiCorp Vault, AWS Secrets Manager или AWS KMS), импорт Ethereum-ключа для state transitions, настройка `resolvers_settings.yaml` под нужные сети (например Polygon Amoy/Mainnet и/или Privado Identity Chain для Web Wallet / Wallet App).
- **Идентичность issuer’а:** у каждого Issuer Node — своя идентичность (DID), ключи которой хранятся в KMS. Поле `issuer` в VC будет разным у разных сообществ (разные DID), при этом `credentialSchema` и тип credential — одни и те же (`AmanitaSoulReputationCredential`), что обеспечивает интероперабельность.
- **Роль сообщества:** сообщество определяет политику, кто вправе запрашивать выдачу VC (например только для активированных пользователей с заминтированной душой в их SoulboundCore) и при необходимости реализует backend-сервис, который вызывает Issuer Node API после проверки ончейн-состояния.

---

## 9. Валидация между разными сообществами

- **Единая схема, разные issuer’ы:** верификатор проверяет, что VC имеет тип `AmanitaSoulReputationCredential` и соответствует зарегистрированной JSON Schema (в т.ч. обязательные поля credentialSubject). Доверие к конкретному сообществу — через `issuer` (DID issuer’а): верификатор может держать allow-list DID’ов сообществ протокола или доверять любому issuer’у, выпускающему credential по этой схеме.
- **Проверка ончейн-души:** для анти-сибил и актуальности верификатор может проверить, что на сети `soulChainId` контракт `soulContractAddress` действительно выдаёт SBT с `soulTokenId` и что текущий owner и/или level/reputation согласованы с заявленным (или что credential не просрочен). Так как каждое сообщество деплоит контракты на своих адресах, `soulContractAddress` + `soulChainId` однозначно идентифицируют «круг» и контракт; подделка души другого сообщества невозможна без контроля того контракта.
- **Revocation:** статус отзыва credential проверяется по механизму Privado (RHS: Centralized / Off Chain / On Chain). Каждый issuer (сообщество) ведёт свой revocation; кросс-проверки между сообществами не требуются для базовой валидации VC.
- **Репутация по сообществу:** поле `communityId` в credentialSubject позволяет верификатору интерпретировать level/reputation в контексте конкретного сообщества; при кросс-комьюнити сценарии верификатор видит несколько VC одного и того же DID с разными communityId и может строить агрегированную или контекстную оценку по своей политике.

---

## 10. Независимые концентрические круги и один протокол

- **Модель:** каждое сообщество **независимо** деплоит полный набор контрактов (SpiralEngine, SoulboundCore, SoulMetadata, SoulIdentity и т.д.) на выбранных сетях и адресах. Точки входа (инвайт-система, минт душ, роли) — свои у каждого круга. При этом все следуют **одному протоколу** (одни и те же интерфейсы, один и тот же стандарт токенов SBT, одна и та же схема VC AmanitaSoulReputationCredential).
- **Токены:** души майнятся по одному стандарту (один и тот же контракт SoulboundCore, возможно один и тот же байткод), но на разных адресах и при необходимости в разных сетях. Идентификатор «души в экосистеме» — тройка (soulChainId, soulContractAddress, soulTokenId).
- **Итог:** получается система **независимых концентрических кругов**, работающих по одному протоколу на разных адресах; интероперабельность достигается за счёт общей схемы credential и единого формата ссылки на душу в VC.

---

## 11. Интероперабельный DID и репутационная база

- **Один DID — много сообществ:** один и тот же DID (например Privado ID / Polygon ID) может владеть **несколькими** AmanitaSoulReputationCredential от разных сообществ: в каждом credential свой `communityId`, свой `soulContractAddress` / soulTokenId (душа заминтирована в контракте этого сообщества). Таким образом один человек в разных сообществах может быть разной «профессиональной личностью» (разная репутация, разный level в каждом круге).
- **Внутри сообщества:** репутационная база сообщества примарна для этого круга: уровень и репутация в нём определяются локальными правилами и ончейн-состоянием контрактов этого сообщества; VC с данным communityId отражает именно эту примарную репутацию.
- **Кросс-комьюнити маркетплейс:** на уровне экосистемы (например единый маркетплейс или агрегатор) репутационная база объединяется **холистически**: один и тот же человек (один DID) виден в нескольких сообществах; UI/верификатор может показывать «одно и то же лицо в разных кругах» — несколько credential с разными communityId и разными level/reputation, без слияния идентичностей в одну. Целостность обеспечивается общим протоколом и схемой, а не единым контрактом.
- **Резюме:** интероперабельный DID позволяет в каждом сообществе собирать свою репутационную базу (примарную внутри круга), а на кросс-комьюнити уровне — объединять вид холистически (один человек, несколько ролей/репутаций по сообществам), при этом все круги независимо деплоят контракты и работают по одному протоколу и одной схеме VC.
