# Bridge: Доработка десериализации продуктов и тестирования в bot слое

**Версия:** 1.0  
**Дата:** 2025-01-23  
**Метод:** @analysis.mdc  
**Цель:** Передача контекста для доработки десериализации продуктов и всех покрывающих процесс тестов в bot слое

---

## 📋 EXECUTIVE SUMMARY

**Задача:** Доработать в bot слое десериализацию продуктов, включая:
1. Загрузку complex fields из блокчейна через `AmanitaInternational`
2. Десериализацию `ComponentDescription` из complex fields
3. Интеграцию с `ProductAssembler` для сборки продуктов с компонентами
4. Покрытие всего процесса тестами (unit, integration, E2E)

**Контекст:** Scripts слой уже реализует загрузку компонентов в блокчейн с правильным форматом `className = "ComponentDescription.{biounit_id}"`. Bot слой должен читать эти данные и десериализовать их в `ComponentDescription` объекты.

---

## 🏗️ АРХИТЕКТУРА СИСТЕМЫ

### 1. Scripts слой (загрузка в блокчейн)

#### 1.1 Процесс загрузки компонентов

**Файл:** `scripts/lib/actions/ComponentActions.js`

**Action 555:** Загружает компоненты в блокчейн через `uploadComponentsCore()`:
1. Активация seller через `InviteActions.activateSeller()`
2. Загрузка компонентов через `upload_steps.js`:
   - `uploadSimpleFields()` — простые поля (title, dosage)
   - `uploadComplexFields()` — комплексные поля (ComponentDescription)
   - `registerComponent()` — регистрация в OrganicComponentRegistry

**Файл:** `scripts/lib/upload_steps.js:189-295`

**Функция:** `uploadComplexFields(context, state)`

**Процесс:**
```javascript
// 1. Читает файлы из complex_fields/
const filePath = `complex_fields/${context.biounit_id}.ComponentDescription.${lang}.json`;

// 2. Загружает в Arweave → получает CID
const descCID = await uploadToArweave(context, descriptionData, filename);

// 3. Сохраняет CID в AmanitaInternational контракт
const classNameWithBiounitId = `ComponentDescription.${context.biounit_id}`;
const tx = await amanitaIntlWithSigner.setComplexFieldCID(
  classNameWithBiounitId,  // "ComponentDescription.amanita_muscaria"
  lang,                     // "ru", "en", "de"
  descCID                   // IPFS/Arweave CID
);

// 4. Сохраняет CID в state.complex_fields[lang]
state.complex_fields[lang] = descCID;
```

**Ключевые особенности:**
- ✅ Использует `className = "ComponentDescription.{biounit_id}"` для уникальности
- ✅ Поддерживает множественные языки (ru, en, de, fr, es, zh, nl, et)
- ✅ Сохраняет CID в `AmanitaInternational` контракт
- ✅ CID доступен через `getComplexFieldCID(className, lang)`

---

### 2. Smart Contracts (хранение CIDs)

#### 2.1 AmanitaInternational Contract

**Файлы:**
- `contracts/AmanitaInternationalLogic.sol` — логика контракта
- `contracts/AmanitaInternationalProxy.sol` — UUPS proxy
- `contracts/interfaces/IAmanitaInternational.sol` — интерфейс

**Методы:**
```solidity
// Запись CID для complex field
function setComplexFieldCID(
    string calldata className,  // "ComponentDescription.amanita_muscaria"
    string calldata lang,       // "ru", "en", "de"
    string calldata cid         // IPFS/Arweave CID
) external onlyOwner;

// Чтение CID для complex field
function getComplexFieldCID(
    string calldata className,  // "ComponentDescription.amanita_muscaria"
    string calldata lang        // "ru", "en", "de"
) external view returns (string memory);
```

**Структура хранения:**
```solidity
// Mapping: className + lang → CID
mapping(string => mapping(string => string)) public complexFieldCIDs;

// Пример:
// complexFieldCIDs["ComponentDescription.amanita_muscaria"]["ru"] = "QmCID123..."
```

**Особенности:**
- ✅ UUPS upgradeable контракт
- ✅ Ownership-based access control (только owner может записывать)
- ✅ Поддержка множественных языков
- ✅ Уникальные ключи для каждого компонента (с `biounit_id`)

---

### 3. Bot слой (чтение и десериализация)

#### 3.1 Текущая архитектура

**Файл:** `bot/services/common/multilingual_ipfs_service.py`

**Сервис:** `MultilingualIPFSService`

**Метод:** `_load_complex_field_from_ipfs(className: str, language: str)`

**Процесс:**
```python
async def _load_complex_field_from_ipfs(self, className: str, language: str) -> Optional[Dict]:
    """
    Загружает complex field из блокчейна и IPFS.
    
    Args:
        className: Класс поля (например, "ComponentDescription.amanita_muscaria")
        language: Язык (например, "ru")
    
    Returns:
        Dict с полями complex field или None
    """
    # 1. Получает CID из блокчейна через BlockchainService
    cid = await self._get_complex_field_cid(className, language)
    
    if not cid:
        return None
    
    # 2. Загружает JSON из IPFS/Arweave через IPFSService
    json_data = await self.ipfs_service.download_json(cid)
    
    # 3. Валидирует структуру
    if not self._validate_complex_field_structure(json_data):
        return None
    
    # 4. Кэширует результат
    await self.cache_service.set(cache_key, json_data, 'ipfs', ttl)
    
    # 5. Возвращает данные
    return json_data
```

**Метод:** `_get_complex_field_cid(className: str, language: str)`

**Процесс:**
```python
async def _get_complex_field_cid(self, className: str, language: str) -> Optional[str]:
    """
    Получает CID для complex field из AmanitaInternational контракта.
    
    Args:
        className: Класс поля (например, "ComponentDescription.amanita_muscaria")
        language: Язык (например, "ru")
    
    Returns:
        CID или None если не найден
    """
    # 1. Получает контракт через BlockchainService
    contract = await self.blockchain_service.get_contract("AmanitaInternational")
    
    if not contract:
        return None
    
    # 2. Вызывает getComplexFieldCID(className, lang)
    cid = await contract.functions.getComplexFieldCID(className, language).call()
    
    # 3. Проверяет, что CID не пустой
    if not cid or cid == "":
        return None
    
    return cid
```

**Файл:** `bot/services/product/component_service.py`

**Сервис:** `ComponentService`

**Метод:** `get_component_description(component_id: str, language: str)`

**Текущая реализация:**
```python
async def get_component_description(
    self,
    component_id: str,  # biounit_id (например, "amanita_muscaria")
    language: str = "ru"
) -> Optional['ComponentDescription']:
    """
    Получает описание компонента из блокчейна.
    
    Args:
        component_id: Business ID компонента (biounit_id)
        language: Язык описания
    
    Returns:
        ComponentDescription объект или None
    """
    # 1. Формирует className с biounit_id
    className = f"ComponentDescription.{component_id}"
    
    # 2. Загружает complex field через MultilingualIPFSService
    description_data = await self.multilingual_ipfs_service._load_complex_field_from_ipfs(
        className,
        language
    )
    
    if not description_data:
        return None
    
    # 3. Извлекает fields из complex field структуры
    fields = description_data.get("fields", {})
    
    # 4. Десериализует в ComponentDescription
    description = ComponentDescription.from_dict(fields)
    
    return description
```

**Файл:** `bot/model/component_description.py`

**Модель:** `ComponentDescription`

**Структура:**
```python
class ComponentDescription:
    """Модель описания компонента."""
    
    generic_description: str  # Обязательное поле
    title: Optional[str] = None
    scientific_title: Optional[str] = None
    effects: Optional[str] = None
    shamanic: Optional[str] = None
    warnings: Optional[str] = None
    dosage_instructions: Optional[List['DosageInstruction']] = None
    features: Optional[List[str]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentDescription':
        """Десериализует из словаря."""
        if not isinstance(data, dict):
            raise ValueError("Данные должны быть словарем")
        
        if "generic_description" not in data:
            raise ValueError("Отсутствует обязательное поле 'generic_description'")
        
        return cls(
            generic_description=data["generic_description"],
            title=data.get("title"),
            scientific_title=data.get("scientific_title"),
            effects=data.get("effects"),
            shamanic=data.get("shamanic"),
            warnings=data.get("warnings"),
            dosage_instructions=[...],  # Десериализация DosageInstruction
            features=data.get("features")
        )
```

---

### 4. Структура данных

#### 4.1 Формат complex field в IPFS/Arweave

**Файл:** `data/components/amanita_muscaria/complex_fields/amanita_muscaria.ComponentDescription.ru.json`

**Пример:**
```json
{
  "label": "ComponentDescription",
  "type": "complex",
  "fields": {
    "generic_description": "Мухомор красный (Amanita muscaria) — гриб семейства Мухоморовые...",
    "title": "Мухомор красный",
    "scientific_title": "Amanita muscaria",
    "effects": "Обладает психоактивными свойствами...",
    "shamanic": "Используется в шаманских практиках...",
    "warnings": "Токсичен в сыром виде...",
    "dosage_instructions": [
      {
        "type": "dried",
        "description": "Сушеные грибы: 1-3 грамма",
        "unit": "g"
      }
    ],
    "features": ["psychoactive", "traditional_use"]
  }
}
```

**Структура:**
- `label` — метка класса ("ComponentDescription")
- `type` — тип поля ("complex")
- `fields` — словарь с полями для десериализации в `ComponentDescription`

---

### 5. Интеграция с ProductAssembler

**Файл:** `bot/services/product/assembler.py`

**Сервис:** `ProductAssembler`

**Метод:** `assemble_product(product_data: Dict) -> Product`

**Процесс:**
```python
async def assemble_product(self, product_data: Dict) -> Product:
    """
    Собирает продукт из данных блокчейна и IPFS.
    
    Process:
    1. Извлекает компоненты из product_data
    2. Для каждого компонента:
       - Загружает описание через ComponentService.get_component_description()
       - Добавляет описание к компоненту
    3. Создает Product объект с компонентами и описаниями
    """
    components = []
    
    for comp_data in product_data.get("components", []):
        component_id = comp_data["component_id"]
        
        # Загружает описание компонента
        description = await self.component_service.get_component_description(
            component_id,
            language="ru"
        )
        
        # Создает OrganicComponent с описанием
        component = OrganicComponent(
            component_id=component_id,
            description=description,
            proportion=comp_data["proportion"]
        )
        
        components.append(component)
    
    # Создает Product
    product = Product(
        business_id=product_data["business_id"],
        components=components,
        # ... другие поля
    )
    
    return product
```

---

## 🧪 ТЕКУЩЕЕ ПОКРЫТИЕ ТЕСТАМИ

### 1. Unit тесты

#### 1.1 ComponentDescription десериализация

**Файл:** `bot/tests/unit/test_component_description.py`

**Покрытие:**
- ✅ `from_dict()` с минимальными данными
- ✅ `from_dict()` с полной структурой
- ✅ `from_dict()` с реальными данными из Arweave (ru, en)
- ✅ Валидация отсутствующих полей
- ✅ Десериализация `DosageInstruction`

**Тесты:**
- `test_from_dict_minimal()` — минимальные данные
- `test_from_dict_full_structure()` — полная структура
- `test_from_dict_real_arweave_russian()` — реальные данные ru
- `test_from_dict_real_arweave_english()` — реальные данные en
- `test_from_dict_reject_missing_generic_description()` — ошибка валидации

---

#### 1.2 ComponentService

**Файл:** `bot/tests/unit/test_component_service.py`

**Покрытие:**
- ✅ `get_component_full()` — получение полных данных компонента
- ✅ Кэширование компонентов
- ⚠️ **ПРОБЕЛ:** Нет тестов для `get_component_description()`

**Тесты:**
- `test_get_component_full()` — базовое получение
- `test_cache_ttl()` — проверка TTL кэша
- `test_cache_invalidation()` — инвалидация кэша

---

### 2. Integration тесты

#### 2.1 MultilingualIPFSService → BlockchainService

**Файл:** `bot/tests/integration/test_multilingual_ipfs_blockchain_integration.py`

**Покрытие:**
- ✅ Загрузка complex field из блокчейна и IPFS
- ✅ Обработка пустого CID
- ✅ Обработка ошибок блокчейна
- ✅ Кэширование complex field
- ✅ Валидация структуры JSON

**Тесты:**
- `test_load_complex_field_success()` — успешная загрузка
- `test_load_complex_field_empty_cid()` — пустой CID
- `test_load_complex_field_blockchain_error()` — ошибка блокчейна
- `test_load_complex_field_caching()` — кэширование
- `test_load_complex_field_invalid_structure()` — невалидная структура

**Проблема:** ⚠️ Тесты используют `className = "ComponentDescription"` без `biounit_id`, но реальный код использует `"ComponentDescription.{biounit_id}"`

---

#### 2.2 ComponentService → MultilingualIPFSService

**Файл:** `bot/tests/unit/test_component_service_localization.py`

**Покрытие:**
- ✅ Интеграция с `MultilingualIPFSService`
- ⚠️ **ПРОБЕЛ:** Нет тестов для `get_component_description()` с `biounit_id`

---

### 3. E2E тесты

#### 3.1 Полный flow десериализации продуктов

**Файл:** `bot/tests/e2e/test_product_full_deserialization_flow.py`

**Покрытие:**
- ✅ Полный pipeline: блокчейн → IPFS → десериализация → форматирование
- ✅ Загрузка описаний компонентов
- ✅ Интеграция с `ProductAssembler`

**Тесты:**
- `test_e2e_single_product_full_flow()` — полный flow одного продукта

**Проблема:** ⚠️ Тесты могут не проверять правильный формат `className` с `biounit_id`

---

## 🚨 ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ

### 1. Несоответствие формата className

**Проблема:**
- Scripts слой загружает с `className = "ComponentDescription.{biounit_id}"`
- Bot слой может использовать `className = "ComponentDescription"` без `biounit_id`
- Тесты используют старый формат без `biounit_id`

**Риск:**
- ❌ Bot не сможет загрузить описания компонентов из блокчейна
- ❌ CID не будет найден в контракте (неправильный ключ)

**Решение:**
- ✅ `ComponentService.get_component_description()` уже использует правильный формат: `f"ComponentDescription.{component_id}"`
- ⚠️ Нужно обновить тесты для использования правильного формата

---

### 2. Отсутствие тестов для get_component_description()

**Проблема:**
- ❌ Нет unit тестов для `ComponentService.get_component_description()`
- ❌ Нет integration тестов для проверки интеграции с `MultilingualIPFSService`
- ⚠️ Есть только E2E тесты, которые проверяют полный flow

**Решение:**
- Добавить unit тесты для `get_component_description()`
- Добавить integration тесты для проверки формата `className`
- Обновить существующие тесты для использования правильного формата

---

### 3. Отсутствие тестов для ProductAssembler с компонентами

**Проблема:**
- ⚠️ Нет тестов для проверки загрузки описаний компонентов в `ProductAssembler`
- ⚠️ Нет тестов для проверки интеграции `ProductAssembler → ComponentService`

**Решение:**
- Добавить тесты для `ProductAssembler.assemble_product()` с компонентами
- Добавить проверку загрузки `ComponentDescription` для каждого компонента

---

### 4. Несоответствие структуры complex field

**Проблема:**
- Scripts слой создает структуру: `{"label": "...", "type": "complex", "fields": {...}}`
- Bot слой должен извлекать `fields` и десериализовать в `ComponentDescription`
- ⚠️ Нужно проверить, что `ComponentService.get_component_description()` правильно извлекает `fields`

**Решение:**
- Проверить текущую реализацию `get_component_description()`
- Добавить тесты для проверки извлечения `fields` из complex field структуры

---

## ✅ ТЕКУЩЕЕ СОСТОЯНИЕ

### Scripts слой

**Статус:** ✅ **Production-ready**

**Реализация:**
- ✅ Загрузка complex fields с правильным форматом `className = "ComponentDescription.{biounit_id}"`
- ✅ Сохранение CID в `AmanitaInternational` контракт
- ✅ Покрытие тестами: Unit (18), Integration (18), E2E (7), Validator

**Документация:**
- `scripts/docs/Components-Architecture.md` — полная архитектура
- `scripts/docs/testing/component-upload-testing-status.md` — статус тестирования

---

### Bot слой

**Статус:** ⚠️ **Реализовано, но требует доработки тестов**

**Реализация:**
- ✅ `ComponentService.get_component_description()` использует правильный формат `className`
- ✅ `MultilingualIPFSService._load_complex_field_from_ipfs()` загружает из блокчейна
- ✅ `ComponentDescription.from_dict()` десериализует данные
- ⚠️ **ПРОБЕЛЫ:**
  - Нет unit тестов для `get_component_description()`
  - Тесты используют старый формат `className` без `biounit_id`
  - Нет тестов для `ProductAssembler` с компонентами

---

## 📋 ЗАДАЧИ ДЛЯ ДОРАБОТКИ

### Приоритет P0 (критично)

#### Task 1: Обновить тесты для правильного формата className

**Файлы:**
- `bot/tests/integration/test_multilingual_ipfs_blockchain_integration.py`
- `bot/tests/common/test_multilingual_ipfs_service.py`

**Действия:**
1. Обновить все тесты для использования `className = "ComponentDescription.{biounit_id}"`
2. Проверить, что тесты используют правильный формат при вызове `_load_complex_field_from_ipfs()`
3. Добавить тесты для проверки формата `className` с `biounit_id`

**Время:** 1-2 часа

---

#### Task 2: Добавить unit тесты для ComponentService.get_component_description()

**Файл:** `bot/tests/unit/test_component_service.py` (или новый файл)

**Действия:**
1. Добавить тесты для `get_component_description()`:
   - Успешная загрузка описания
   - Обработка отсутствующего описания
   - Обработка ошибок загрузки
   - Проверка правильного формата `className`
   - Проверка извлечения `fields` из complex field структуры
   - Проверка десериализации в `ComponentDescription`

2. Использовать моки для `MultilingualIPFSService` и `ComponentDescription.from_dict()`

**Время:** 2-3 часа

---

### Приоритет P1 (важно)

#### Task 3: Добавить integration тесты для ComponentService → MultilingualIPFSService

**Файл:** `bot/tests/integration/test_component_service_integration.py` (новый файл)

**Действия:**
1. Добавить тесты для проверки интеграции:
   - `ComponentService.get_component_description()` → `MultilingualIPFSService._load_complex_field_from_ipfs()`
   - Проверка правильного формата `className` с `biounit_id`
   - Проверка извлечения `fields` из complex field структуры
   - Проверка десериализации в `ComponentDescription`

2. Использовать stubs для `BlockchainService` и `IPFSService`

**Время:** 2-3 часа

---

#### Task 4: Добавить тесты для ProductAssembler с компонентами

**Файл:** `bot/tests/unit/test_product_assembler.py` (расширить существующий)

**Действия:**
1. Добавить тесты для `assemble_product()` с компонентами:
   - Проверка загрузки описаний компонентов
   - Проверка интеграции с `ComponentService.get_component_description()`
   - Проверка создания `Product` с компонентами и описаниями

2. Использовать моки для `ComponentService` и `MultilingualIPFSService`

**Время:** 2-3 часа

---

#### Task 5: Обновить E2E тесты для проверки правильного формата className

**Файл:** `bot/tests/e2e/test_product_full_deserialization_flow.py`

**Действия:**
1. Обновить тесты для проверки правильного формата `className` с `biounit_id`
2. Добавить проверки для загрузки описаний компонентов из блокчейна
3. Проверить, что `ComponentService.get_component_description()` вызывается с правильным форматом

**Время:** 1-2 часа

---

## 📊 ТЕКУЩЕЕ ПОКРЫТИЕ ТЕСТАМИ

| Слой | Функциональность | Unit | Integration | E2E | Статус |
|------|------------------|------|-------------|-----|--------|
| **Scripts** | Загрузка complex fields | ✅ 18 | ✅ 18 | ✅ 7 | ✅ Production-ready |
| **Bot** | Десериализация ComponentDescription | ✅ 6 | ⚠️ 5 | ✅ 1 | ⚠️ Требует доработки |
| **Bot** | ComponentService.get_component_description() | ❌ 0 | ⚠️ 0 | ✅ 1 | ❌ Критический пробел |
| **Bot** | ProductAssembler с компонентами | ⚠️ Частично | ❌ 0 | ✅ 1 | ⚠️ Требует доработки |

---

## 🎯 КЛЮЧЕВЫЕ ФАЙЛЫ

### Scripts слой

- `scripts/lib/actions/ComponentActions.js` — Action 555 для загрузки компонентов
- `scripts/lib/upload_steps.js:189-295` — `uploadComplexFields()` загрузка complex fields
- `scripts/docs/Components-Architecture.md` — архитектура компонентов
- `scripts/docs/testing/component-upload-testing-status.md` — статус тестирования

---

### Smart Contracts

- `contracts/AmanitaInternationalLogic.sol` — логика контракта
- `contracts/interfaces/IAmanitaInternational.sol` — интерфейс контракта
- Методы: `setComplexFieldCID()`, `getComplexFieldCID()`

---

### Bot слой

#### Сервисы

- `bot/services/common/multilingual_ipfs_service.py` — загрузка complex fields из блокчейна
- `bot/services/product/component_service.py` — сервис работы с компонентами
- `bot/services/product/assembler.py` — сборка продуктов с компонентами

#### Модели

- `bot/model/component_description.py` — модель `ComponentDescription`
- `bot/model/organic_component.py` — модель `OrganicComponent`
- `bot/model/product.py` — модель `Product`

#### Тесты

- `bot/tests/unit/test_component_description.py` — тесты десериализации
- `bot/tests/unit/test_component_service.py` — тесты ComponentService
- `bot/tests/integration/test_multilingual_ipfs_blockchain_integration.py` — integration тесты
- `bot/tests/e2e/test_product_full_deserialization_flow.py` — E2E тесты

---

## 📚 ДОКУМЕНТАЦИЯ

### Актуальная документация

- `scripts/docs/Components-Architecture.md` — полная архитектура компонентов
- `scripts/docs/testing/component-upload-testing-status.md` — статус тестирования загрузки
- `bot/docs/product/future-typed-component-descriptions.md` — будущая архитектура типизированных описаний

### Связанные документы

- `scripts/docs/Testing-Architecture.md` — архитектура тестирования (scripts)
- `bot/tests/README_COMPONENT_TESTING.md` — документация по тестированию компонентов

---

## 🔍 КЛЮЧЕВЫЕ МЕТРИКИ

### Формат className

**Scripts слой:**
- ✅ Использует: `"ComponentDescription.{biounit_id}"`
- ✅ Пример: `"ComponentDescription.amanita_muscaria"`

**Bot слой:**
- ✅ `ComponentService.get_component_description()` использует: `f"ComponentDescription.{component_id}"`
- ⚠️ Тесты могут использовать старый формат: `"ComponentDescription"`

---

### Структура complex field

**В IPFS/Arweave:**
```json
{
  "label": "ComponentDescription",
  "type": "complex",
  "fields": {
    "generic_description": "...",
    "title": "...",
    // ... другие поля
  }
}
```

**В ComponentDescription:**
- Извлекается `fields` из complex field структуры
- Десериализуется через `ComponentDescription.from_dict(fields)`

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

### Phase 1: Обновление тестов (P0)

1. **Обновить integration тесты** для использования правильного формата `className` с `biounit_id`
2. **Добавить unit тесты** для `ComponentService.get_component_description()`
3. **Проверить E2E тесты** для правильного формата `className`

**Время:** 4-7 часов

---

### Phase 2: Расширение тестов (P1)

1. **Добавить integration тесты** для `ComponentService → MultilingualIPFSService`
2. **Добавить тесты** для `ProductAssembler` с компонентами
3. **Обновить E2E тесты** для проверки полного flow с компонентами

**Время:** 4-6 часов

---

### Phase 3: Валидация (P0)

1. **Запустить все тесты** и убедиться, что они проходят
2. **Проверить интеграцию** с реальным блокчейном (если доступен)
3. **Обновить документацию** с результатами тестирования

**Время:** 1-2 часа

---

## 📝 ПРИМЕЧАНИЯ

### Важные детали

1. **biounit_id vs component_id:**
   - `biounit_id` — текстовый идентификатор компонента (например, "amanita_muscaria")
   - Используется в `className` для уникальности ключей в контракте
   - В bot слое обычно называется `component_id`

2. **Формат className:**
   - ✅ **Правильный:** `"ComponentDescription.{biounit_id}"` (например, `"ComponentDescription.amanita_muscaria"`)
   - ❌ **Неправильный:** `"ComponentDescription"` (глобальный ключ, перезаписывается)

3. **Структура complex field:**
   - В IPFS/Arweave хранится обёртка: `{"label": "...", "type": "complex", "fields": {...}}`
   - Bot слой извлекает `fields` и десериализует в `ComponentDescription`

4. **Тестирование:**
   - Unit тесты должны использовать моки для внешних сервисов
   - Integration тесты должны использовать stubs для блокчейна и IPFS
   - E2E тесты должны использовать реальный блокчейн (если доступен)

---

## ✅ КРИТЕРИИ УСПЕХА

1. ✅ Все тесты обновлены для использования правильного формата `className` с `biounit_id`
2. ✅ Добавлены unit тесты для `ComponentService.get_component_description()`
3. ✅ Добавлены integration тесты для проверки интеграции с `MultilingualIPFSService`
4. ✅ Добавлены тесты для `ProductAssembler` с компонентами
5. ✅ Все тесты проходят успешно
6. ✅ Документация обновлена с результатами

---

**Версия:** 1.0  
**Последнее обновление:** 2025-01-23  
**Статус:** ✅ Готово для использования в новом диалоге

