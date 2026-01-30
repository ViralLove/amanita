# Квалификация тестов: ActivityRegistry.UUPS.comprehensive.test.js

**Правило:** @test-qualification.mdc  
**Дата:** 2026-01-29 (повторная проверка)  
**Цель:** Честная проверка на false successes, некорректные утверждения и непокрытые критические пути.

---

## Применённые правила

| ID | Приоритет | Описание |
|----|-----------|----------|
| NO_FALSE_SUCCESSES | P0 | Тесты не должны проходить при сломанной функциональности |
| VALIDATE_REAL_FUNCTIONALITY | P0 | Тесты проверяют реальное поведение, не побочные эффекты |
| NO_UNTESTED_CRITICAL_PATHS | P0 | Все критические пути должны быть покрыты |
| CORRECT_LOGIC | P1 | Утверждения осмысленны, не тавтологии |
| MINIMAL_MOCK_OVERUSE | P2 | Не перегружать моками |

---

## P0 — Обнаруженные пробелы

### 1. NO_UNTESTED_CRITICAL_PATHS: upgradeToAndCall только от UPGRADER_ROLE
- **Архитектура:** _authorizeUpgrade — onlyRole(UPGRADER_ROLE). Не-админ не должен иметь возможность апгрейда.
- **Сейчас:** Тестируется только успешный апгрейд (admin) в Full State Preservation. Вызов upgradeToAndCall от creator не проверяется.
- **Риск:** При удалении onlyRole(UPGRADER_ROLE) тесты останутся зелёными.
- **Рекомендация:** Добавить тест: creator вызывает upgradeToAndCall(newLogic, "0x") — ожидать revert (AccessControlUnauthorizedAccount или аналог).

### 2. NO_UNTESTED_CRITICAL_PATHS: повторная инициализация (double initialize)
- **Архитектура:** initialize — initializer, вызывается один раз при деплое Proxy.
- **Сейчас:** Нет теста на повторный вызов initialize(admin, spiralEngine) от admin.
- **Риск:** При снятии initializer повторный вызов может перезаписать роли.
- **Рекомендация:** Добавить тест: activityRegistry.connect(admin).initialize(admin.address, await spiralEngine.getAddress()) — ожидать InvalidInitialization (OpenZeppelin).

### 3. NO_UNTESTED_CRITICAL_PATHS: publishedActivityIds после deactivate
- **Архитектура:** deactivateActivity делает swap-and-pop, id должен исчезнуть из getPublishedActivityIds().
- **Сейчас:** Проверяется только active = false после deactivate; массив getPublishedActivityIds() явно не проверяется на отсутствие id.
- **Риск:** При сломанном swap-and-pop id останется в списке — тест не упадёт.
- **Рекомендация:** В одном из тестов (или отдельно): после activate(1) → getPublishedActivityIds() содержит [1]; после deactivate(1) → getPublishedActivityIds() пустой или не содержит 1.

---

## P1 — Замечания

### 4. VALIDATE_REAL_FUNCTIONALITY: после setSpiralEngine создание использует новый engine
- **Сейчас:** Проверяется только spiralEngine() === newAddr и событие SpiralEngineUpdated.
- **Дополнительно:** Можно добавить тест: setSpiralEngine(spiral2); на spiral2 creator не активирован → createActivity от creator ревертит (если новый engine не выдал роль). Или наоборот: spiral2 с тем же creator активирован → createActivity успешен. Это подтверждает, что контракт реально использует новый адрес. Опционально P1.

### 5. CORRECT_LOGIC: хелпер expectNotReverted не используется
- **Сейчас:** expectNotReverted объявлен, в файле не вызывается.
- **Рекомендация:** P2 — удалить неиспользуемый хелпер или использовать в подходящем тесте (например, expectNotReverted(activityRegistry.connect(admin).unpause())).

---

## P2

### 6. MINIMAL_MOCK_OVERUSE
- MockSpiralEngine используется обоснованно. Замечаний нет.

---

## Итог и действия

| Приоритет | Найдено | Действие |
|-----------|---------|----------|
| P0        | 3       | Добавить тесты: upgradeToAndCall от не-UPGRADER; double initialize; после deactivate getPublishedActivityIds не содержит id |
| P1        | 2       | Опционально: тест после setSpiralEngine; expectNotReverted использовать или удалить |
| P2        | 0       | — |

---

## Внесённые правки (по результатам квалификации 2026-01-29)

1. **P0:** Добавлен тест «повторный initialize ревертит с InvalidInitialization» (Deployment and initialization).
2. **P0:** Добавлен тест «upgradeToAndCall от не-UPGRADER ревертит с AccessControlUnauthorizedAccount» (Deployment and initialization).
3. **P0:** Добавлен тест «после deactivate getPublishedActivityIds не содержит id (swap-and-pop)» (Activate and deactivate).

Итого: 35 тестов, все проходят. P0 пробелы закрыты.

---

## Метрики газа (4.3, REPORT_GAS=true)

| Метод | Avg gas | Примечание |
|-------|---------|------------|
| createActivity | 172638 | Min 146949, Max 181245 |
| activateActivity | 102044 | |
| deactivateActivity | 43668 | |
| pause | 54402 | |
| unpause | 32122 | |
| setSpiralEngine | 40220 | |
| upgradeToAndCall | 37410 | |
