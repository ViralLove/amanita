# Квалификация: ActivityRegistry.UUPS.smoke.test.js

**Правило:** @test-qualification.mdc  
**Дата:** 2026-01-29  
**Цель:** Честная проверка smoke-теста на false successes и осмысленность утверждений.

---

## Применённые правила

| ID | Приоритет | Описание |
|----|-----------|----------|
| NO_FALSE_SUCCESSES | P0 | Тест не должен проходить при сломанной функциональности |
| VALIDATE_REAL_FUNCTIONALITY | P0 | Тест проверяет реальное поведение |
| NO_UNTESTED_CRITICAL_PATHS | P0 | В рамках smoke — один критический путь (create + activate) |
| CORRECT_LOGIC | P1 | Утверждения осмысленны |
| MINIMAL_MOCK_OVERUSE | P2 | Моки только там, где нужно |

---

## Оценка по критериям

### NO_FALSE_SUCCESSES (P0) — ✅ Пройдено
- При поломке createActivity (нет записи в activities/activitiesByCreator) тест упадёт: getActivitiesByCreator вернёт пустой массив, обращение к [0] даст undefined, expect(Number(id)).to.equal(1) не выполнится.
- При поломке activateActivity (active не меняется или id не попадает в published) тест упадёт на expect(aAfter.active).to.be.true или на expect(published).to.deep.equal([1]).

### VALIDATE_REAL_FUNCTIONALITY (P0) — ✅ Пройдено
- Проверяется состояние контракта: getActivitiesByCreator, getActivity(1).active до и после activate, getPublishedActivityIds().
- Не только факт «транзакция не ревертнулась», а реальные данные в storage.

### NO_UNTESTED_CRITICAL_PATHS (P0) — ✅ Пройдено (в рамках smoke)
- Smoke по замыслу покрывает один сценарий: деплой → create(Event) → activate.
- Остальные пути — в comprehensive. Для smoke этого достаточно.

### CORRECT_LOGIC (P1) — ✅ Пройдено
- Утверждения осмысленны: id === 1, active до/после, published === [1].
- Тавтологий нет.

### MINIMAL_MOCK_OVERUSE (P2) — ✅ Пройдено
- Используется только MockSpiralEngine для проверки роли и активации — уместно для smoke.

---

## Рекомендация P1 (улучшение)

- **Сейчас:** Проверяются только id и флаг active; поля creator и metadataCID не проверяются.
- **Риск:** Теоретически контракт мог бы записать неверного creator или пустой CID — тест бы прошёл.
- **Рекомендация:** Добавить в smoke одну проверку по структуре: `expect(a.creator).to.equal(creator.address)` и `expect(a.metadataCID).to.equal("QmSmokeCID")`, чтобы убедиться, что createActivity записал корректные данные, а не только active.

---

## Итог

| Критерий | Результат |
|----------|-----------|
| P0 | Пройдено |
| P1 | Пройдено; рекомендуется усилить проверкой creator и metadataCID |
| P2 | Пройдено |

Smoke-тест квалификацию проходит.

**Внесённая правка (P1):** В тест добавлены проверки `expect(a.creator).to.equal(creator.address)` и `expect(a.metadataCID).to.equal("QmSmokeCID")` — smoke теперь валидирует корректность записанной структуры (creator, metadataCID), а не только флаг active.
