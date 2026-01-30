# Описание изменений: ActivityRegistry (Task 1)

## Дата изменений
2026-01-29

## Общая статистика
- **Scope:** только артефакты Task 1 (ActivityRegistry контракт, тесты, документация).
- **Группы изменений:** 3 (Core, Tests, Documentation).

---

## Группа 1: Core — контракты ActivityRegistry и мок

### Файлы
- `contracts/ActivityRegistryLogic.sol`
- `contracts/ActivityRegistryProxy.sol`
- `contracts/interfaces/IActivityRegistry.sol`
- `contracts/mocks/MockSpiralEngine.sol`

### Что изменено
- Добавлены ActivityRegistryLogic (UUPS), ActivityRegistryProxy (ERC1967Proxy), IActivityRegistry (интерфейс). Модель: ActivityType, Activity (id, creator, activity_type, metadataCID, active); createActivity, getActivity, activateActivity, deactivateActivity, getActivitiesByCreator, getPublishedActivityIds; pause/unpause, setSpiralEngine, forceDeactivate; интеграция с SpiralEngine (ACTIVITY_CREATOR_ROLE, usedInviteByUser).
- MockSpiralEngine: поддержка ACTIVITY_CREATOR_ROLE для тестов ActivityRegistry (если изменён).

### Цель изменений
Реализация контракта-источника истины для активностей (events/services) в экосистеме Amanita; блокирует Epic Activities API Phase 1.

---

## Группа 2: Tests — тесты ActivityRegistry и хелперы

### Файлы
- `contracts/tests/ActivityRegistry.MockSpiralEngine.phase0.test.js`
- `contracts/tests/ActivityRegistry.UUPS.comprehensive.test.js`
- `contracts/tests/ActivityRegistry.UUPS.smoke.test.js`
- `contracts/tests/helpers/testHelpers.js`
- `contracts/tests/ActivityRegistry.UUPS.comprehensive.qualification.md`
- `contracts/tests/ActivityRegistry.UUPS.smoke.qualification.md`

### Что изменено
- Comprehensive и smoke тесты для ActivityRegistry (UUPS Proxy+Logic); хелперы expectRevertCustom, expectEvent и др. в helpers/testHelpers.js; квалификационные отчёты по тестам.

### Цель изменений
Покрытие P0/P1 по solution-architecture; квалификация набора тестов.

---

## Группа 3: Documentation — документация контракта и таска

### Файлы
- `contracts/docs/ActivityRegistry.md`
- `contracts/docs/roles-architecture-synthesis.md` — канонический архитектурный документ по системе ролей (перенесён в корень доков контрактов; self-explainable имя).
- Зеркало для синхронизации: `contracts/docs/analysis/tasks/task-Activities-1/roles-architecture-synthesis.md` (указывает на канонический файл).

### Что изменено
- ActivityRegistry.md: API, модель данных, события, роли, деплой; ссылка на роли ведёт на канонический документ в корне.
- Роли экосистемы: канонический документ **roles-architecture-synthesis.md** в корне `contracts/docs/`; в папке таска — зеркало для синхронизации ссылок.
- Анализ и план по Task 1: solution-architecture, ретроспективы фаз, оценка приёмки, decision-points; ссылки на роли обновлены на канонический путь.

### Цель изменений
Закрытие критерия «документация контракта»; фиксация архитектуры, решений и уроков по Task 1.
