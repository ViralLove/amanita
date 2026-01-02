# Deployment Automation Format

## Назначение

Структурированный JSON-формат для автоматизации выполнения пайплайнов деплоя (Вариант A из `node-launch.txt`). Формат разработан для удобного парсинга и выполнения AI-ассистентом.

## Структура формата

### Основные секции

1. **`prerequisites`** - Проверки перед началом выполнения
2. **`steps`** - Последовательность шагов выполнения
3. **`state`** - Состояние для хранения промежуточных данных
4. **`options`** - Опции выполнения

### Типы шагов

- **`bash`** - Выполнение bash-команд
- **`hardhat`** - Выполнение Hardhat скриптов
- **`manual`** - Требует ручного вмешательства
- **`validation`** - Валидация результатов

### Типы валидаций

- **`exit_code`** - Проверка кода выхода
- **`grep`** - Поиск паттерна в файле
- **`file_exists`** - Проверка существования файла
- **`file_content`** - Проверка содержимого файла
- **`log_contains`** - Поиск паттернов в логах

### Извлечение данных (extractors)

Позволяет извлекать данные из результатов выполнения и сохранять в `state` для использования в последующих шагах.

Пример: извлечение инвайтов из файла для использования в следующих шагах.

## Использование

### Базовое использование

```bash
# AI читает JSON и выполняет шаги последовательно
# Формат позволяет:
# 1. Парсить структуру
# 2. Проверять зависимости
# 3. Выполнять команды
# 4. Валидировать результаты
# 5. Извлекать данные для следующих шагов
```

### Расширение для нюансировки

Вы можете добавить дополнительные поля в каждый шаг:

```json
{
  "id": "custom_step",
  "name": "Кастомный шаг",
  "type": "hardhat",
  "command": "...",
  "env": {
    "DEPLOY_ACTION": "999",
    "CUSTOM_PARAM": "${state.custom_value}"
  },
  "conditions": [
    {
      "if": "state.some_flag == true",
      "then": "execute",
      "else": "skip"
    }
  ],
  "retry": {
    "max_attempts": 3,
    "delay_seconds": 5
  },
  "timeout_seconds": 300
}
```

## Преимущества формата

1. **Структурированность** - Легко парсить программно
2. **Зависимости** - Явное указание зависимостей между шагами
3. **Валидация** - Встроенные проверки после каждого шага
4. **Извлечение данных** - Автоматическое извлечение данных (invites, адреса и т.д.)
5. **Расширяемость** - Легко добавлять новые шаги и параметры
6. **Состояние** - Сохранение промежуточных данных для использования в следующих шагах

## Примеры расширений

### Добавление условного выполнения

```json
{
  "id": "conditional_step",
  "condition": {
    "type": "file_exists",
    "path": ".env.backup",
    "if_true": "skip",
    "if_false": "execute"
  }
}
```

### Добавление повторных попыток

```json
{
  "id": "retry_step",
  "retry": {
    "max_attempts": 3,
    "delay_seconds": 10,
    "on_error": "retry"
  }
}
```

### Добавление таймаутов

```json
{
  "id": "timeout_step",
  "timeout_seconds": 300,
  "on_timeout": "fail"
}
```

## Формат для AI

Этот формат специально разработан для удобного парсинга AI:

1. **Четкая структура** - JSON легко парсится
2. **Явные зависимости** - AI понимает порядок выполнения
3. **Валидации** - AI знает что проверять после каждого шага
4. **Извлечение данных** - AI автоматически извлекает нужные данные
5. **Обработка ошибок** - Явные инструкции что делать при ошибках
6. **Поддержка сценариев** - Система кодов для выбора параметров выполнения

### Обработка сценариев в JSON

**Структура**:
```json
{
  "scenario": "SCENARIO_1_1",  // Выбранный сценарий (опционально, default: SCENARIO_1_1)
  "scenarios": {
    "SCENARIO_1_1": {
      "requires_deployer_invite": true,
      "use_existing_cids": false
    },
    ...
  },
  "steps": [
    {
      "id": "load_components",
      "env": {
        "DEPLOYER_INVITE": "${scenarios[scenario].requires_deployer_invite ? state.invites.invite_1 : ''}",
        "USE_EXISTING_CIDS": "${scenarios[scenario].use_existing_cids ? 'true' : 'false'}"
      }
    }
  ]
}
```

**Алгоритм для AI**:
1. Прочитать поле `scenario` (или использовать default "SCENARIO_1_1")
2. Найти определение в `scenarios[scenario]`
3. Подставить параметры в шаг `load_components`:
   - Если `requires_deployer_invite == true` → установить `DEPLOYER_INVITE=${state.invites.invite_1}`
   - Если `requires_deployer_invite == false` → не устанавливать `DEPLOYER_INVITE` (или пустая строка)
   - Установить `USE_EXISTING_CIDS=${scenarios[scenario].use_existing_cids ? 'true' : 'false'}`

**Примеры**:
- `"scenario": "SCENARIO_1_1"` → `DEPLOYER_INVITE` требуется, `USE_EXISTING_CIDS=false`
- `"scenario": "SCENARIO_2_2"` → `DEPLOYER_INVITE` не требуется, `USE_EXISTING_CIDS=true`

## Система кодов для сценариев создания компонентов

Для автоматизации через AI-промпты используется система кодов, которая определяет параметры выполнения Action 555.

### Сценарии

#### **SCENARIO_1_1**: Seller с активацией + перезагрузка Arweave
- **Описание**: Seller НЕ активирован, требуется активация через инвайт. Все компоненты загружаются заново в Arweave, CID перезаписываются.
- **Параметры**:
  - `DEPLOYER_INVITE`: ✅ **Требуется** (рутовый инвайт из Action 777)
  - `USE_EXISTING_CIDS`: `false` (или не устанавливать, default=false)
- **Поведение**:
  - Action 51: Выполнит активацию seller через `activateSeller()`
  - Action 52: Загрузит все компоненты заново в Arweave, перезапишет CID в `_upload_state.json`
- **Пример команды**:
  ```bash
  DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX-YYYY \
    npx hardhat run scripts/deploy_full.js --network localhost
  ```

#### **SCENARIO_1_2**: Seller с активацией + использовать существующие CID
- **Описание**: Seller НЕ активирован, требуется активация через инвайт. Используются существующие CID из state файлов, загрузка в Arweave не выполняется.
- **Параметры**:
  - `DEPLOYER_INVITE`: ✅ **Требуется** (рутовый инвайт из Action 777)
  - `USE_EXISTING_CIDS`: `true`
- **Поведение**:
  - Action 51: Выполнит активацию seller через `activateSeller()`
  - Action 52: Использует CID из `_upload_state.json`, не загружает в Arweave (fallback: если CID отсутствует → автоматическая загрузка)
- **Пример команды**:
  ```bash
  DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-XXXX-YYYY USE_EXISTING_CIDS=true \
    npx hardhat run scripts/deploy_full.js --network localhost
  ```

#### **SCENARIO_2_1**: Seller уже активирован + перезагрузка Arweave
- **Описание**: Seller уже активирован (имеет `SELLER_ROLE`), активация пропускается. Все компоненты загружаются заново в Arweave, CID перезаписываются.
- **Параметры**:
  - `DEPLOYER_INVITE`: ❌ **Не требуется** (seller уже активирован)
  - `USE_EXISTING_CIDS`: `false` (или не устанавливать, default=false)
- **Поведение**:
  - Action 51: Пропустит активацию (`skipActivation=true`), проверит статус через blockchain
  - Action 52: Загрузит все компоненты заново в Arweave, перезапишет CID в `_upload_state.json`
- **Пример команды**:
  ```bash
  DEPLOY_ACTION=555 USE_EXISTING_CIDS=false \
    npx hardhat run scripts/deploy_full.js --network localhost
  ```

#### **SCENARIO_2_2**: Seller уже активирован + использовать существующие CID
- **Описание**: Seller уже активирован (имеет `SELLER_ROLE`), активация пропускается. Используются существующие CID из state файлов, загрузка в Arweave не выполняется.
- **Параметры**:
  - `DEPLOYER_INVITE`: ❌ **Не требуется** (seller уже активирован)
  - `USE_EXISTING_CIDS`: `true`
- **Поведение**:
  - Action 51: Пропустит активацию (`skipActivation=true`), проверит статус через blockchain
  - Action 52: Использует CID из `_upload_state.json`, не загружает в Arweave (fallback: если CID отсутствует → автоматическая загрузка)
- **Пример команды**:
  ```bash
  DEPLOY_ACTION=555 USE_EXISTING_CIDS=true \
    npx hardhat run scripts/deploy_full.js --network localhost
  ```

### Использование для AI-промптов

**Формат промпта**:
```
Выполни SCENARIO_X_Y для создания компонентов
```

**Примеры**:
- `"Выполни SCENARIO_1_1 для создания компонентов"` → AI понимает: нужен DEPLOYER_INVITE, USE_EXISTING_CIDS=false, выполнить активацию и загрузить в Arweave
- `"Выполни SCENARIO_2_2 для создания компонентов"` → AI понимает: DEPLOYER_INVITE не нужен, USE_EXISTING_CIDS=true, пропустить активацию и использовать существующие CID

### Матрица сценариев

| Сценарий | Код | DEPLOYER_INVITE | USE_EXISTING_CIDS | Action 51 | Action 52 |
|----------|-----|-----------------|-------------------|-----------|-----------|
| 1.1 | SCENARIO_1_1 | ✅ Требуется | false | Активация | Загрузка в Arweave |
| 1.2 | SCENARIO_1_2 | ✅ Требуется | true | Активация | Использовать CID |
| 2.1 | SCENARIO_2_1 | ❌ Не требуется | false | Пропуск | Загрузка в Arweave |
| 2.2 | SCENARIO_2_2 | ❌ Не требуется | true | Пропуск | Использовать CID |

### Важные замечания

1. **Проверка активации**: Action 51 автоматически проверяет статус активации ДО требования DEPLOYER_INVITE. Если seller уже активирован → активация пропускается.

2. **Fallback механизм**: Если `USE_EXISTING_CIDS=true`, но CID отсутствует в state файлах → автоматически выполняется загрузка в Arweave (fallback).

3. **Валидация**: После выполнения Action 555 рекомендуется запустить валидацию компонентов:
   ```bash
   node scripts/validators/validate_component_upload.js --component <component_id> --network localhost
   ```

## Файлы

- `variant-a.json` - Конфигурация для Варианта A
- `variant-b.json` - (TODO) Конфигурация для Варианта B
- `quick-restart.json` - (TODO) Конфигурация для быстрого рестарта
