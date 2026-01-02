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
    
    Формат: {blockchain_id}_{form}_{weight}{weight_unit}_{currency}
            или {blockchain_id}_{form}_{volume}{volume_unit}_{currency}
    Пример: 123_dried_100g_EUR (весовой продукт)
    Пример: 456_tincture_50ml_USD (объемный продукт)
    
    Args:
        product: Продукт
        form: Форма продукта
        price_info: Информация о цене (должна иметь weight или volume)
        
    Returns:
        str: SKU вариации
        
    Raises:
        ValueError: Если цена не имеет weight или volume
    """
    # Получаем базовый SKU продукта
    base_sku = generate_product_sku(product, form)
    
    # Определяем количество и единицу измерения
    if price_info.is_weight_based:
        quantity = int(price_info.weight)  # Конвертируем Decimal в int для SKU
        unit = price_info.weight_unit
        quantity_unit = f"{quantity}{unit}"
    elif price_info.is_volume_based:
        quantity = int(price_info.volume)  # Конвертируем Decimal в int для SKU
        unit = price_info.volume_unit
        quantity_unit = f"{quantity}{unit}"
    else:
        # Простые цены не поддерживаются для вариаций WooCommerce
        raise ValueError(
            f"Цена для продукта {product.business_id} (форма: {form}) не имеет weight или volume. "
            f"Вариации WooCommerce требуют конкретные атрибуты (вес/объем)."
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
        sku = row.get('SKU') or row.get('Variation SKU', '')
        
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
            if 'SKU' in row:
                row['SKU'] = new_sku
            elif 'Variation SKU' in row:
                row['Variation SKU'] = new_sku
            
            # Обновляем Parent если он ссылается на дубликат
            if 'Parent' in row and row['Parent'] == sku:
                row['Parent'] = new_sku
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
    # Проверить наличие weight/volume
    has_weight_volume = any(
        p.is_weight_based or p.is_volume_based 
        for p in prices_for_form
    )
    
    # Если все цены без weight/volume → simple
    if not has_weight_volume:
        return "simple"
    
    # Если есть хотя бы одна цена с weight/volume и несколько цен → variable
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
    
    # Получить все цены для формы с weight/volume
    prices_with_weight_volume = [
        p for p in product.prices 
        if p.form == form and (p.is_weight_based or p.is_volume_based)
    ]
    
    if not prices_with_weight_volume:
        return attributes
    
    # Собрать уникальные веса/объемы
    weight_volume_values = set()
    for price in prices_with_weight_volume:
        if price.is_weight_based:
            quantity = int(price.weight)  # Decimal в int для SKU
            weight_volume_values.add(f"{quantity}{price.weight_unit}")
        elif price.is_volume_based:
            quantity = int(price.volume)  # Decimal в int для SKU
            weight_volume_values.add(f"{quantity}{price.volume_unit}")
    
    # Собрать уникальные валюты
    currencies = set(p.currency for p in prices_with_weight_volume)
    
    # Сформировать атрибуты
    if weight_volume_values:
        # Attribute 1: weight/volume
        # Определяем тип (weight или volume) по первой цене
        first_price = prices_with_weight_volume[0]
        if first_price.is_weight_based:
            attributes["Attribute 1 name"] = "pa_weight"
        else:
            attributes["Attribute 1 name"] = "pa_volume"
        
        # Значения через |
        attributes["Attribute 1 value(s)"] = "|".join(sorted(weight_volume_values))
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
    row["Type"] = "simple"
    row["SKU"] = generate_product_sku(product, form)
    row["Name"] = get_localized_title(product, language, html_adapter)
    row["Description"] = format_product_description_html(product, language, html_adapter)
    row["Short description"] = ""  # Опционально, можно оставить пустым
    
    # Изображение (CID, можно конвертировать в URL позже)
    if product.cover_image_url and product.cover_image_url.strip():
        row["Images"] = _image_identifier_to_public_url(product.cover_image_url)
    else:
        row["Images"] = ""
    
    # Статус
    row["Status"] = "Published" if product.status == 1 else "Draft"
    row["Stock status"] = "In stock"
    row["Stock"] = "50"  # По умолчанию
    
    # Цена (первая цена для формы или единственная)
    prices_for_form = [p for p in product.prices if p.form == form]
    if prices_for_form:
        first_price = prices_for_form[0]
        row["Price"] = str(float(first_price.price))  # Decimal в float, затем в str
    else:
        row["Price"] = ""
        logger.warning(
            f"[Export] Продукт {product.business_id} (форма: {form}) не имеет цен. "
            f"Цена не установлена."
        )
    
    # Категории через запятую
    if product.categories:
        row["Categories"] = ",".join(product.categories)
    else:
        row["Categories"] = ""
    
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
    row["Type"] = "variable"
    row["SKU"] = generate_product_sku(product, form)
    row["Name"] = get_localized_title(product, language, html_adapter)
    row["Description"] = format_product_description_html(product, language, html_adapter)
    row["Short description"] = ""  # Опционально
    
    # Изображение
    if product.cover_image_url and product.cover_image_url.strip():
        row["Images"] = _image_identifier_to_public_url(product.cover_image_url)
    else:
        row["Images"] = ""
    
    # Статус
    row["Status"] = "Published" if product.status == 1 else "Draft"
    row["Stock status"] = "In stock"
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
        price_info: Информация о цене (должна иметь weight или volume)
        language: Язык локализации
        html_adapter: HTML адаптер
        
    Returns:
        Dict[str, str]: Словарь с колонками CSV (включая meta:*)
        
    Raises:
        ValueError: Если price_info не имеет weight или volume
    """
    if not price_info.is_weight_based and not price_info.is_volume_based:
        raise ValueError(
            f"Вариация требует price_info с weight или volume. "
            f"Продукт: {product.business_id}, форма: {form}"
        )
    
    row = {}
    
    # Основные поля
    row["Type"] = "variation"
    row["Parent"] = generate_product_sku(product, form)
    
    # SKU вариации
    variation_sku = generate_variation_sku(product, form, price_info)
    row["SKU"] = variation_sku
    row["Variation SKU"] = variation_sku
    
    # Название вариации: локализованное название + вес/объем + валюта
    base_title = get_localized_title(product, language, html_adapter)
    if price_info.is_weight_based:
        quantity_str = f"{int(price_info.weight)}{price_info.weight_unit}"
    else:
        quantity_str = f"{int(price_info.volume)}{price_info.volume_unit}"
    row["Name"] = f"{base_title} {quantity_str} {price_info.currency}"
    
    row["Description"] = ""  # Опционально, можно оставить пустым
    
    # Цена
    row["Price"] = str(float(price_info.price))  # Decimal в float, затем в str
    row["Stock"] = "50"  # По умолчанию
    row["Stock status"] = "In stock"
    
    # Атрибуты вариации (конкретные значения)
    if price_info.is_weight_based:
        row["Attribute 1 name"] = "pa_weight"
        row["Attribute 1 value"] = f"{int(price_info.weight)}{price_info.weight_unit}"
    else:
        row["Attribute 1 name"] = "pa_volume"
        row["Attribute 1 value"] = f"{int(price_info.volume)}{price_info.volume_unit}"
    
    # Attribute 2: currency (если есть разные валюты в продукте)
    # Проверяем, есть ли другие валюты для этой формы (только для цен с weight/volume)
    prices_with_weight_volume = [
        p for p in product.prices 
        if p.form == form and (p.is_weight_based or p.is_volume_based)
    ]
    currencies = set(p.currency for p in prices_with_weight_volume)
    if len(currencies) > 1:
        row["Attribute 2 name"] = "pa_currency"
        row["Attribute 2 value"] = price_info.currency
    
    # Изображение
    if product.cover_image_url and product.cover_image_url.strip():
        row["Images"] = _image_identifier_to_public_url(product.cover_image_url)
    else:
        row["Images"] = ""
    
    # Метаданные вариации
    if price_info.is_weight_based:
        row["meta:weight"] = str(int(price_info.weight))
        row["meta:weight_unit"] = price_info.weight_unit
    else:
        row["meta:volume"] = str(int(price_info.volume))
        row["meta:volume_unit"] = price_info.volume_unit
    
    row["meta:currency"] = price_info.currency
    row["meta:blockchain_id"] = str(product.blockchain_id)
    row["meta:form"] = form
    
    return row


# ============================================================================
# Главная функция экспорта
# ============================================================================

def export_to_woocommerce_csv(
    products: List[Product],
    language: str,
    output_path: str,
    html_adapter: HTMLFormatAdapter
) -> str:
    """
    Экспортирует продукты в CSV файл для импорта в WooCommerce.
    
    Алгоритм:
    1. Для каждого продукта и каждой формы определяет тип (simple/variable)
    2. Генерирует CSV строки (simple, variable, или variable + variations)
    3. Валидирует уникальность SKU
    4. Записывает в CSV файл с правильным порядком колонок
    
    Args:
        products: Список продуктов для экспорта
        language: Язык локализации (например, "ru", "en")
        output_path: Путь к выходному CSV файлу
        html_adapter: HTML адаптер для форматирования описаний
        
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
                    
                    # Для каждой цены с weight/volume добавить вариацию
                    prices_with_weight_volume = [
                        p for p in product.prices 
                        if p.form == form and (p.is_weight_based or p.is_volume_based)
                    ]
                    
                    if not prices_with_weight_volume:
                        logger.warning(
                            f"[Export] Variable продукт {product.business_id} (форма: {form}) "
                            f"не имеет цен с weight/volume. Родительский продукт создан без вариаций."
                        )
                    else:
                        for price_info in prices_with_weight_volume:
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
    
    # Запись в CSV файл
    # Создать директорию если её нет
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Собрать все уникальные колонки из всех строк
    all_columns = set()
    for row in csv_rows:
        all_columns.update(row.keys())
    
    # Определить порядок колонок:
    # 1. Стандартные колонки WooCommerce (в логическом порядке)
    # 2. Другие колонки (атрибуты и т.д.)
    # 3. Метаданные (meta:*)
    standard_columns = [
        "Type", "Parent", "SKU", "Variation SKU", "Name", "Description", 
        "Short description", "Images", "Status", "Stock status", "Stock", 
        "Price", "Categories"
    ]
    
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
    
    # Записать CSV файл
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(csv_rows)
        
        logger.info(f"[Export] CSV файл успешно создан: {output_path}")
        logger.info(f"[Export] Всего строк: {len(csv_rows)}, колонок: {len(fieldnames)}")
        
    except IOError as e:
        logger.error(f"[Export] Ошибка при записи CSV файла {output_path}: {e}")
        raise
    
    return output_path

