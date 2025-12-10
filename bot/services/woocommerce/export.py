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
from typing import List, Dict
from model.product import Product, PriceInfo
from services.common.localization import Localization
from services.woocommerce.html_format_adapter import HTMLFormatAdapter

logger = logging.getLogger(__name__)


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
                    "image_url": product.cover_image_url,
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

