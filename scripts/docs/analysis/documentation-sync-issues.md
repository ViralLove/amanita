# 🔍 Анализ синхронизации документации с кодом

**Дата**: 2025-01-13  
**Методология**: @analysis.mdc  
**Статус**: Требуется исправление

---

## 📋 Резюме

Проведен глубокий анализ документации в `scripts/docs` и сравнение с реальным кодом в `scripts/lib` и `scripts/deploy_full.js`. Обнаружены критические несоответствия, требующие исправления.

---

## ❌ КРИТИЧЕСКИЕ НЕСООТВЕТСТВИЯ

### 1. **InviteNFT vs SpiralEngine** (КРИТИЧНО)

**Проблема**: Документация упоминает `InviteNFT` как отдельный контракт, но в коде используется `SpiralEngine`.

**Где найдено**:
- `scripts/docs/Deploy_Full.md:716-718`:
  ```markdown
  | `InviteNFT` | Нет | Да (SELLER_ROLE) | Система инвайт-кодов |
  | `ProductRegistry` | InviteNFT | Нет | Реестр продуктов |
  | `LoveDoPostNFT` | InviteNFT, AmanitaRegistry | Нет | NFT для постов о любви |
  ```

**Реальность в коде**:
- `scripts/lib/actions/InviteActions.js` - использует `SpiralEngine` (все упоминания)
- `scripts/lib/actions/DeployActions.js:138` - деплоит `SpiralEngine`
- `scripts/lib/actions/ComponentActions.js:44` - загружает `SpiralEngine`
- `scripts/lib/actions/CatalogActions.js:257` - использует `SpiralEngine`

**Исправление**:
- Заменить все упоминания `InviteNFT` на `SpiralEngine`
- Обновить таблицу зависимостей контрактов
- Обновить примеры деплоя

---

### 2. **AmanitaToken vs Lovecoin** (КРИТИЧНО)

**Проблема**: Документация упоминает `AmanitaToken` как основной утилити токен, но в коде используется `Lovecoin`.

**Где найдено**:
- `scripts/docs/Deploy_Full.md:720`:
  ```markdown
  | `AmanitaToken` | Нет | Нет | Утилити токен |
  ```
- `scripts/docs/Deploy_Full.md:767`:
  ```bash
  node deploy_full.js 5 AmanitaToken
  ```
- `scripts/docs/Deploy_Full.md:719`:
  ```markdown
  | `LoveEmissionEngine` | AmanitaToken, AmanitaGovToken, LoveDoPostNFT, InviteNFT | Да (EMITTER_ROLE) | Движок эмиссии любви |
  ```
- `scripts/docs/actions/Deploy.md:108`:
  ```yaml
  Regular:
    - AmanitaToken
  ```

**Реальность в коде**:
- `scripts/lib/actions/DeployActions.js` - НЕТ упоминаний `AmanitaToken`
- В коде используется `Lovecoin` как основной утилити токен
- `LoveEmissionEngine` использует `Lovecoin`, а не `AmanitaToken`

**Исправление**:
- Заменить `AmanitaToken` на `Lovecoin` в таблицах зависимостей
- Обновить примеры деплоя
- Уточнить, что `AmanitaToken` существует, но не является основным токеном для эмиссии

---

### 3. **Зависимости контрактов** (КРИТИЧНО)

**Проблема**: Документация указывает неверные зависимости для контрактов.

**Где найдено**:
- `scripts/docs/Deploy_Full.md:717-719`:
  ```markdown
  | `ProductRegistry` | InviteNFT | Нет | Реестр продуктов |
  | `LoveDoPostNFT` | InviteNFT, AmanitaRegistry | Нет | NFT для постов о любви |
  | `LoveEmissionEngine` | AmanitaToken, AmanitaGovToken, LoveDoPostNFT, InviteNFT | Да (EMITTER_ROLE) | Движок эмиссии любви |
  ```

**Реальность в коде**:
- `ProductRegistry` зависит от `SpiralEngine` (не от `InviteNFT`)
- `LoveDoPostNFT` зависит от `SpiralEngine` (не от `InviteNFT`)
- `LoveEmissionEngine` зависит от `Lovecoin` (не от `AmanitaToken`) и `SpiralEngine` (не от `InviteNFT`)

**Исправление**:
- Обновить таблицу зависимостей:
  ```markdown
  | `ProductRegistry` | SpiralEngine | Нет | Реестр продуктов |
  | `LoveDoPostNFT` | SpiralEngine, AmanitaRegistry | Нет | NFT для постов о любви |
  | `LoveEmissionEngine` | Lovecoin, AmanitaGovToken, LoveDoPostNFT, SpiralEngine | Да (EMITTER_ROLE) | Движок эмиссии любви |
  ```

---

### 4. **Отсутствующие Actions в документации** (СРЕДНЕ)

**Проблема**: В документации упоминаются actions, которых нет в реальном коде.

**Где найдено**:
- `scripts/docs/Deploy_Full.md:441-497` - описание Action 10 и Action 12

**Реальность в коде**:
- `scripts/lib/actions/index.js:104` - список доступных actions: `[0, 1, 2, 4, 5, 6, 7, 9, 11, 13, 40, 41, 42, 43, 46, 444, 555, 777, 888]`
- Actions 10 и 12 **НЕ СУЩЕСТВУЮТ** в коде

**Исправление**:
- Удалить разделы про Action 10 и Action 12 из `Deploy_Full.md`
- Или добавить примечание, что эти actions устарели/удалены

---

### 5. **Дублирование Action 13** (НИЗКО)

**Проблема**: Action 13 описан дважды с разными описаниями.

**Где найдено**:
- `scripts/docs/Deploy_Full.md:441-460` - Action 10 (описание идентично Action 13)
- `scripts/docs/Deploy_Full.md:499-520` - Action 13

**Реальность в коде**:
- `scripts/lib/actions/index.js:73` - Action 13 существует и вызывает `accessControlActions.action13()`
- Action 10 **НЕ СУЩЕСТВУЕТ** в коде

**Исправление**:
- Удалить описание Action 10 (дубликат Action 13)

---

### 6. **Неточности в примерах деплоя** (СРЕДНЕ)

**Проблема**: Примеры деплоя используют устаревшие названия контрактов.

**Где найдено**:
- `scripts/docs/Deploy_Full.md:770-771`:
  ```bash
  # Деплой InviteNFT (требует настройки ролей)
  node deploy_full.js 5 InviteNFT
  ```
- `scripts/docs/Deploy_Full.md:773`:
  ```bash
  # Деплой ProductRegistry (требует InviteNFT)
  node deploy_full.js 5 ProductRegistry
  ```

**Исправление**:
- Заменить примеры:
  ```bash
  # Деплой SpiralEngine (требует настройки ролей)
  DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost SpiralEngine
  
  # Деплой ProductRegistry (требует SpiralEngine)
  DEPLOY_ACTION=5 npx hardhat run scripts/deploy_full.js --network localhost ProductRegistry
  ```

---

## ⚠️ СРЕДНИЕ НЕСООТВЕТСТВИЯ

### 7. **Устаревшие ссылки на deploy_full_new.js** (НИЗКО)

**Где найдено**:
- `scripts/docs/Deploy_Full.md:196`:
  ```bash
  DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full_new.js --network localhost
  ```

**Реальность**:
- Файл называется `deploy_full.js` (не `deploy_full_new.js`)

**Исправление**:
- Заменить `deploy_full_new.js` на `deploy_full.js`

---

### 8. **Неточности в описании Action 5** (НИЗКО)

**Проблема**: В документации указаны контракты, которые могут быть неверными.

**Где найдено**:
- `scripts/docs/Deploy_Full.md:377-407` - список поддерживаемых контрактов для Action 5

**Проверка**:
- Нужно сверить с реальным списком в `ContractManager.deploySingleContract()`

---

## ✅ СООТВЕТСТВИЯ (Проверено)

### Правильно документировано:
- ✅ Action 0, 1, 2, 4, 5, 6, 7, 9, 11, 13, 40, 41, 42, 43, 46, 444, 555, 777, 888
- ✅ UUPS архитектура для SpiralEngine и ProductRegistry
- ✅ Action 555 - загрузка компонентов
- ✅ Action 888 - полная инициализация seller
- ✅ Формат инвайт-кодов: `AMANITA-XXXX-XXXX`
- ✅ Структура модульной архитектуры (Deploy_Architecture.md)

---

## 📝 ПЛАН ИСПРАВЛЕНИЙ

### Приоритет 1 (КРИТИЧНО):
1. ✅ **ИСПРАВЛЕНО** Заменить все `InviteNFT` → `SpiralEngine` в `Deploy_Full.md`
2. ⏳ Заменить все `AmanitaToken` → `Lovecoin` в таблицах зависимостей
3. ✅ **ИСПРАВЛЕНО** Обновить таблицу зависимостей контрактов (частично - вместе с пунктом 1)
4. ✅ **ИСПРАВЛЕНО** Удалить описания Actions 10 и 12

### Приоритет 2 (СРЕДНЕ):
5. ✅ **ИСПРАВЛЕНО** Исправить примеры деплоя для Action 5
6. ✅ **ИСПРАВЛЕНО** Удалить дубликат Action 10 (вместе с пунктом 4)
7. ✅ **ИСПРАВЛЕНО** Заменить `deploy_full_new.js` → `deploy_full.js`

### Приоритет 3 (НИЗКО):
8. ✅ **ИСПРАВЛЕНО** Проверить список поддерживаемых контрактов для Action 5 (добавлено примечание и OrganicComponentRegistry)
9. ⚠️ Обновить другие документы в `scripts/docs/actions/`

---

## 🔍 МЕТОДОЛОГИЯ ПРОВЕРКИ

### Проверенные файлы:
- ✅ `scripts/deploy_full.js` - главный роутер
- ✅ `scripts/lib/actions/index.js` - список всех actions
- ✅ `scripts/lib/actions/DeployActions.js` - деплой контрактов
- ✅ `scripts/lib/actions/InviteActions.js` - инвайты
- ✅ `scripts/lib/actions/CatalogActions.js` - каталог
- ✅ `scripts/lib/actions/ComponentActions.js` - компоненты

### Проверенные документы:
- ✅ `scripts/docs/Deploy_Full.md` - основная документация
- ✅ `scripts/docs/Deploy_Architecture.md` - архитектура
- ✅ `scripts/docs/actions/Deploy.md` - документация DeployActions
- ✅ `scripts/docs/actions/Invite.md` - документация InviteActions

---

## 📊 СТАТИСТИКА

- **Всего найдено несоответствий**: 8
- **Критичных**: 4
- **Средних**: 3
- **Низких**: 1

---

**Следующий шаг**: Исправить все найденные несоответствия согласно плану приоритетов.

