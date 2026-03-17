# Amanita SBT Architecture — сводный анализ

**Папка:** `contracts/docs/Amanita-SBT-Architecture`  
**Назначение:** единая точка входа по архитектуре SBT-экосистемы и SpiralEngine: факты из кода, связи контрактов, соответствие целям.

---

## Документы (порядок чтения)

| № | Документ | Содержание |
|---|----------|------------|
| **01** | [01-SBT-ecosystem-and-SpiralEngine-analysis.md](./01-SBT-ecosystem-and-SpiralEngine-analysis.md) | Глубокий разбор SBT-экосистемы и связи с SpiralEngine: SoulboundCore, SoulMetadata, SoulIdentity, SoulRecovery, SoulIntegration; заглушки и зоны доработки. |
| **02** | [02-SBT-next-level-social-self-identity.md](./02-SBT-next-level-social-self-identity.md) | SBT как ступень к социальным связям и самоидентификации: инвайт → активация → душа → DID → guardian; что в коде есть и что не доведено. |
| **03** | [03-contracts-relationships-diagram.md](./03-contracts-relationships-diagram.md) | Схема связей контрактов в стиле реляционной модели (ER + flowchart), без UUPS. |
| **04** | [04-critical-audit-goals.md](./04-critical-audit-goals.md) | Критический аудит на соответствие целям: инвайты/SpiralEngine, Multi Chain Amanita Passport, доверенные лица и recovery (в т.ч. хранение ключей). |
| **05** | [05-recovery-mode-comparative-analysis.md](./05-recovery-mode-comparative-analysis.md) | Сравнение режимов восстановления: перенос на другой адрес (текущая реализация) vs возврат доступа к тому же адресу (передача ключей, временный ключ, MPC). |
| **06** | [06-identity-did-invite-sbt-metadata-audit.md](./06-identity-did-invite-sbt-metadata-audit.md) | Аудит: создание идентичности и окно для DID; инвайт vs SBT (роль и разделение); SoulboundCore и хранение метаданных; избыточность; дыры архитектуры (удобство и безопасность). |
| **07** | [07-privado-did-credential-schema.md](./07-privado-did-credential-schema.md) | Privado DID: схема VC (credentialSubject, JSON-LD, JSON Schema); процесс issuing; кто может быть issuing node; валидация между сообществами; независимые концентрические круги (один протокол, разные адреса); интероперабельный DID и холистическая репутация на кросс-комьюнити маркетплейсе. |
| **08** | [08-personhood-driven-federated-identity-model.md](./08-personhood-driven-federated-identity-model.md) | Amanita Passport как personhood-driven federated identity model: DID per community, automatic orchestration, displayName + community-prefixed handle, федеративная репутация, X как интерфейс и social-mining layer, биометрия только как local key unlock. |
| **09** | [09-x-love-do-feasibility-analysis.md](./09-x-love-do-feasibility-analysis.md) | Feasibility-анализ X-интеграции для LoveDo: X как discovery-transport, кросспостинг X post -> LoveDo token через proxy/orchestrator, ограничения raw X likes и модель qualified likes -> superlikes -> social mining. |
| **10** | [10-amanita-passport-mvp-scope.md](./10-amanita-passport-mvp-scope.md) | Минимально необходимый функционал Amanita Passport MVP: один community/сеть, активация→душа, профиль (displayName, handle, soul, DID, X опционально), recovery, границы с SpiralEngine/LoveDo/X и список вне MVP. |

---

## Исходные файлы (для ссылок)

- Анализ 01 изначально: `contracts/docs/SBT-ecosystem-and-SpiralEngine-analysis.md`
- Анализ 02: `contracts/docs/SBT-next-level-social-self-identity-analysis.md`
- Схема 03: `contracts/docs/contracts-relationships-diagram.md`
- Аудит 04: создан в этой папке.

Алилуя! Аминь.
