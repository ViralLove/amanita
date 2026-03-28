# Passport и X: опциональная интеграция (схема)

**Версия:** 1.0  
**Дата:** 2026-03-16  
**Назначение:** единая точка входа — как Amanita Passport интегрируется с X (Twitter): привязка, discovery, превью и **явные границы** (X не source of truth).  
**Связанные документы:** [08-personhood-driven-federated-identity-model.md](../../contracts/docs/Amanita-SBT-Architecture/08-personhood-driven-federated-identity-model.md) (разд. 11), [09-x-love-do-feasibility-analysis.md](../../contracts/docs/Amanita-SBT-Architecture/09-x-love-do-feasibility-analysis.md), [10-amanita-passport-mvp-scope.md](../../contracts/docs/Amanita-SBT-Architecture/10-amanita-passport-mvp-scope.md).

---

## 1. Границы интеграции (обязательно к соблюдению)

- **X не является source of truth для репутации.** Репутация и доверие в Amanita строятся на soul, DID, invite-circle и ончейн/оффчейн данных протокола, а не на лайках или метриках X.
- **Passport не зависит от X онтологически.** Ценность Passport — в soul, DID и репутации внутри экосистемы; X — опциональный интерфейс и канал discovery, не замена идентичности.
- **Привязка X к Passport — опциональная.** Пользователь может не иметь X-аккаунта; Passport и все функции (профиль, recovery, LoveDo) работают без X.

---

## 2. Привязка X-аккаунта к Passport (external identity)

- **Механизм:** привязка реализуется как **external identity** в SoulIdentity: вызов `linkExternalIdentity(user, identityType, identityValue, verified)` (роль `SPIRAL_ENGINE_ROLE` или self-service при наличии соответствующего метода оркестратора).
- **Формат хранения:** тип идентичности — например `"x"` или `"twitter"`; значение — X handle (например `@username`) и/или profile URL; при необходимости в атрибутах или оффчейн хранят `xUserId`, `xProfileUrl`, `xLinkedAt`, `xVerificationStatus` как внешние маркеры.
- **Кто может устанавливать:** в текущей реализации — оркестратор/бэкенд с ролью SPIRAL_ENGINE_ROLE; при добавлении self-service (например через Sign in with X + верификацию владельца души) — документировать в этом месте.
- Это именно **external identity link**, а не замена soul или DID.

---

## 3. Использование X для discovery

- **Passport URL:** у каждого Passport / community profile есть публичный web URL; по нему возможен переход с X и обратная привязка «X → Passport».
- **Preview cards:** при публикации ссылки на Passport/профиль в X отображается rich preview (Open Graph / X card meta tags): displayName, handle, сообщество, ключевые маркеры репутации, визуальная карточка. Для X это просто shareable page; нативная модель DID не требуется.
- **Sign in with X:** опционально — для привязки X-аккаунта к Passport и упрощения входа; не обязательно для работы Passport.

---

## 4. Использование X для превью профиля

- При шаринге ссылки на Passport в X показывается превью профиля (карточка с displayName, handle, community, репутационными маркерами). Данные для карточки берутся из ончейн/оффчейн источников Amanita, а не из X; X только отображает метаданные страницы.

---

## 5. Ограничения (API X, эксплуатация)

- X может менять API-условия, rate limits, стоимость и политику доступа. Preview-карточки и социальный трафик зависят от интерфейса X, а не от протокола Amanita.
- Интеграция должна быть устойчивой к недоступности или изменению X API; ценность Passport не должна от этого страдать.

---

## 6. Чего нет в этой интеграции (MVP)

- **X post → LoveDo token** и **X likes → on-chain superlikes** не входят в MVP как автоматический ончейн-поток. Superlike остаётся доверительным действием внутри invite-circle (док. 09). При появлении таких сценариев — отдельная схема и документ.

---

## 7. Проверка соответствия DoD Passport MVP

- Документ доступен в репозитории: `docs/tech/X-Integration-Schema.md`.
- Описаны: привязка X как external identity (формат, кто устанавливает); discovery (Passport URL, preview cards, Sign in with X при необходимости); превью профиля при шаринге.
- Явно зафиксировано: X **не** source of truth для репутации; Passport не зависит от X онтологически; ценность Passport — в soul, DID и репутации.
- Ссылка на документ добавлена в 10-amanita-passport-mvp-scope.md.
