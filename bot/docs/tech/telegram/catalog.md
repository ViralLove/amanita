# Архитектура каталога в Telegram боте Amanita

## 📋 **Обзор системы**

Каталог продуктов в Telegram боте представляет собой многоуровневую архитектуру, которая обеспечивает:
- **Кэширование** для быстрого доступа к данным
- **Валидацию** через единую систему ValidationFactory
- **Хранение** в IPFS (Pinata/Arweave) с гибридными режимами коммуникации
- **Синхронизацию** с блокчейном для актуальности данных
- **Двухуровневое отображение** продуктов (изображение + детальное описание)
- **Оптимизированную навигацию** через callback-кнопки

## 🎯 **Ключевые архитектурные решения**

### **Структура отображения продуктов**
- **Сообщение 1**: Изображение с основной информацией (caption до 1024 символов)
- **Сообщение 2**: Детальное описание без ограничений длины
- **Единая клавиатура**: Кнопки "В корзину" и "К каталогу" для обоих сообщений
- **Чистый контент**: Описания продуктов без технических элементов

## 🏗️ **Архитектурные слои**

### 1. **Telegram Bot Layer** (`bot/handlers/catalog.py`)

```python
@router.callback_query(F.data == "menu:catalog")
async def show_catalog(callback: CallbackQuery):
    # 1. Получаем user_id и язык пользователя
    # 2. Получаем каталог через ProductRegistryService (с кэшированием)
    # 3. Для каждого продукта формируем описание и отправляем в чат
    # 4. Навигация размещается только в сообщении статуса загрузки
```

**Ключевые компоненты:**
- **Router**: Обработчик callback-запросов для каталога
- **Localization**: Многоязычная поддержка (ru/en)
- **UserSettings**: Управление настройками пользователя
- **ProductRegistryService**: Основной сервис для работы с продуктами
- **Two-Level Display**: Двухуровневое отображение продуктов

**Обработчики:**
```python
@router.callback_query(F.data == "scroll:catalog")
async def scroll_to_catalog(callback: CallbackQuery):
    # Умный скролл к началу каталога

@router.callback_query(F.data.startswith("product:details:"))
async def show_product_details(callback: CallbackQuery):
    # Двухуровневое отображение: изображение + детальное описание
```

### 2. **Service Layer** (`bot/services/product/`)

#### **ProductRegistryService** - Центральный координатор
```python
class ProductRegistryService:
    def __init__(self, 
                 blockchain_service: BlockchainService,
                 storage_service: ProductStorageService,
                 validation_service: ProductValidationService,
                 account_service: AccountService):
        self.cache_service = ProductCacheService()
        self.metadata_service = ProductMetadataService(storage_service)
        self.formatter_service = ProductFormatterService()
```

**Сервисы форматирования:**
```python
class ProductFormatterService:
    def format_product_main_info_for_telegram(self, product: Product, loc: Localization) -> str:
        # Форматирование основной информации для caption изображения
        
    def format_product_description_for_telegram(self, product: Product, loc: Localization) -> str:
        # Форматирование детального описания для отдельного сообщения
```

**Основные методы:**
- `async def get_all_products() -> List[Product]` - получение всех продуктов с кэшированием
- `async def get_product(product_id) -> Product` - получение конкретного продукта
- `async def create_product(product_data) -> dict` - создание нового продукта

**Стратегия кэширования:**
```python
CACHE_TTL = {
    'catalog': timedelta(minutes=5),      # Каталог продуктов
    'description': timedelta(hours=24),   # Описания продуктов
    'image': timedelta(hours=12)          # Изображения
}
```

#### **ProductCacheService** - Многоуровневое кэширование
```python
class ProductCacheService:
    def __init__(self):
        self.catalog_cache: Dict = {}      # {"version": int, "products": List[Product], "timestamp": datetime}
        self.description_cache: Dict[str, Tuple[Description, datetime]] = {}
        self.image_cache: Dict[str, Tuple[str, datetime]] = {}
```

**Валидация кэша:**
```python
def _validate_cached_data(self, data: Any, data_type: str) -> ValidationResult:
    if data_type == 'catalog':
        # Валидируем структуру каталога
        if isinstance(data, dict) and 'version' in data and 'products' in data:
            return ValidationResult.success()
        else:
            return ValidationResult.failure("Неверная структура каталога")
```

#### **ProductStorageService** - Адаптивное хранилище
```python
class ProductStorageService:
    def __init__(self, storage_provider=None):
        self.communication_type = STORAGE_COMMUNICATION_TYPE  # sync/async/hybrid
        self.ipfs = IPFSFactory().get_storage()
```

**Режимы коммуникации:**
- **`sync`**: Прямые вызовы для Pinata, моков
- **`async`**: Через `asyncio.run()` для Arweave
- **`hybrid`**: Комбинированный подход

**Метод `download_json`:**
```python
def download_json(self, cid: str) -> Optional[Dict[str, Any]]:
    # Автоматически адаптируется к типу провайдера и режиму коммуникации
    if self.communication_type == "sync":
        if hasattr(self.ipfs, 'download_json'):
            return self.ipfs.download_json(cid)  # Прямой вызов
        else:
            return asyncio.run(self.ipfs.download_json_async(cid))  # Fallback
```

### 3. **Storage Layer** (`bot/services/core/storage/`)

#### **IPFSFactory** - Фабрика провайдеров
```python
class IPFSFactory:
    def __init__(self):
        self.set_storage(STORAGE_TYPE)  # pinata/arweave
        
    def set_storage(self, storage_type: str):
        if storage_type.lower() == 'pinata':
            self.storage = SecurePinataUploader()
        elif storage_type.lower() == 'arweave':
            self.storage = ArWeaveUploader()
```

#### **SecurePinataUploader** - Синхронный провайдер
```python
def download_json(self, cid: str) -> Optional[Dict]:
    url = f"{self.gateway_url}/{cid}"
    response = self._make_request('GET', url)
    return response.json()
```

**Особенности:**
- **Синхронные вызовы** - блокирующие операции
- **Rate limiting** - автоматические повторные попытки
- **Gateway URLs** - преобразование CID в HTTP URL

### 4. **Validation Layer** (`bot/validation/`)

#### **ValidationFactory** - Централизованная валидация
```python
class ValidationFactory:
    @classmethod
    def get_product_validator(cls) -> ProductValidator:
        if cls._product_validator is None:
            cls._product_validator = ProductValidator()
        return cls._product_validator
```

**Доступные валидаторы:**
- `CIDValidator` - валидация IPFS CID
- `ProductValidator` - валидация структуры продукта
- `PriceValidator` - валидация цен
- `ProportionValidator` - валидация пропорций

#### **ProductValidator** - Валидация продуктов
```python
class ProductValidator(ValidationRule[Dict[str, Any]]):
    def validate(self, value: Dict[str, Any]) -> ValidationResult:
        # Проверяем обязательные поля
        required_fields = ['business_id', 'title', 'cover_image_url', 'species', 'organic_components']
        for field in required_fields:
            if field not in value:
                return ValidationResult.failure(f"Отсутствует обязательное поле: {field}")
```

### 5. **Blockchain Layer** (`bot/services/core/blockchain.py`)

#### **BlockchainService** - Взаимодействие с смарт-контрактами
```python
class BlockchainService:
    def get_catalog_version(self) -> int:
        """Получает текущую версию каталога"""
        return self._call_contract_read_function(
            "ProductRegistry", "getMyCatalogVersion", 0
        )
    
    def get_all_products(self) -> List[dict]:
        """Получает все продукты из блокчейна"""
        product_ids = self._call_contract_read_function(
            "ProductRegistry", "getAllActiveProductIds", []
        )
        # Получаем полные данные для каждого продукта
        products = []
        for product_id in product_ids:
            product = self._call_contract_read_function(
                "ProductRegistry", "getProduct", None, product_id
            )
            if product:
                products.append(product)
        return products
```

## 🔄 **Поток данных каталога**

### **При запуске бота:**
```python
# bot/main.py
async def preload_catalog():
    await product_registry_service.get_all_products()
    logger.info("Фоновая загрузка каталога завершена!")

asyncio.create_task(preload_catalog())
```

### **При запросе каталога:**
1. **Проверка кэша** - `cache_service.get_cached_item("catalog", "catalog")`
2. **Валидация версии** - сравнение с `blockchain_service.get_catalog_version()`
3. **Загрузка из блокчейна** (если кэш устарел)
4. **Десериализация продуктов** - `_deserialize_product()`
5. **Обновление кэша** - `cache_service.set_cached_item()`
6. **Отображение с навигацией** - навигация только в сообщении статуса

### **При запросе деталей продукта:**
1. **Получение продукта** - `product_registry_service.get_all_products()`
2. **Форматирование основной информации** - `formatter_service.format_product_main_info_for_telegram()`
3. **Форматирование детального описания** - `formatter_service.format_product_description_for_telegram()`
4. **Отправка изображения** - `answer_photo` с caption и клавиатурой
5. **Отправка описания** - `answer` с детальным текстом и той же клавиатурой

### **При десериализации продукта:**
1. **Загрузка метаданных** - `storage_service.download_json(ipfs_cid)`
2. **Валидация данных** - `validation_service.validate_product_data()`
3. **Создание объекта Product** - `Product.from_dict()`

## 🎨 **Форматирование и динамическое отображение**

### **🏗️ Архитектура форматирования**

#### **ProductFormatterService** - Центральный сервис форматирования
```python
class ProductFormatterService(IProductFormatter):
    def __init__(self, config: Optional[ProductFormatterConfig] = None):
        self.config = config or ProductFormatterConfig()
        self.logger = logging.getLogger(__name__)
```

**Ключевые возможности:**
- **Конфигурируемое форматирование** через `ProductFormatterConfig`
- **Логирование операций** с детальным трекингом
- **Обработка ошибок** с fallback стратегиями
- **Расширяемость** для различных стратегий форматирования

#### **ProductFormatterConfig** - Гибкая конфигурация
```python
@dataclass
class ProductFormatterConfig:
    max_text_length: int = 4000
    enable_emoji: bool = True
    enable_html: bool = True
    truncate_text: bool = True
    
    emoji_mapping: Dict[str, str] = {
        'product': '🏷️', 'species': '🌿', 'status_available': '✅',
        'composition': '🔬', 'pricing': '💰', 'details': '📋',
        'shamanic': '🧙‍♂️', 'warnings': '⚠️', 'dosage': '💊'
    }
    
    text_templates: Dict[str, str] = {
        'truncate_indicator': '... <i>Текст обрезан для Telegram</i>',
        'section_separator': '\n', 'component_separator': '\n'
    }
```

### **📱 Двухуровневое отображение продуктов**

#### **Уровень 1: Основная информация (Caption)**
```python
def format_product_main_info_for_telegram(product, loc: Localization) -> str:
    # Оптимизировано для caption изображения (до 1024 символов)
    # Включает: название, вид, статус, научное название, состав, цены, формы, категории
    return main_info_text
```

**Содержимое основного сообщения:**
- **🏷️ Название продукта** - самое важное для идентификации
- **🌿 Вид продукта** - для понимания что это
- **✅ Статус** - активен ли для покупки
- **🔬 Научное название** - для точной идентификации
- **🔬 Состав** - базовый список компонентов
- **💰 Цены** - с валютами и весами
- **📦 Формы** - доступные варианты
- **🏷️ Категории** - классификация продукта

#### **Уровень 2: Детальное описание**
```python
def format_product_description_for_telegram(product, loc: Localization) -> str:
    # Без ограничений длины, полный нарративный контент
    # Включает: активные компоненты, эффекты, шаманская перспектива, предостережения
    return description_text
```

**Содержимое детального сообщения:**
- **🔬 Детальный состав** - полная информация о компонентах
- **📖 Описания компонентов** - детальные характеристики
- **✨ Эффекты** - воздействие на организм
- **🧙‍♂️ Шаманская перспектива** - традиционное применение
- **⚠️ Предупреждения** - важные предостережения
- **💊 Дозировка** - инструкции по применению
- **🌟 Особенности** - уникальные свойства

### **⚡ Динамическое отображение прогресса**

#### **Прогресс-индикатор загрузки каталога**
```python
# Отправляем сообщение о прогрессе с навигацией
progress_message = await callback.message.answer(
    f"📦 Загружаем каталог: 0/{len(products)} продуктов...\n\n"
    f"🔍 <b>Навигация:</b> #catalog"
)

# Обновляем прогресс для каждого продукта
for i, product in enumerate(products):
    # ... отправка продукта ...
    await progress_message.edit_text(f"📦 Загружаем каталог: {i+1}/{len(products)} продуктов...")

# Удаляем сообщение о прогрессе и отправляем финальное
await progress_message.delete()
await callback.message.answer(f"✅ Каталог загружен! Всего продуктов: {len(products)}")
```

**Особенности прогресс-индикатора:**
- **Реальное время** - обновление после каждого продукта
- **Навигация** - хэштеги для быстрого доступа
- **Финальная статистика** - общее количество загруженных продуктов
- **Автоочистка** - удаление временных сообщений

#### **Индикатор загрузки деталей продукта**
```python
# Отправляем сообщение о загрузке
loading_message = await callback.message.answer(loc.t("catalog.loading"))

# ... получение и форматирование продукта ...

# Удаляем сообщение о загрузке
await loading_message.delete()
```

### **🎯 Умные клавиатуры и навигация**

#### **Контекстные клавиатуры**
```python
# Каталог: кнопки для каждого продукта
def get_product_keyboard(product_id: str, loc: Localization) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📖 Подробнее", callback_data=f"product:details:{product_id}"),
            InlineKeyboardButton(text="🛒 В корзину", callback_data=f"product:cart:{product_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Детальный просмотр: умная навигация
def get_product_details_keyboard_with_scroll(product_id: str, loc: Localization) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🛒 В корзину", callback_data=f"product:cart:{product_id}"),
            InlineKeyboardButton(text="🔙 К каталогу", callback_data="scroll:catalog")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
```

**Особенности навигации:**
- **Контекстные действия** - разные кнопки для разных состояний
- **Умный скролл** - `scroll:catalog` вместо перезагрузки
- **Консистентность** - одинаковая клавиатура для обоих сообщений продукта
- **Минимализм** - только необходимые действия

#### **Умная навигация через хэштеги**
```python
@router.callback_query(F.data == "scroll:catalog")
async def scroll_to_catalog(callback: CallbackQuery):
    scroll_message = (
        f"📚 <b>Каталог продуктов</b>\n\n"
        f"• #catalog - основной каталог\n"
        f"💡 <i>Нажмите на хэштег для быстрого перехода к нужному разделу</i>"
    )
    await callback.message.answer(scroll_message, parse_mode="HTML")
```

### **🔄 Адаптивная обработка ошибок**

#### **Fallback стратегии форматирования**
```python
try:
    formatted_sections = formatter_service.format_product_for_telegram(product, loc)
    product_text = (
        formatted_sections['main_info'] +
        formatted_sections['composition'] +
        formatted_sections['pricing'] +
        formatted_sections['details']
    )
except Exception as e:
    logger.error(f"Ошибка сервиса форматирования: {e}")
    # Fallback форматирование
    product_text = f"🏷️ <b>{getattr(product, 'title', 'Продукт')}</b>\n❌ Ошибка при форматировании"
```

#### **Адаптивная отправка изображений**
```python
if product.cover_image_url:
    try:
        # Попытка загрузки изображения
        image_url = storage_service.get_public_url(product.cover_image_url)
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    # Успешная загрузка - отправляем с изображением
                    await callback.message.answer_photo(FSInputFile(image_path), caption=product_text)
                else:
                    # Fallback: только текст
                    await callback.message.answer(product_text, reply_markup=keyboard)
    except Exception as e:
        # Fallback: только текст
        await callback.message.answer(product_text, reply_markup=keyboard)
else:
    # Нет изображения - только текст
    await callback.message.answer(product_text, reply_markup=keyboard)
```

### **📏 Умная обрезка текста**

#### **Адаптивная обрезка для Telegram**
```python
# Обрезаем текст если он слишком длинный для Telegram
original_length = len(product_text)
product_text = formatter_service._truncate_text(product_text)
final_length = len(product_text)

if original_length != final_length:
    logger.info(f"Текст продукта обрезан: {original_length} -> {final_length} символов")
```

#### **Конфигурируемые ограничения**
```python
def should_truncate(self, text: str) -> bool:
    return self.truncate_text and len(text) > self.max_text_length

def _truncate_text(self, text: str) -> str:
    if not self.config.should_truncate(text):
        return text
    
    # Обрезаем с учетом HTML тегов
    truncated = text[:self.config.max_text_length - len(self.config.get_template('truncate_indicator'))]
    return truncated + self.config.get_template('truncate_indicator')
```

### **🌐 Многоязычная поддержка**

#### **Локализованные сообщения**
```python
# Получаем язык пользователя
user_id = callback.from_user.id
lang = user_settings.get_language(user_id)
loc = Localization(lang)

# Используем локализованные строки
await callback.message.answer(loc.t("catalog.loading"))
await callback.message.answer(loc.t("catalog.empty"))
```

#### **Локализованные статусы продуктов**
```python
if product.status == 1:
    status_emoji = self.config.get_emoji('status_available')
    status_text = loc.t('catalog.product.available_for_order')
else:
    status_emoji = self.config.get_emoji('status_unavailable')
    status_text = loc.t('catalog.product.temporarily_unavailable')
```

### **🎨 Визуальные улучшения**

#### **Эмодзи-навигация**
- **🏷️ Продукты** - основная категория
- **🌿 Виды** - классификация по типу
- **✅ Статусы** - доступность для заказа
- **💰 Цены** - финансовая информация
- **🔬 Состав** - технические детали
- **🧙‍♂️ Шаманская перспектива** - традиционное применение

#### **Визуальные разделители**
```python
# Добавляем разделитель между продуктами (кроме последнего)
if i < len(products) - 1:
    await callback.message.answer("☀️" * 8)
```

#### **HTML-разметка для читаемости**
```python
# Используем HTML для форматирования
await callback.message.answer_photo(
    FSInputFile(image_path),
    caption=product_text,
    parse_mode="HTML",
    reply_markup=keyboard
)
```

### **⚡ Оптимизация производительности**

#### **Кэширование форматирования**
- **Кэш продуктов** - избегаем повторного форматирования
- **Кэш изображений** - временные файлы с автоочисткой
- **Кэш локализации** - переиспользование переводов

#### **Асинхронная загрузка**
```python
# Параллельная загрузка изображений
async with aiohttp.ClientSession() as session:
    async with session.get(image_url) as response:
        if response.status == 200:
            # Обработка в фоне
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                tmp_file.write(await response.read())
```

#### **Автоочистка ресурсов**
```python
# Удаляем временные файлы
os.unlink(image_path)

# Удаляем временные сообщения
await loading_message.delete()
await progress_message.delete()
```

## 🔧 **Конфигурация и настройки**

### **Переменные окружения:**
```bash
# .env
STORAGE_TYPE=pinata                    # pinata/arweave
STORAGE_COMMUNICATION_TYPE=sync        # sync/async/hybrid
PINATA_API_KEY=your_pinata_key
PINATA_SECRET_KEY=your_pinata_secret
ARWEAVE_PRIVATE_KEY=your_arweave_key
```

### **Настройка логирования:**
```python
# bot/config.py
LOG_LEVEL = "INFO"
LOG_FILE = "logs/amanita_api.log"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

## 📊 **Метрики и производительность**

### **Время жизни кэша:**
- **Каталог**: 5 минут (часто обновляется)
- **Описания**: 24 часа (стабильные данные)
- **Изображения**: 12 часов (медиа-контент)

### **Стратегии оптимизации:**
1. **Фоновая загрузка** при старте бота
2. **Многоуровневое кэширование** в памяти
3. **Валидация версий** для инвалидации устаревших данных
4. **Адаптивные режимы коммуникации** с хранилищами

## 🚨 **Обработка ошибок**

### **Типы ошибок:**
- **StorageError** - проблемы с IPFS/Arweave
- **ValidationError** - невалидные данные
- **BlockchainError** - проблемы с блокчейном
- **CacheError** - проблемы с кэшированием

### **Стратегии восстановления:**
1. **Автоматические повторные попытки** для сетевых ошибок
2. **Fallback на альтернативные провайдеры**
3. **Очистка поврежденного кэша**
4. **Логирование всех ошибок** для диагностики

## 🔮 **Будущие улучшения**

### **Планируемые функции:**
1. **Фильтрация и поиск** по категориям (грибы, травы, добавки)
2. **Пагинация** для больших каталогов
3. **Оффлайн-режим** с локальным кэшем
4. **Персонализация** - избранные продукты, история просмотров
5. **Уведомления** о новых продуктах и акциях

### **Технические улучшения:**
1. **Redis кэш** для распределенных систем
2. **CDN** для изображений
3. **WebSocket** для real-time обновлений
4. **GraphQL** для гибких запросов
5. **Микросервисная архитектура** для масштабирования

---

## 📋 **Итоговая архитектура**

### **Ключевые компоненты:**
1. **Двухуровневое отображение** - изображение + детальное описание
2. **Многоуровневое кэширование** - оптимизация производительности
3. **Адаптивное хранилище** - поддержка различных провайдеров
4. **Централизованная валидация** - единая система проверки данных
5. **Блокчейн-синхронизация** - актуальность данных

### **Преимущества архитектуры:**
1. **Масштабируемость** - модульная структура
2. **Производительность** - многоуровневое кэширование
3. **Надежность** - обработка ошибок и fallback стратегии
4. **Гибкость** - поддержка различных провайдеров хранения
5. **UX-оптимизация** - двухуровневое отображение контента