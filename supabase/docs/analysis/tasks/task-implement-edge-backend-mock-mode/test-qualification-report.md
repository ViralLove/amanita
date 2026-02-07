# Test Qualification Report: backend mock + publish flow

**Правило:** @test-qualification.mdc (v2)  
**Объект:** `supabase/functions/arweave-upload/tests/backend-mock.test.ts`, `publish-flow.test.ts`  
**Дата:** 2026-02-07

---

## Что сделано (созданные и доработанные тесты)

### backend-mock.test.ts (8 тестов, после доработки по test-improvements-plan.md)

| Тест | Заявленная цель | Что реально проверяется |
|------|-----------------|-------------------------|
| BACKEND_USE_MOCK=true → putStatus не вызывает fetch | Мок включён → нет HTTP к Backend | 401, code token_invalid, fetchCalls.length === 0 |
| override через BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE | Значение из заголовка в putStatus | 401, fetchCalls.length === 0, **getPutStatusSimulatedStatus(logCalls) === 409** |
| override через X-Backend-Mock-Secret | Значение из заголовка в putStatus | 401, fetchCalls.length === 0, **getPutStatusSimulatedStatus(logCalls) === 404** |
| без override, секрет не совпадает | Заголовки игнорируются, используется env | 401, fetchCalls.length === 0, **BACKEND_MOCK_PUT_STATUS=404, заголовок 409 → simulatedStatus === 404** (перехват лога) |
| **мок выключен → putStatus вызывает fetch** | При выключенном моке бекенд вызывается | fetchCalls.length === 1, PUT с token_invalid, URL содержит /uploads/ и status |
| **мок 200 по умолчанию** | Вариант ответа 200 | перехват лога → simulatedStatus === 200 |
| **мок 404 из env** | BACKEND_MOCK_PUT_STATUS=404 | перехват лога → simulatedStatus === 404 |
| **мок 409 из заголовка** | Override разрешён, значение из заголовка | перехват лога → simulatedStatus === 409 |

### publish-flow.test.ts (4 теста, существующие)

Проверяют: 400 при пустом теле и отсутствие putStatus; 401 при невалидном токене и вызов putStatus(failed, token_invalid); 400 при невалидном data item и putStatus(signature_invalid); 200 при валидном потоке и putStatus(queued_for_publish). Используется подмена `fetch` для проверки вызовов к Backend.

---

## Оценка по правилам (test-qualification)

### NO_FALSE_SUCCESSES (P0)

- **backend-mock, тест 1:** Если убрать проверку `BACKEND_USE_MOCK` и всегда ходить в fetch, тест упадёт (fetchCalls.length > 0). **OK.**
- **backend-mock, тесты override (2–3):** Проверяется «нет fetch», 401 и **simulatedStatus в логе** (409, 404). Если убрать передачу override в putStatus, тест упадёт (ожидаемый код в логе не совпадёт). **OK (после доработки).**
- **backend-mock, тест «неверный секрет»:** Задаётся env 404, заголовок 409; утверждается **simulatedStatus === 404** из перехваченного лога. При ошибочном учёте заголовка было бы 409 — тест упадёт. **OK (после доработки).**
- **backend-mock, тест «мок выключен»:** Утверждается fetchCalls.length >= 1 и PUT к Backend. **OK.**

### VALIDATE_REAL_FUNCTIONALITY (P0)

- **backend-mock:** Проверяется реальное поведение «при моке fetch не вызывается» и **реальное значение simulatedStatus в логе** (200, 404, 409 из env или заголовка); при выключенном моке — вызов fetch. **OK (после доработки).**
- **publish-flow:** Проверяется реальное поведение handler (коды ответа, тело, вызов putStatus через перехват fetch). **OK.**

### NO_UNTESTED_CRITICAL_PATHS (P0)

- **Покрыто после доработки:** использование кода 200/404/409 из env и из заголовка (тесты с перехватом лога); «неверный секрет → заголовок не используется» (тест с env 404, заголовок 409, assert simulatedStatus 404); «мок выключен → fetch вызывается».
- **Не покрыто (приемлемо):** мок postCallback — вызывается только после успешной публикации в Arweave (асинхронный путь); для изолированного теста без реального Arweave сценарий не воспроизводится. Оставлено как опциональный P2 в плане.

### CORRECT_LOGIC (P1)

- Тесты override и «неверный секрет» после доработки проверяют **значение simulatedStatus в логе** — утверждения соответствуют проверкам. **OK.**

### MINIMAL_MOCK_OVERUSE (P2)

- Подмена `fetch` здесь уместна: изолируем handler и проверяем вызовы к Backend / их отсутствие. **OK.**

---

## Итоги тестирования: что стало понятно (после доработки)

1. **Подтверждено:** при `BACKEND_USE_MOCK=true` putStatus не дергает fetch; при невалидном токене 401 и нет сетевых вызовов; варианты 200/404/409 проверяются по перехваченному логу (simulatedStatus).
2. **Подтверждено:** при разрешённом override (ALLOW_REQUEST_OVERRIDE или верный X-Backend-Mock-Secret) значение из заголовка попадает в putStatus — в логе simulatedStatus совпадает с заголовком (409, 404).
3. **Подтверждено:** при неверном секрете заголовок переопределения игнорируется — в тесте env 404, заголовок 409, в логе simulatedStatus 404.
4. **Подтверждено:** при выключенном моке putStatus вызывает fetch к Backend (тест проверяет fetchCalls и URL/body).
5. **Не покрыто:** мок postCallback (асинхронный путь после Arweave) — опционально P2.
6. **publish-flow:** контракт publish (400/401/400/200 и вызовы putStatus) проверяется; при выключенном моке вызов putStatus через fetch проверяется.

---

## Рекомендации (статус после доработки)

| Приоритет | Действие | Статус |
|-----------|----------|--------|
| P1 | Неверный секрет + перехват лога, simulatedStatus из env | ✅ Выполнено (тест «без override секрет не совпадает»). |
| P2 | Override: значение 409/404 в логе | ✅ Выполнено (тесты override + «мок 409 из заголовка», «мок 404 из env»). |
| P2 | Явный тест «мок выключен → fetch» | ✅ Выполнено. |
| P2 | postCallback в моке | Опционально; не реализовано (сценарий требует Arweave). |

**План доработок:** [test-improvements-plan.md](./test-improvements-plan.md) — фазы 1–3 выполнены.

---

**Вердикт (после доработки):** тесты проверяют реальное поведение мока (перехват лога simulatedStatus), проверку секрета (неверный секрет → env), вызов fetch при выключенном моке. Квалификация по P0/P1 закрыта; postCallback в моке остаётся опциональным P2.
