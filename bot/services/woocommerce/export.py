"""
SKU Generation и Helper Functions для WooCommerce Export

Модуль для генерации SKU (Stock Keeping Unit) для продуктов и вариаций
и вспомогательных функций для экспорта в формате WooCommerce.
Обеспечивает уникальность и соответствие архитектуре.

Соответствует разделам 2.5, 4.3, 4.4, 4.5 docs-woo-export-architecture.md

Функции:
- generate_product_sku(): Генерация SKU для основного продукта
- generate_variation_sku(): Генерация SKU для вариации
- get_localized_title(): Получение локализованного названия продукта
- format_product_description_html(): Форматирование описания в HTML
- prepare_images_list(): Подготовка списка изображений
- validate_sku_uniqueness(): Валидация уникальности SKU
"""

import logging
import re
from typing import List, Dict
from model.product import Product, PriceInfo
from services.common.localization import Localization
from services.woocommerce.html_format_adapter import HTMLFormatAdapter

logger = logging.getLogger(__name__)

_IPFS_V0_CID_PATTERN = re.compile(r'^Qm[1-9A-HJ-NP-Za-km-z]{44}$')
_IPFS_V1_CID_PATTERN = re.compile(r'^bafy[A-Za-z2-7]{55}$')
_ARWEAVE_TXID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{43}$')


class WooCommerceColumns:
    """Константы для названий колонок WooCommerce CSV.
    
    Все названия колонок должны использовать константы из этого класса
    для обеспечения единообразия и упрощения поддержки.
    """
    
    # Основные колонки (в порядке появления в стандартном CSV)
    ID = "ID"  # WooCommerce ID для обновления существующих продуктов
    TYPE = "Type"
    PARENT = "Parent"
    SKU = "SKU"
    VARIATION_SKU = "Variation SKU"
    NAME = "Name"
    DESCRIPTION = "Description"
    SHORT_DESCRIPTION = "Short description"
    IMAGES = "Images"
    STATUS = "Status"
    STOCK_STATUS = "Stock status"
    STOCK = "Stock"
    REGULAR_PRICE = "Regular price"  # Стандартное название WooCommerce
    SALE_PRICE = "Sale price"  # Для будущего использования
    CATEGORIES = "Categories"
    
    @staticmethod
    def get_standard_order():
        """Возвращает список стандартных колонок в правильном порядке.
        
        Порядок соответствует стандарту WooCommerce CSV импорта.
        """
        return [
            WooCommerceColumns.ID,
            WooCommerceColumns.TYPE,
            WooCommerceColumns.PARENT,
            WooCommerceColumns.SKU,
            WooCommerceColumns.VARIATION_SKU,
            WooCommerceColumns.NAME,
            WooCommerceColumns.DESCRIPTION,
            WooCommerceColumns.SHORT_DESCRIPTION,
            WooCommerceColumns.IMAGES,
            WooCommerceColumns.STATUS,
            WooCommerceColumns.STOCK_STATUS,
            WooCommerceColumns.STOCK,
            WooCommerceColumns.REGULAR_PRICE,
            WooCommerceColumns.CATEGORIES
        ]


def _image_identifier_to_public_url(identifier: str) -> str:
    """
    Нормализует поле изображения для WooCommerce CSV.
    
    В проекте `cover_image_url` часто является не URL, а идентификатором хранилища:
    - IPFS CID (Qm.../bafy...)
    - Arweave txId (43 base64url)
    
    WooCommerce CSV ожидает URL. Поэтому:
    - если уже URL (http/https) → возвращаем как есть
    - если Arweave txId → https://arweave.net/<txId>
    - если IPFS CID → https://ipfs.io/ipfs/<cid>
    - иначе → возвращаем как есть (может быть неимпортируемо, но не блокирует экспорт)
    """
    if not identifier:
        return ""
    
    value = identifier.strip()
    if not value:
        return ""
    
    if value.startswith("http://") or value.startswith("https://"):
        return value
    
    if _ARWEAVE_TXID_PATTERN.match(value):
        return f"https://arweave.net/{value}"
    
    if _IPFS_V0_CID_PATTERN.match(value) or _IPFS_V1_CID_PATTERN.match(value):
        return f"https://ipfs.io/ipfs/{value}"
    
    return value


def generate_product_sku(product: Product, form: str) -> str:
    """
    Генерирует SKU для основного продукта (Variable Product в WooCommerce).
    
    Формат: {blockchain_id}_{form}
    Пример: 123_dried
    
    Args:
        product: Продукт
        form: Форма продукта (например, "dried", "powder", "capsules")
        
    Returns:
        str: SKU продукта
        
    Raises:
        ValueError: Если blockchain_id или form невалидны
    """
    # Валидация blockchain_id
    if product.blockchain_id is None:
        raise ValueError("blockchain_id не может быть None")
    if isinstance(product.blockchain_id, str) and not product.blockchain_id.strip():
        raise ValueError("blockchain_id не может быть пустой строкой")
    if isinstance(product.blockchain_id, int) and product.blockchain_id < 0:
        raise ValueError("blockchain_id не может быть отрицательным")
    
    # Валидация form
    if not form:
        raise ValueError("form не может быть None или пустым")
    if not isinstance(form, str):
        raise ValueError("form должен быть строкой")
    if not form.strip():
        raise ValueError("form не может быть пустой строкой или состоять только из пробелов")
    
    return f"{product.blockchain_id}_{form}"


def generate_variation_sku(
    product: Product, 
    form: str, 
    price_info: PriceInfo
) -> str:
    """
    Генерирует SKU для вариации (Variation в WooCommerce).
    
    Формат: {blockchain_id}_{form}_{quantity}{unit}_{currency}
    Пример: 123_dried_100g_EUR
    Пример: 456_tincture_50ml_USD
    
    Args:
        product: Продукт
        form: Форма продукта
        price_info: Информация о цене (должна иметь quantity и unit)
        
    Returns:
        str: SKU вариации
        
    Raises:
        ValueError: Если цена не имеет quantity и unit
    """
    # Получаем базовый SKU продукта
    base_sku = generate_product_sku(product, form)
    
    # Определяем количество и единицу измерения
    if price_info.is_quantity_based:
        quantity = int(price_info.quantity)  # Конвертируем Decimal в int для SKU
        unit = price_info.unit
        quantity_unit = f"{quantity}{unit}"
    else:
        # Простые цены не поддерживаются для вариаций WooCommerce
        raise ValueError(
            f"Цена для продукта {product.business_id} (форма: {form}) не имеет quantity и unit. "
            f"Вариации WooCommerce требуют конкретные атрибуты (quantity/unit)."
        )
    
    # Валюта всегда в SKU
    currency = price_info.currency
    
    return f"{base_sku}_{quantity_unit}_{currency}"


def get_localized_title(
    product: Product,
    language: str,
    html_adapter: HTMLFormatAdapter
) -> str:
    """
    Получает локализованное название продукта.
    
    ✅ РЕЮЗ: Использует HTMLFormatAdapter.get_product_title(), 
    который реюзит ProductFormatterService._get_product_title() (та же логика, что Telegram).
    
    Примечание: HTMLFormatAdapter.get_product_title() уже имеет обработку ошибок с fallback.
    Дополнительный try-except в обертке обеспечивает дополнительную защиту и логирование
    на уровне экспорта.
    
    Args:
        product: Продукт
        language: Язык локализации (например, "ru", "en")
        html_adapter: HTML адаптер (содержит formatter_service)
        
    Returns:
        str: Локализованное название продукта
    """
    try:
        # ✅ РЕЮЗ: Используем адаптер, который реюзит логику из ProductFormatterService
        return html_adapter.get_product_title(product, language)
        
    except Exception as e:
        logger.error(
            f"[Export] Ошибка получения локализованного названия для {product.business_id}: {e}",
            exc_info=True
        )
        # Fallback: возвращаем базовое название
        return getattr(product, 'title', 'Продукт')


def format_product_description_html(
    product: Product,
    language: str,
    html_adapter: HTMLFormatAdapter
) -> str:
    """
    Форматирует описание продукта в HTML для WooCommerce.
    
    ✅ РЕЮЗ: Использует HTMLFormatAdapter.format_product_html(), который реюзит 
    логику структурирования из ProductFormatterService.
    
    ❌ АДАПТЕР: Создает Localization объект из language строки.
    
    Примечание: Localization(language) создается при каждом вызове.
    Для MVP это приемлемо. Если функция вызывается часто, можно добавить кэширование.
    
    Args:
        product: Продукт для форматирования
        language: Язык локализации (например, "ru", "en")
        html_adapter: HTML адаптер (содержит formatter_service)
        
    Returns:
        str: HTML описание продукта
    """
    try:
        # Создаем Localization объект из language строки
        loc = Localization(language)
        
        # ✅ РЕЮЗ: Используем адаптер, который реюзит общую логику структурирования
        html = html_adapter.format_product_html(product, loc)
        
        return html
        
    except Exception as e:
        logger.error(
            f"[Export] Ошибка форматирования описания для {product.business_id}: {e}",
            exc_info=True
        )
        # Fallback: возвращаем базовое описание
        return f"<p>{product.title}</p>"


def prepare_images_list(
    products: List[Product],
    language: str,
    html_adapter: HTMLFormatAdapter
) -> List[Dict]:
    """
    Подготавливает список изображений для ручной загрузки.
    Пропускает продукты без изображений.
    
    ✅ РЕЮЗ: Использует HTMLFormatAdapter.get_product_title() для получения локализованных названий.
    ✅ РЕЮЗ: Использует generate_product_sku() для генерации SKU (функция в том же файле).
    
    Args:
        products: Список продуктов
        language: Язык для локализации названий
        html_adapter: HTML адаптер (для получения локализованных названий)
        
    Returns:
        List[Dict]: Список изображений с метаданными:
            - product_sku: SKU продукта
            - product_name: Локализованное название
            - image_url: URL изображения
            - form: Форма продукта
            - blockchain_id: ID в блокчейне
            - business_id: Бизнес-идентификатор
    """
    images_list = []
    
    for product in products:
        for form in product.forms:
            # Проверяем наличие изображения
            if product.cover_image_url and product.cover_image_url.strip():
                # ✅ РЕЮЗ: Используем адаптер для получения локализованного названия
                title = html_adapter.get_product_title(product, language)
                
                # ✅ РЕЮЗ: Используем generate_product_sku() для генерации SKU
                # Функция находится в том же файле, прямой вызов без импорта
                product_sku = generate_product_sku(product, form)
                
                images_list.append({
                    "product_sku": product_sku,
                    "product_name": title,
                    "image_url": _image_identifier_to_public_url(product.cover_image_url),
                    "form": form,
                    "blockchain_id": product.blockchain_id,
                    "business_id": product.business_id
                })
            # Если изображения нет, пропускаем этот продукт
    
    return images_list


def validate_sku_uniqueness(
    csv_rows: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Валидирует уникальность SKU и добавляет суффикс к дубликатам.
    
    Обрабатывает дубликаты SKU в CSV строках, добавляя суффиксы (_1, _2, и т.д.)
    к повторяющимся значениям. Также обновляет поле 'Parent' если оно ссылается
    на дубликат.
    
    Args:
        csv_rows: Список строк CSV (каждая строка - словарь с ключами-заголовками)
        
    Returns:
        List[Dict[str, str]]: Список строк с уникальными SKU
        
    Пример:
        Вход: [{'SKU': '123_dried'}, {'SKU': '123_dried'}]
        Выход: [{'SKU': '123_dried'}, {'SKU': '123_dried_1'}]
    """
    seen_skus = {}
    result = []
    
    for row in csv_rows:
        # Извлекаем SKU из строки (может быть в 'SKU' или 'Variation SKU')
        sku = row.get(WooCommerceColumns.SKU) or row.get(WooCommerceColumns.VARIATION_SKU, '')
        
        # Если SKU отсутствует, добавляем строку без изменений
        if not sku:
            result.append(row)
            continue
            
        # Проверяем, встречался ли этот SKU ранее
        if sku in seen_skus:
            # Увеличиваем счетчик дубликатов
            seen_skus[sku] += 1
            suffix = f"_{seen_skus[sku]}"
            new_sku = f"{sku}{suffix}"
            
            logger.warning(f"[Export] Дубликат SKU обнаружен: {sku} → {new_sku}")
            
            # Обновляем SKU в строке
            if WooCommerceColumns.SKU in row:
                row[WooCommerceColumns.SKU] = new_sku
            elif WooCommerceColumns.VARIATION_SKU in row:
                row[WooCommerceColumns.VARIATION_SKU] = new_sku
            
            # Обновляем Parent если он ссылается на дубликат
            if WooCommerceColumns.PARENT in row and row[WooCommerceColumns.PARENT] == sku:
                row[WooCommerceColumns.PARENT] = new_sku
        else:
            # Первое вхождение SKU (счетчик = 0, суффикс не добавляется)
            seen_skus[sku] = 0
        
        result.append(row)
    
    return result


# ============================================================================
# Приватные функции для генерации CSV строк
# ============================================================================

def _determine_product_type(product: Product, form: str) -> str:
    """
    Определяет тип продукта WooCommerce (simple или variable).
    
    Логика:
    - Если одна цена или цены без weight/volume → simple
    - Если несколько цен с weight/volume (разные значения) → variable
    
    Args:
        product: Продукт
        form: Форма продукта
        
    Returns:
        str: "simple" или "variable"
    """
    # Получить все цены для конкретной формы
    prices_for_form = [
        p for p in product.prices 
        if p.form == form
    ]
    
    # Если цен нет → simple (с предупреждением)
    if not prices_for_form:
        logger.warning(
            f"[Export] Продукт {product.business_id} (форма: {form}) не имеет цен. "
            f"Создается simple продукт."
        )
        return "simple"
    
    # Если одна цена → simple
    if len(prices_for_form) == 1:
        return "simple"
    
    # Если несколько цен:
    # Проверить наличие quantity/unit
    has_quantity = any(
        p.is_quantity_based 
        for p in prices_for_form
    )
    
    # Если все цены без quantity/unit → simple
    if not has_quantity:
        return "simple"
    
    # Если есть хотя бы одна цена с quantity/unit и несколько цен → variable
    return "variable"


def _collect_attributes(product: Product, form: str) -> Dict[str, str]:
    """
    Собирает атрибуты для родительского продукта (variable).
    
    Args:
        product: Продукт
        form: Форма продукта
        
    Returns:
        Dict[str, str]: Словарь с атрибутами (Attribute 1 name, Attribute 1 value(s), ...)
    """
    attributes = {}
    
    # Получить все цены для формы с quantity/unit
    prices_with_quantity = [
        p for p in product.prices 
        if p.form == form and p.is_quantity_based
    ]
    
    if not prices_with_quantity:
        return attributes
    
    # Собрать уникальные quantity/unit
    quantity_values = set()
    for price in prices_with_quantity:
        quantity = int(price.quantity)  # Decimal в int для SKU
        quantity_values.add(f"{quantity}{price.unit}")
    
    # Собрать уникальные валюты
    currencies = set(p.currency for p in prices_with_quantity)
    
    # Сформировать атрибуты
    if quantity_values:
        # Attribute 1: quantity
        attributes["Attribute 1 name"] = "pa_quantity"
        
        # Значения через |
        attributes["Attribute 1 value(s)"] = "|".join(sorted(quantity_values))
        attributes["Attribute 1 visible"] = "1"
        attributes["Attribute 1 global"] = "1"
    
    # Attribute 2: currency (только если есть разные валюты)
    if len(currencies) > 1:
        attributes["Attribute 2 name"] = "pa_currency"
        attributes["Attribute 2 value(s)"] = "|".join(sorted(currencies))
        attributes["Attribute 2 visible"] = "1"
        attributes["Attribute 2 global"] = "1"
    
    return attributes


def _collect_component_blockchain_ids(product: Product) -> str:
    """
    Собирает blockchain_id компонентов в строку через запятую.
    
    Args:
        product: Продукт
        
    Returns:
        str: Строка с blockchain_id через запятую (например, "123,456,789") или "" если компонентов нет
    """
    if not product.organic_components:
        return ""
    
    # Извлечь blockchain_id из компонентов
    # blockchain_id всегда есть (из контракта), но для безопасности проверяем
    component_ids = []
    for comp in product.organic_components:
        if comp.blockchain_id is not None:
            component_ids.append(str(comp.blockchain_id))
        else:
            # Логируем предупреждение, но продолжаем (не должно происходить)
            logger.warning(
                f"[Export] Компонент {comp.component_id} продукта {product.business_id} "
                f"не имеет blockchain_id. Пропускаем в метаданных."
            )
    
    # Объединить через запятую
    return ",".join(component_ids)


# ============================================================================
# Публичные функции генерации CSV строк
# ============================================================================

def generate_simple_product_row(
    product: Product,
    form: str,
    language: str,
    html_adapter: HTMLFormatAdapter
) -> Dict[str, str]:
    """
    Генерирует CSV строку для простого продукта (simple).
    
    Args:
        product: Продукт
        form: Форма продукта
        language: Язык локализации
        html_adapter: HTML адаптер
        
    Returns:
        Dict[str, str]: Словарь с колонками CSV (включая meta:*)
    """
    row = {}
    
    # Основные поля
    row[WooCommerceColumns.TYPE] = "simple"
    row[WooCommerceColumns.SKU] = generate_product_sku(product, form)
    row[WooCommerceColumns.NAME] = get_localized_title(product, language, html_adapter)
    row[WooCommerceColumns.DESCRIPTION] = format_product_description_html(product, language, html_adapter)
    row[WooCommerceColumns.SHORT_DESCRIPTION] = ""  # Опционально, можно оставить пустым
    
    # Изображение (CID, можно конвертировать в URL позже)
    if product.cover_image_url and product.cover_image_url.strip():
        row[WooCommerceColumns.IMAGES] = _image_identifier_to_public_url(product.cover_image_url)
    else:
        row[WooCommerceColumns.IMAGES] = ""
    
    # Статус
    row[WooCommerceColumns.STATUS] = "Published" if product.status == 1 else "Draft"
    row[WooCommerceColumns.STOCK_STATUS] = "In stock"
    row[WooCommerceColumns.STOCK] = "50"  # По умолчанию
    
    # Цена (первая цена для формы или единственная)
    # Детальное логирование для диагностики проблемы с ценами
    logger.info(f"[Export] 🔍 Поиск цен для продукта {product.business_id}, форма: {form}")
    logger.info(f"[Export] 📋 Всего цен в продукте: {len(product.prices)}")
    logger.info(f"[Export] 📋 Все формы продукта: {product.forms}")
    
    # Логируем все цены с их полями
    if product.prices:
        logger.info(f"[Export] 📊 Детали всех цен продукта:")
        for i, price in enumerate(product.prices):
            logger.info(
                f"[Export]   Цена {i+1}/{len(product.prices)}: "
                f"price={price.price}, currency={price.currency}, "
                f"form={repr(price.form)}, "
                f"quantity={price.quantity}, unit={price.unit}"
            )
    else:
        logger.warning(f"[Export] ⚠️ У продукта {product.business_id} вообще нет цен в списке product.prices")
    
    prices_for_form = [p for p in product.prices if p.form == form]
    logger.info(f"[Export] 🔍 Найдено цен для формы '{form}': {len(prices_for_form)}")
    
    if prices_for_form:
        first_price = prices_for_form[0]
        row[WooCommerceColumns.REGULAR_PRICE] = str(float(first_price.price))  # Decimal в float, затем в str
        logger.info(
            f"[Export] ✅ Цена установлена для {product.business_id} (форма: {form}): "
            f"{row[WooCommerceColumns.REGULAR_PRICE]} {first_price.currency}"
        )
    else:
        row[WooCommerceColumns.REGULAR_PRICE] = ""
        logger.warning(
            f"[Export] ⚠️ Продукт {product.business_id} (форма: {form}) не имеет цен. "
            f"Цена не установлена."
        )
        # Дополнительная диагностика
        if product.prices:
            forms_in_prices = [p.form for p in product.prices]
            logger.warning(
                f"[Export] ⚠️ У продукта есть {len(product.prices)} цена(и), но ни одна не соответствует форме '{form}'. "
                f"Формы цен: {forms_in_prices}"
            )
            logger.warning(
                f"[Export] ⚠️ Сравнение: ищем форму '{form}' (тип: {type(form).__name__}), "
                f"но в ценах формы: {[repr(f) for f in forms_in_prices]}"
            )
        else:
            logger.warning(
                f"[Export] ⚠️ У продукта вообще нет цен в списке product.prices"
            )
    
    # Категории через запятую
    if product.categories:
        row[WooCommerceColumns.CATEGORIES] = ",".join(product.categories)
    else:
        row[WooCommerceColumns.CATEGORIES] = ""
    
    # Метаданные (включены в CSV для импорта)
    row["meta:blockchain_id"] = str(product.blockchain_id)
    row["meta:business_id"] = product.business_id
    row["meta:form"] = form
    row["meta:component_ids"] = _collect_component_blockchain_ids(product)
    
    return row


def generate_variable_product_row(
    product: Product,
    form: str,
    language: str,
    html_adapter: HTMLFormatAdapter
) -> Dict[str, str]:
    """
    Генерирует CSV строку для родительского продукта (variable).
    
    Args:
        product: Продукт
        form: Форма продукта
        language: Язык локализации
        html_adapter: HTML адаптер
        
    Returns:
        Dict[str, str]: Словарь с колонками CSV (включая атрибуты и meta:*)
    """
    row = {}
    
    # Основные поля
    row[WooCommerceColumns.TYPE] = "variable"
    row[WooCommerceColumns.SKU] = generate_product_sku(product, form)
    row[WooCommerceColumns.NAME] = get_localized_title(product, language, html_adapter)
    row[WooCommerceColumns.DESCRIPTION] = format_product_description_html(product, language, html_adapter)
    row[WooCommerceColumns.SHORT_DESCRIPTION] = ""  # Опционально
    
    # Изображение
    if product.cover_image_url and product.cover_image_url.strip():
        row[WooCommerceColumns.IMAGES] = _image_identifier_to_public_url(product.cover_image_url)
    else:
        row[WooCommerceColumns.IMAGES] = ""
    
    # Статус
    row[WooCommerceColumns.STATUS] = "Published" if product.status == 1 else "Draft"
    row[WooCommerceColumns.STOCK_STATUS] = "In stock"
    # Price не указывается для variable продукта (указывается в вариациях)
    
    # Атрибуты через _collect_attributes()
    attributes = _collect_attributes(product, form)
    row.update(attributes)
    
    # Метаданные (включены в CSV для импорта)
    row["meta:blockchain_id"] = str(product.blockchain_id)
    row["meta:business_id"] = product.business_id
    row["meta:form"] = form
    row["meta:component_ids"] = _collect_component_blockchain_ids(product)
    
    return row


def generate_variation_row(
    product: Product,
    form: str,
    price_info: PriceInfo,
    language: str,
    html_adapter: HTMLFormatAdapter
) -> Dict[str, str]:
    """
    Генерирует CSV строку для вариации.
    
    Args:
        product: Продукт
        form: Форма продукта
        price_info: Информация о цене (должна иметь quantity и unit)
        language: Язык локализации
        html_adapter: HTML адаптер
        
    Returns:
        Dict[str, str]: Словарь с колонками CSV (включая meta:*)
        
    Raises:
        ValueError: Если price_info не имеет quantity и unit
    """
    if not price_info.is_quantity_based:
        raise ValueError(
            f"Вариация требует price_info с quantity и unit. "
            f"Продукт: {product.business_id}, форма: {form}"
        )
    
    row = {}
    
    # Основные поля
    row[WooCommerceColumns.TYPE] = "variation"
    row[WooCommerceColumns.PARENT] = generate_product_sku(product, form)
    
    # SKU вариации: в WooCommerce вариации НЕ имеют SKU (поле пустое)
    # SKU используется только для Parent продукта, вариации идентифицируются по ID
    # При --reuse-woo-id вариации получают ID из mapping (mappings_by_variation_id)
    row[WooCommerceColumns.SKU] = ""
    row[WooCommerceColumns.VARIATION_SKU] = ""
    
    # Название вариации: локализованное название + quantity/unit + валюта
    base_title = get_localized_title(product, language, html_adapter)
    if price_info.is_quantity_based:
        quantity_str = f"{int(price_info.quantity)}{price_info.unit}"
    else:
        quantity_str = ""  # Простые цены без quantity/unit
    row[WooCommerceColumns.NAME] = f"{base_title} {quantity_str} {price_info.currency}".strip()
    
    row[WooCommerceColumns.DESCRIPTION] = ""  # Опционально, можно оставить пустым
    
    # Цена
    row[WooCommerceColumns.REGULAR_PRICE] = str(float(price_info.price))  # Decimal в float, затем в str
    row[WooCommerceColumns.STOCK] = "50"  # По умолчанию
    row[WooCommerceColumns.STOCK_STATUS] = "In stock"
    
    # Атрибуты вариации (конкретные значения)
    if price_info.is_quantity_based:
        row["Attribute 1 name"] = "pa_quantity"
        row["Attribute 1 value"] = f"{int(price_info.quantity)}{price_info.unit}"
        row["meta:quantity"] = str(int(price_info.quantity))
        row["meta:unit"] = price_info.unit
    
    # Attribute 2: currency (если есть разные валюты в продукте)
    # Проверяем, есть ли другие валюты для этой формы (только для цен с quantity/unit)
    prices_with_quantity = [
        p for p in product.prices 
        if p.form == form and p.is_quantity_based
    ]
    currencies = set(p.currency for p in prices_with_quantity)
    if len(currencies) > 1:
        row["Attribute 2 name"] = "pa_currency"
        row["Attribute 2 value"] = price_info.currency
    
    # Изображение
    if product.cover_image_url and product.cover_image_url.strip():
        row[WooCommerceColumns.IMAGES] = _image_identifier_to_public_url(product.cover_image_url)
    else:
        row[WooCommerceColumns.IMAGES] = ""
    
    # Метаданные вариации (quantity/unit уже добавлены выше в атрибутах)
    row["meta:currency"] = price_info.currency
    row["meta:blockchain_id"] = str(product.blockchain_id)
    row["meta:business_id"] = product.business_id  # Для сопоставления с основным продуктом
    row["meta:form"] = form
    
    return row


# ============================================================================
# Вспомогательные функции для работы с mapping
# ============================================================================

def _apply_mapping_to_rows(csv_rows: List[Dict], mapping_data: Dict) -> List[Dict]:
    """
    Применяет mapping данных к строкам CSV для добавления WooCommerce ID.
    
    Алгоритм:
    1. Для каждой строки CSV извлекает SKU (или генерирует из meta:blockchain_id + meta:form)
    2. Ищет mapping по SKU в mappings_by_sku (приоритет 1)
    3. Если не найдено, ищет по business_id в mappings_by_business_id (приоритет 2)
    4. Для вариаций (строки с атрибутами) — ищет variation_id внутри родительского продукта
    5. Если найдено, добавляет ID = woo_id (или variation_id) и обновляет SKU из mapping
    6. Если не найдено, логирует предупреждение (продолжает работу)
    
    Args:
        csv_rows: Список словарей с данными строк CSV
        mapping_data: Словарь с mapping данными (структура из woo_id_mapping.json)
        
    Returns:
        List[Dict]: Обновлённый список строк CSV с добавленными ID и обновлёнными SKU
    """
    if not mapping_data:
        logger.warning("[Export] ⚠️ Mapping данные отсутствуют. Пропускаем применение mapping.")
        return csv_rows
    
    mappings_by_sku = mapping_data.get("mappings_by_sku", {})
    mappings_by_business_id = mapping_data.get("mappings_by_business_id", {})
    mappings_by_variation_id = mapping_data.get("mappings_by_variation_id", {})
    
    if not mappings_by_sku and not mappings_by_business_id:
        logger.warning("[Export] ⚠️ Mapping данные пусты. Пропускаем применение mapping.")
        return csv_rows
    
    # Статистика
    stats_mapped = 0
    stats_mapped_variations = 0
    stats_skipped = 0
    stats_duplicates = 0
    woo_ids_seen = {}  # Для отслеживания дубликатов
    
    updated_rows = []
    
    for row in csv_rows:
        # Создаём копию строки для безопасной модификации
        updated_row = row.copy()
        
        # Извлечение SKU из строки
        sku = updated_row.get(WooCommerceColumns.SKU, "").strip()
        
        # Если SKU отсутствует, попытаться сгенерировать из meta:blockchain_id и meta:form
        if not sku:
            blockchain_id = updated_row.get("meta:blockchain_id", "").strip()
            form = updated_row.get("meta:form", "").strip()
            if blockchain_id and form:
                sku = f"{blockchain_id}_{form}"
                logger.debug(f"[Export] 🔧 Сгенерирован SKU для сопоставления: {sku}")
        
        # Извлечение business_id для fallback поиска
        business_id = updated_row.get("meta:business_id", "").strip()
        
        # Определение, является ли строка вариацией
        # Вариации имеют атрибуты в названии (например, "30g EUR", "100g EUR")
        # или в специальном поле meta:variation_attribute
        name = updated_row.get(WooCommerceColumns.NAME, "")
        variation_attribute = updated_row.get("meta:variation_attribute", "").strip()
        
        # Извлечение атрибута из названия (формат: "Название Xg EUR" или "Название Xg")
        extracted_attribute = None
        if not variation_attribute and name:
            import re
            # Ищем паттерн типа "30g", "50g", "100g", "200g" в конце названия
            attr_match = re.search(r'\b(\d+g)\b', name)
            if attr_match:
                extracted_attribute = attr_match.group(1)
        
        attribute_value = variation_attribute or extracted_attribute
        
        mapping_found = None
        search_method = None
        is_variation = False
        variation_id = None
        
        # Приоритет 1: Поиск по SKU
        if sku and sku in mappings_by_sku:
            mapping_found = mappings_by_sku[sku]
            search_method = "SKU"
        # Приоритет 2: Поиск по business_id
        elif business_id and business_id in mappings_by_business_id:
            mapping_found = mappings_by_business_id[business_id]
            search_method = "business_id"
            
            # Проверяем, является ли это variable продуктом с вариациями
            if mapping_found.get("product_type") == "variable" and attribute_value:
                variations = mapping_found.get("variations", [])
                for var in variations:
                    if var.get("attribute_value") == attribute_value:
                        variation_id = var.get("variation_id")
                        is_variation = True
                        logger.debug(
                            f"[Export] 🔍 Найдена вариация для {business_id}: "
                            f"attribute={attribute_value}, variation_id={variation_id}"
                        )
                        break
        
        if mapping_found:
            # Определяем какой ID использовать
            if is_variation and variation_id:
                woo_id = variation_id
                search_method = f"variation ({attribute_value})"
            else:
                woo_id = mapping_found.get("woo_id")
            
            if woo_id is None:
                logger.warning(
                    f"[Export] ⚠️ Найден mapping для {search_method}={sku or business_id}, "
                    f"но woo_id отсутствует. Пропускаем."
                )
                stats_skipped += 1
                updated_rows.append(updated_row)
                continue
            
            # Проверка на дубликаты WooCommerce ID
            woo_id_str = str(woo_id)
            row_identifier = f"{business_id}_{attribute_value}" if attribute_value else (sku or business_id)
            
            if woo_id_str in woo_ids_seen:
                # Дубликаты для вариаций — это нормально только если это родительский ID
                # Но variation_id должен быть уникальным
                if is_variation:
                    logger.warning(
                        f"[Export] ⚠️ Дубликат variation ID {woo_id_str}: "
                        f"найден для {row_identifier}, "
                        f"ранее использован для {woo_ids_seen[woo_id_str]}"
                    )
                    stats_duplicates += 1
                else:
                    logger.warning(
                        f"[Export] ⚠️ Дубликат WooCommerce ID {woo_id_str}: "
                        f"найден для {search_method}={sku or business_id}, "
                        f"ранее использован для {woo_ids_seen[woo_id_str]}"
                    )
                    stats_duplicates += 1
            else:
                woo_ids_seen[woo_id_str] = row_identifier
            
            # Добавление ID и обновление SKU
            updated_row[WooCommerceColumns.ID] = woo_id_str
            
            # Обновление SKU из mapping (приоритет над генерацией)
            # Для вариаций SKU остаётся пустым (как в WooCommerce)
            if "sku" in mapping_found and not is_variation:
                old_sku = updated_row.get(WooCommerceColumns.SKU, "")
                new_sku = mapping_found["sku"]
                updated_row[WooCommerceColumns.SKU] = new_sku
                if old_sku != new_sku:
                    logger.debug(f"[Export] 📝 SKU из mapping: {old_sku} → {new_sku}")
            
            if is_variation:
                stats_mapped_variations += 1
            else:
                stats_mapped += 1
            
            logger.debug(
                f"[Export] ✅ Mapping применён ({search_method}): "
                f"ID={woo_id_str}, SKU={updated_row.get(WooCommerceColumns.SKU, sku)}"
            )
        else:
            # Mapping не найден
            search_info = f"SKU={sku}" if sku else "SKU отсутствует"
            if business_id:
                search_info += f", business_id={business_id}"
            
            logger.warning(
                f"[Export] ⚠️ Mapping не найден для строки: {search_info}. "
                f"Продукт будет создан как новый в WooCommerce."
            )
            stats_skipped += 1
        
        updated_rows.append(updated_row)
    
    # Логирование статистики
    logger.info(f"[Export] 📊 Статистика применения mapping:")
    logger.info(f"   ✅ Найдено и применено (продукты): {stats_mapped}")
    if stats_mapped_variations > 0:
        logger.info(f"   ✅ Найдено и применено (вариации): {stats_mapped_variations}")
    logger.info(f"   ⚠️ Пропущено (не найдено в mapping): {stats_skipped}")
    if stats_duplicates > 0:
        logger.warning(f"   ⚠️ Дубликаты WooCommerce ID: {stats_duplicates}")
    
    return updated_rows


def _filter_columns(csv_rows: List[Dict], columns: List[str], reuse_woo_id: bool) -> List[Dict]:
    """
    Фильтрует колонки в строках CSV, оставляя только указанные колонки.
    
    Алгоритм:
    1. Если reuse_woo_id=True, гарантирует наличие ID и SKU в списке колонок
    2. Для каждой строки CSV создаёт новый словарь только с указанными колонками
    3. Колонки, отсутствующие в строке, будут иметь значение пустой строки или None
    
    Args:
        csv_rows: Список словарей с данными строк CSV
        columns: Список названий колонок для фильтрации
        reuse_woo_id: Флаг, указывающий, используются ли WooCommerce ID из mapping
        
    Returns:
        List[Dict]: Отфильтрованный список строк CSV только с указанными колонками
    """
    if not columns:
        logger.debug("[Export] Список колонок для фильтрации пуст. Возвращаем все колонки.")
        return csv_rows
    
    # Гарантировать наличие ID и SKU при reuse_woo_id
    filtered_columns = columns.copy()
    if reuse_woo_id:
        # Добавить ID в начало, если отсутствует
        if WooCommerceColumns.ID not in filtered_columns:
            filtered_columns.insert(0, WooCommerceColumns.ID)
            logger.debug(f"[Export] Добавлена колонка {WooCommerceColumns.ID} (требуется для reuse_woo_id)")
        
        # Добавить SKU, если отсутствует (но не в самое начало, после ID)
        if WooCommerceColumns.SKU not in filtered_columns:
            # Вставить после ID, если ID есть, иначе в начало
            try:
                id_index = filtered_columns.index(WooCommerceColumns.ID)
                filtered_columns.insert(id_index + 1, WooCommerceColumns.SKU)
            except ValueError:
                filtered_columns.insert(0, WooCommerceColumns.SKU)
            logger.debug(f"[Export] Добавлена колонка {WooCommerceColumns.SKU} (требуется для reuse_woo_id)")
    
    # Определить доступные колонки из всех строк
    available_columns = set()
    for row in csv_rows:
        available_columns.update(row.keys())
    
    # Проверить наличие указанных колонок в данных
    missing_columns = [col for col in filtered_columns if col not in available_columns]
    if missing_columns:
        logger.warning(
            f"[Export] ⚠️ Следующие колонки из --columns отсутствуют в данных и будут исключены: {', '.join(missing_columns)}"
        )
        # Исключить отсутствующие колонки из фильтрации
        filtered_columns = [col for col in filtered_columns if col in available_columns]
    
    # Подсчитать добавленные колонки для reuse_woo_id
    added_for_reuse = 0
    if reuse_woo_id:
        if WooCommerceColumns.ID not in columns and WooCommerceColumns.ID in filtered_columns:
            added_for_reuse += 1
        if WooCommerceColumns.SKU not in columns and WooCommerceColumns.SKU in filtered_columns:
            added_for_reuse += 1
    
    logger.info(
        f"[Export] Фильтрация колонок: оставляем {len(filtered_columns)} из {len(available_columns)} доступных "
        f"(запрошено: {len(columns)}, исключено отсутствующих: {len(missing_columns)}, "
        f"добавлено для reuse_woo_id: {added_for_reuse})"
    )
    
    # Фильтрация строк
    filtered_rows = []
    for row in csv_rows:
        filtered_row = {}
        for col in filtered_columns:
            # Взять значение из строки, если существует, иначе пустая строка
            filtered_row[col] = row.get(col, "")
        filtered_rows.append(filtered_row)
    
    logger.info(f"[Export] ✅ Отфильтровано {len(filtered_rows)} строк с {len(filtered_columns)} колонками")
    
    return filtered_rows


# ============================================================================
# Главная функция экспорта
# ============================================================================

def export_to_woocommerce_csv(
    products: List[Product],
    language: str,
    output_path: str,
    html_adapter: HTMLFormatAdapter,
    columns: List[str] = None,
    mapping_data: Dict = None,
    reuse_woo_id: bool = False
) -> str:
    """
    Экспортирует продукты в CSV файл для импорта в WooCommerce.
    
    Алгоритм:
    1. Для каждого продукта и каждой формы определяет тип (simple/variable)
    2. Генерирует CSV строки (simple, variable, или variable + variations)
    3. Валидирует уникальность SKU
    4. Применяет mapping для добавления WooCommerce ID (если reuse_woo_id=True)
    5. Фильтрует колонки (если columns указан)
    6. Записывает в CSV файл с правильным порядком колонок
    
    Args:
        products: Список продуктов для экспорта
        language: Язык локализации (например, "ru", "en")
        output_path: Путь к выходному CSV файлу
        html_adapter: HTML адаптер для форматирования описаний
        columns: Список колонок для экспорта (None = все колонки)
        mapping_data: Данные mapping для reuse WooCommerce ID (из woo_id_mapping.json)
        reuse_woo_id: Флаг использования WooCommerce ID из mapping
        
    Returns:
        str: Путь к созданному CSV файлу
        
    Raises:
        ValueError: Если список продуктов пуст
        IOError: Если не удалось создать директорию или записать файл
    """
    import csv
    import os
    from pathlib import Path
    
    if not products:
        raise ValueError("Список продуктов для экспорта пуст")
    
    logger.info(f"[Export] Начало экспорта {len(products)} продуктов в CSV")
    
    csv_rows = []
    
    # Для каждого продукта:
    for product in products:
        # Проверка наличия форм
        if not product.forms:
            logger.warning(
                f"[Export] Продукт {product.business_id} не имеет форм. Пропускаем."
            )
            continue
        
        # Для каждой формы:
        for form in product.forms:
            try:
                # Определить тип продукта
                product_type = _determine_product_type(product, form)
                
                if product_type == "variable":
                    # Добавить родительский продукт (variable)
                    variable_row = generate_variable_product_row(
                        product, form, language, html_adapter
                    )
                    csv_rows.append(variable_row)
                    
                    # Для каждой цены с quantity/unit добавить вариацию
                    prices_with_quantity = [
                        p for p in product.prices 
                        if p.form == form and p.is_quantity_based
                    ]
                    
                    if not prices_with_quantity:
                        logger.warning(
                            f"[Export] Variable продукт {product.business_id} (форма: {form}) "
                            f"не имеет цен с quantity/unit. Родительский продукт создан без вариаций."
                        )
                    else:
                        for price_info in prices_with_quantity:
                            try:
                                variation_row = generate_variation_row(
                                    product, form, price_info, language, html_adapter
                                )
                                csv_rows.append(variation_row)
                            except ValueError as e:
                                logger.error(
                                    f"[Export] Ошибка при создании вариации для продукта "
                                    f"{product.business_id} (форма: {form}): {e}"
                                )
                                # Продолжаем обработку других вариаций
                                continue
                else:
                    # Добавить simple продукт
                    simple_row = generate_simple_product_row(
                        product, form, language, html_adapter
                    )
                    csv_rows.append(simple_row)
                    
            except Exception as e:
                logger.error(
                    f"[Export] Ошибка при обработке продукта {product.business_id} "
                    f"(форма: {form}): {e}"
                )
                # Продолжаем обработку других продуктов
                continue
    
    if not csv_rows:
        raise ValueError("Не удалось сгенерировать ни одной строки CSV")
    
    logger.info(f"[Export] Сгенерировано {len(csv_rows)} строк CSV")
    
    # Валидация SKU
    csv_rows = validate_sku_uniqueness(csv_rows)
    logger.info(f"[Export] Валидация SKU завершена. Осталось {len(csv_rows)} строк")
    
    # Применение mapping для добавления WooCommerce ID (если включён reuse_woo_id)
    if reuse_woo_id and mapping_data:
        logger.info("[Export] Применение mapping для добавления WooCommerce ID...")
        csv_rows = _apply_mapping_to_rows(csv_rows, mapping_data)
    elif reuse_woo_id and not mapping_data:
        # Если reuse_woo_id=True, но mapping не загружен, добавляем пустую колонку ID
        # чтобы она была доступна для фильтрации
        logger.warning(
            "[Export] ⚠️ reuse_woo_id включён, но mapping-файл не загружен. "
            "Колонка ID будет добавлена пустой."
        )
        for row in csv_rows:
            if WooCommerceColumns.ID not in row:
                row[WooCommerceColumns.ID] = ""
    
    # Фильтрация колонок (если указаны)
    if columns:
        logger.info(f"[Export] Фильтрация колонок: оставляем только {len(columns)} указанных колонок")
        csv_rows = _filter_columns(csv_rows, columns, reuse_woo_id)
    
    # Запись в CSV файл
    # Создать директорию если её нет
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Определить fieldnames для CSV
    if columns:
        # Если указаны конкретные колонки, использовать их (уже отфильтрованы в _filter_columns)
        # _filter_columns уже гарантировала наличие ID и SKU при reuse_woo_id
        all_columns_from_rows = set()
        for row in csv_rows:
            all_columns_from_rows.update(row.keys())
        
        # Использовать колонки, которые реально присутствуют в строках
        # Это важно, если какие-то колонки из списка отсутствуют в данных
        fieldnames = [col for col in columns if col in all_columns_from_rows]
        
        # Гарантировать наличие ID и SKU при reuse_woo_id (на случай, если они были удалены)
        if reuse_woo_id:
            if WooCommerceColumns.ID in all_columns_from_rows and WooCommerceColumns.ID not in fieldnames:
                fieldnames.insert(0, WooCommerceColumns.ID)
            if WooCommerceColumns.SKU in all_columns_from_rows and WooCommerceColumns.SKU not in fieldnames:
                # Вставить после ID, если ID есть
                try:
                    id_index = fieldnames.index(WooCommerceColumns.ID)
                    fieldnames.insert(id_index + 1, WooCommerceColumns.SKU)
                except ValueError:
                    fieldnames.insert(0, WooCommerceColumns.SKU)
    else:
        # Если колонки не указаны, использовать стандартную логику
        # Собрать все уникальные колонки из всех строк
        all_columns = set()
        for row in csv_rows:
            all_columns.update(row.keys())
        
        # Определить порядок колонок:
        # 1. Стандартные колонки WooCommerce (в логическом порядке)
        # 2. Другие колонки (атрибуты и т.д.)
        # 3. Метаданные (meta:*)
        standard_columns = WooCommerceColumns.get_standard_order()
        
        # Атрибуты (Attribute 1, Attribute 2, ...)
        attribute_columns = sorted([
            c for c in all_columns 
            if c.startswith("Attribute ") and not c.startswith("meta:")
        ])
        
        # Метаданные
        meta_columns = sorted([
            c for c in all_columns 
            if c.startswith("meta:")
        ])
        
        # Остальные колонки (если есть)
        other_columns = sorted([
            c for c in all_columns 
            if c not in standard_columns 
            and c not in attribute_columns 
            and c not in meta_columns
        ])
        
        # Финальный порядок колонок
        fieldnames = (
            [c for c in standard_columns if c in all_columns] +
            attribute_columns +
            other_columns +
            meta_columns
        )
        
        # Гарантировать наличие ID и SKU при reuse_woo_id (даже если они отсутствуют в стандартном порядке)
        if reuse_woo_id:
            if WooCommerceColumns.ID in all_columns and WooCommerceColumns.ID not in fieldnames:
                fieldnames.insert(0, WooCommerceColumns.ID)
            if WooCommerceColumns.SKU in all_columns and WooCommerceColumns.SKU not in fieldnames:
                try:
                    id_index = fieldnames.index(WooCommerceColumns.ID)
                    fieldnames.insert(id_index + 1, WooCommerceColumns.SKU)
                except ValueError:
                    fieldnames.insert(0, WooCommerceColumns.SKU)
    
    # Записать CSV файл
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(csv_rows)
        
        logger.info(f"[Export] CSV файл успешно создан: {output_path}")
        logger.info(f"[Export] Всего строк: {len(csv_rows)}, колонок: {len(fieldnames)}")
        
        # Дополнительная информация о колонках
        if columns:
            logger.info(f"[Export] 📋 Использованы колонки: {', '.join(fieldnames[:10])}{'...' if len(fieldnames) > 10 else ''}")
        if reuse_woo_id:
            id_count = sum(1 for row in csv_rows if row.get(WooCommerceColumns.ID))
            logger.info(f"[Export] 🆔 Продуктов с WooCommerce ID: {id_count} из {len(csv_rows)}")
        
    except IOError as e:
        logger.error(f"[Export] Ошибка при записи CSV файла {output_path}: {e}")
        raise
    
    return output_path

