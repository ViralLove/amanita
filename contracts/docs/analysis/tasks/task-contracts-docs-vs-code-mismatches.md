# task: Несоответствия docs ↔ code ↔ tests в `contracts/`

**Статус:** Implemented (Waiting Acceptance)  
**Цель:** держать актуальный реестр реальных mismatch-пунктов после SM-1 / SM-1.1 / SM-1.2 / SM-2.  
**Правило:** только подтвержденные факты из текущего кода и тестов.

---

## 1) LoveDo ↔ LoveEmission ↔ tests: статус после последних задач

### 1.1 Ранее критичный mismatch интерфейсов — **закрыт**
- Исторический конфликт (`addSuperlike`/`getPost`) из SM-1 устранен.
- Текущая связка компилируется и тестируется:
  - `contracts/LoveDoPostNFT.sol`
  - `contracts/LoveEmissionEngine.sol`
  - `contracts/tests/LoveEmissionEngine.lovecoin.test.js`
  - `contracts/tests/LoveEmissionEngine.social-mining.mvp.test.js`

### 1.2 User-driven superlike и anti-double-emit — **закрыто**
- Лайк ставится пользователем напрямую в LoveDo (`msg.sender`).
- Engine проверяет `hasSuperliked(tokenId, liker)` и защищен `emittedForLike[tokenId][liker]`.

### 1.3 Depth-circle модель в LoveDo и удаление дублирования в Engine — **закрыто**
- В `LoveDoPostNFT` проверка сообщества теперь depth-based (`K/L`, anchor, max hops).
- В `LoveEmissionEngine` удален дублирующий circle-check.

### 1.4 Social-mining MVP suite — **закрыто**
- Добавлен отдельный suite:
  - `contracts/tests/LoveEmissionEngine.social-mining.mvp.test.js`
- Покрыты accrual инварианты, depth-circle gating, monthly limits, threshold + one-shot.

---

## 2) Оставшиеся актуальные mismatch-пункты

## 2.1 `LoveDoPostNFT.sol` ↔ `AmanitaRegistry.sol`: API still mismatched
- **В `LoveDoPostNFT.sol`** ожидается `hasSellerRole(address)`.
- **В `AmanitaRegistry.sol`** (по текущему состоянию задачи и прошлому аудиту) такого метода нет.
- В тестах используется `LoveAmanitaRegistryMock`, что обходило это место, но для production source-of-truth вопрос остаётся.

**Статус:** Open.

---

## 2.2 Терминология LGOV vs on-chain symbol AGOV
- Экономические docs используют `$LGOV`.
- Контракт governance токена использует symbol `AGOV`.
- В персистентной зоне social mining (`LoveEmissionEngine.md`, `LovecoinTokens.md`, `SpiralEngine & LGOV Security MVP Scope.md`) добавлена/сохранена явная связка: *LGOV в экономической модели ↔ AGOV как on-chain symbol*.

**Статус:** Partially closed (остаётся проверить оставшиеся docs вне social-mining пакета).

---

## 2.3 Реестры адресов и дубликаты имен (`AmanitaRegistry` / `MagicRegistry`)
- По-прежнему актуально наблюдение о потенциальных дубликатах в списках имен при повторных `set`.

**Статус:** Open (качество API/документации).

---

## 2.4 Варианты SpiralEngine (UUPS vs non-UUPS)
- В репозитории присутствуют обе линии.
- В docs/integration notes важно явно указывать, о каком адресе/ABI идет речь.

**Статус:** Open (архитектурная дисциплина документации).

---

## 3) Что закрыто относительно старой версии этого файла

- ❎ Пункт про «несовместимые сигнатуры LoveEmission ↔ LoveDo» — закрыт.
- ❎ Пункт про «тесты написаны под старый LoveDo» — закрыт.
- ❎ Пункт про «LoveEmissionEngine.md критично не соответствует коду» — существенно закрыт по ключевым API/flow после SM-1.1/SM-1.2.

---

## 4) Мини-чеклист на следующий цикл (реально открытое)

- [ ] Зафиксировать production source-of-truth для `hasSellerRole` в LoveDo (и документировать контракт-источник).
- [ ] Дозакрыть нормализацию LGOV/AGOV терминологии во всех оставшихся docs вне social-mining зоны.
- [ ] Уточнить и при необходимости задокументировать поведение реестров при повторных `set`.
- [ ] Добавить в канонические docs явную пометку про UUPS/non-UUPS адреса SpiralEngine.


