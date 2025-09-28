# AI Journal - Рабочий журнал разработки Amanita

## 📋 Постановка задачи: Локализация данных о продуктах и organic components

### 🎯 Цель задачи
Реализовать полную локализацию данных о продуктах в Telegram каталоге, включая не только интерфейсные элементы, но и сами описания продуктов, компонентов и их характеристик. Обеспечить поддержку 15 языков для всех текстовых данных, связанных с продуктами.

### 🔍 Анализ текущей ситуации

#### **Текущее состояние:**
- ✅ **Интерфейс локализован**: Меню, кнопки, сообщения (15 языков)
- ✅ **Система локализации работает**: Localization класс, UserSettings, миксины
- ❌ **Данные продуктов НЕ локализованы**: Названия, описания, характеристики только на русском
- ❌ **Organic components НЕ локализованы**: Описания компонентов только на русском
- ❌ **Нет базы данных**: Только JSON файлы в `bot/templates/`

#### **Проблемы:**
1. **Блокчейн не база данных**: Загрузка данных стоит газа и времени
2. **Shared components**: Organic components используются между продавцами
3. **Структура данных**: Описания хранятся в IPFS как JSON с русскими текстами
4. **Производительность**: Нужно минимизировать обращения к блокчейну

### 🏗️ Архитектурное решение

#### **1. Гибридная система локализации**

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │  Interface      │ │  Product Data   │ │  Components     │ │
│  │  (JSON Files)   │ │  (Hybrid)       │ │  (Shared)       │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │Localization     │ │ProductFormatter │ │ComponentCache   │ │
│  │Service          │ │Service          │ │Service          │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │  JSON Files     │ │  IPFS Cache     │ │  Memory Cache   │ │
│  │  (Interface)    │ │  (Product Data) │ │  (Components)   │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │  Templates/     │ │     IPFS        │ │   Blockchain    │ │
│  │  (15 Languages) │ │  (Metadata)     │ │  (References)   │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### **2. Стратегия хранения переводов**

**A. Интерфейсные элементы (существующее)**
- **Хранение**: JSON файлы в `bot/templates/`
- **Языки**: 15 языков
- **Обновление**: Ручное редактирование файлов

**B. Данные продуктов (новое)**
- **Хранение**: IPFS с мультиязычными метаданными
- **Структура**: JSON с переводами для каждого языка
- **Кэширование**: Локальный кэш + IPFS кэш

**C. Organic components (новое)**
- **Хранение**: Отдельные IPFS файлы для каждого компонента
- **Shared**: Переиспользование между продавцами
- **Кэширование**: Агрессивное кэширование (24 часа TTL)

### 📊 Структура данных

#### **1. Мультиязычные метаданные продукта**
```json
{
  "business_id": "amanita_powder_001",
  "versions": {
    "ru": {
      "title": "Порошок мухомора красного",
      "scientific_name": "Amanita muscaria",
      "generic_description": "Высушенный и измельченный порошок...",
      "effects": "Успокаивающее действие...",
      "shamanic": "В шаманских традициях...",
      "warnings": "Использовать с осторожностью..."
    },
    "en": {
      "title": "Red Fly Agaric Powder",
      "scientific_name": "Amanita muscaria",
      "generic_description": "Dried and ground powder...",
      "effects": "Calming effect...",
      "shamanic": "In shamanic traditions...",
      "warnings": "Use with caution..."
    }
  },
  "organic_components": [
    {
      "biounit_id": "amanita_muscaria",
      "description_cid": "QmComponentDescriptionCID",
      "proportion": "100%"
    }
  ],
  "categories": ["mushroom", "powder"],
  "forms": ["powder"],
  "species": "Amanita muscaria",
  "prices": [...],
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### **2. Мультиязычные описания компонентов**
```json
{
  "biounit_id": "amanita_muscaria",
  "versions": {
    "ru": {
      "generic_description": "Мухомор красный - гриб семейства мухоморовых...",
      "effects": "Содержит мусцимол и иботеновую кислоту...",
      "shamanic": "В сибирских шаманских традициях...",
      "warnings": "Токсичен в сыром виде...",
      "features": ["Успокаивающее", "Галлюциногенное", "Традиционное"]
    },
    "en": {
      "generic_description": "Red fly agaric - mushroom of the Amanitaceae family...",
      "effects": "Contains muscimol and ibotenic acid...",
      "shamanic": "In Siberian shamanic traditions...",
      "warnings": "Toxic when raw...",
      "features": ["Calming", "Hallucinogenic", "Traditional"]
    }
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 🔧 Техническая реализация

#### **1. Расширение ProductFormatterService**

```python
class ProductFormatterService(IProductFormatter):
    def __init__(self, localization_service: LocalizationService):
        self.localization_service = localization_service
        self.component_cache = ComponentCacheService()
    
    def format_product_main_info_for_telegram(self, product: Any, loc: Localization) -> str:
        """Форматирует основную информацию с локализацией"""
        # Получаем локализованные данные продукта
        localized_product = self.localization_service.get_localized_product(product, loc.lang)
        
        main_info_text = f"🏷️ <b>{localized_product['title']}</b>\n"
        main_info_text += f"🌿 <b>Вид:</b> {localized_product['scientific_name']}\n"
        
        # Локализованный статус
        if product.status == 1:
            status_text = loc.t('catalog.product.available_for_order')
        else:
            status_text = loc.t('catalog.product.temporarily_unavailable')
        main_info_text += f"✅ <b>Статус:</b> {status_text}\n"
        
        return main_info_text
    
    def format_product_description_for_telegram(self, product: Any, loc: Localization) -> str:
        """Форматирует детальное описание с локализацией"""
        # Получаем локализованные данные продукта
        localized_product = self.localization_service.get_localized_product(product, loc.lang)
        
        description_text = f"🏷️ <b>{localized_product['title']}</b>\n"
        description_text += f"🔬 <b>Научное название:</b> {localized_product['scientific_name']}\n\n"
        
        # Локализованное описание
        if localized_product.get('generic_description'):
            description_text += f"📖 <b>Описание:</b>\n{localized_product['generic_description']}\n\n"
        
        # Локализованные эффекты
        if localized_product.get('effects'):
            description_text += f"✨ <b>Эффекты:</b>\n{localized_product['effects']}\n\n"
        
        # Локализованная шаманская перспектива
        if localized_product.get('shamanic'):
            description_text += f"🧙‍♂️ <b>Шаманская перспектива:</b>\n{localized_product['shamanic']}\n\n"
        
        # Локализованные предупреждения
        if localized_product.get('warnings'):
            description_text += f"⚠️ <b>Предупреждения:</b>\n{localized_product['warnings']}\n\n"
        
        return description_text
```

#### **2. Новый LocalizationService**

```python
class LocalizationService:
    def __init__(self, storage_service: ProductStorageService, cache_service: ComponentCacheService):
        self.storage_service = storage_service
        self.cache_service = cache_service
        self.logger = logging.getLogger(__name__)
    
    def get_localized_product(self, product: Product, lang: str) -> Dict[str, Any]:
        """Получает локализованные данные продукта"""
        # Проверяем кэш
        cache_key = f"product_{product.business_id}_{lang}"
        cached_data = self.cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        # Загружаем метаданные из IPFS
        metadata = self.storage_service.download_json(product.cid)
        if not metadata:
            return self._get_fallback_data(product, lang)
        
        # Извлекаем локализованные данные
        localized_data = self._extract_localized_data(metadata, lang)
        
        # Кэшируем результат
        self.cache_service.set(cache_key, localized_data, ttl=3600)  # 1 час
        
        return localized_data
    
    def get_localized_component(self, component: OrganicComponent, lang: str) -> Dict[str, Any]:
        """Получает локализованные данные компонента"""
        # Проверяем кэш компонентов (более агрессивное кэширование)
        cache_key = f"component_{component.biounit_id}_{lang}"
        cached_data = self.cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        # Загружаем описание компонента из IPFS
        component_data = self.storage_service.download_json(component.description_cid)
        if not component_data:
            return self._get_fallback_component_data(component, lang)
        
        # Извлекаем локализованные данные компонента
        localized_data = self._extract_localized_component_data(component_data, lang)
        
        # Кэшируем результат (24 часа для компонентов)
        self.cache_service.set(cache_key, localized_data, ttl=86400)
        
        return localized_data
```

#### **3. ComponentCacheService для shared components**

```python
class ComponentCacheService:
    def __init__(self):
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """Получает данные из кэша"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(hours=24):
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl: int = 3600) -> None:
        """Сохраняет данные в кэш"""
        self.cache[key] = (data, datetime.now())
        self.logger.debug(f"Кэширован компонент: {key}")
```

### 📋 План реализации

#### **Этап 1: Подготовка инфраструктуры (1-2 дня)**
1. **Создать LocalizationService** для работы с мультиязычными данными
2. **Создать ComponentCacheService** для кэширования shared components
3. **Расширить ProductFormatterService** для поддержки локализации
4. **Создать утилиты** для миграции существующих данных

#### **Этап 2: Миграция данных (2-3 дня)**
1. **Создать скрипт миграции** для преобразования существующих метаданных
2. **Добавить переводы** для существующих продуктов (ru → en, es, de, fr)
3. **Создать shared components** с переводами
4. **Загрузить в IPFS** мультиязычные метаданные

#### **Этап 3: Интеграция с форматированием (1-2 дня)**
1. **Обновить ProductFormatterService** для использования LocalizationService
2. **Добавить fallback логику** для отсутствующих переводов
3. **Протестировать** на всех 15 языках
4. **Оптимизировать производительность** кэширования

#### **Этап 4: Тестирование и оптимизация (1-2 дня)**
1. **Создать тесты** для всех компонентов
2. **Протестировать производительность** с реальными данными
3. **Оптимизировать кэширование** на основе метрик
4. **Документировать** API и процессы

### 🎯 Критерии успеха

#### **Функциональные требования:**
- ✅ **Полная локализация** всех текстовых данных продуктов
- ✅ **Поддержка 15 языков** для всех элементов
- ✅ **Fallback на русский** при отсутствии переводов
- ✅ **Shared components** переиспользуются между продавцами
- ✅ **Производительность** не хуже текущей

#### **Технические требования:**
- ✅ **Минимальные обращения к блокчейну** (только при изменении версии)
- ✅ **Агрессивное кэширование** shared components (24 часа TTL)
- ✅ **Graceful degradation** при ошибках загрузки
- ✅ **Обратная совместимость** с существующими данными

#### **UX требования:**
- ✅ **Мгновенное переключение** языка без перезагрузки
- ✅ **Консистентная локализация** во всех элементах
- ✅ **Понятные fallback** при отсутствии переводов
- ✅ **Сохранение форматирования** и структуры

### 🚨 Риски и митигация

#### **Риск 1: Увеличение размера IPFS данных**
- **Митигация**: Сжатие JSON, оптимизация структуры
- **Мониторинг**: Отслеживание размера метаданных

#### **Риск 2: Снижение производительности**
- **Митигация**: Многоуровневое кэширование, lazy loading
- **Мониторинг**: Профилирование времени загрузки

#### **Риск 3: Сложность миграции данных**
- **Митигация**: Поэтапная миграция, rollback план
- **Мониторинг**: Тестирование на копии данных

### 📊 Метрики успеха

#### **Производительность:**
- **Время загрузки каталога**: < 3 секунд
- **Время переключения языка**: < 1 секунды
- **Использование кэша**: > 80% запросов

#### **Качество:**
- **Покрытие переводов**: > 90% для основных языков
- **Fallback срабатывания**: < 5% запросов
- **Ошибки локализации**: < 1% запросов

#### **Пользовательский опыт:**
- **Консистентность**: 100% элементов локализованы
- **Читаемость**: Сохранение форматирования и структуры
- **Удобство**: Мгновенное переключение языка

---

**Дата создания**: $(date)
**Статус**: В работе
**Приоритет**: Высокий
**Оценка времени**: 6-9 дней
**Ответственный**: AI Assistant + Development Team
