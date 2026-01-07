#!/usr/bin/env python3
"""
Генерация маппинга WooCommerce ID ↔ business_id для инкрементальных экспортов.

ФОРМАТ МАППИНГА (JSON):
========================

Структура:
{
  "version": "1.0",                    # Версия формата (string)
  "generated_at": "2026-01-02T12:00:00Z",  # ISO 8601 timestamp (string)
  "source_file": "wc-product-export-*.csv",  # Имя исходного CSV (string)
  "mappings_by_business_id": {         # Объект с ключами = business_id
    "business_id": {
      "woo_id": 194,                   # WooCommerce ID (integer, обязательное)
      "sku": "35_dried",               # SKU продукта (string, обязательное)
      "blockchain_id": 35,             # Blockchain ID (integer, опциональное)
      "component_ids": 1,             # ID компонента (integer, опциональное)
      "form": "dried",                 # Форма продукта (string, опциональное)
      "name": "Название",              # Название продукта (string, опциональное)
      "regular_price": null            # Цена (string|null, опциональное)
    }
  },
  "mappings_by_sku": {                 # Объект с ключами = SKU
    "35_dried": {
      "woo_id": 194,                   # WooCommerce ID (integer, обязательное)
      "business_id": "amanita1",       # Business ID (string, обязательное)
      "blockchain_id": 35              # Blockchain ID (integer, опциональное)
    }
  },
  "statistics": {
    "total_products": 17,              # Всего продуктов в CSV (integer)
    "mapped": 17,                      # Успешно сопоставлено (integer)
    "skipped": 0,                      # Пропущено (integer)
    "duplicates": 0                    # Дубликатов (integer)
  }
}

ОБЯЗАТЕЛЬНЫЕ ПОЛЯ:
- version: версия формата (string)
- generated_at: ISO 8601 timestamp (string)
- source_file: имя исходного CSV (string)
- mappings_by_business_id: объект с маппингами по business_id (обязательное)
- mappings_by_sku: объект с маппингами по SKU (обязательное)
- statistics: статистика обработки (обязательное)

В mappings_by_business_id каждая запись должна иметь:
- woo_id (integer, обязательное)
- sku (string, обязательное)
- остальные поля опциональные

В mappings_by_sku каждая запись должна иметь:
- woo_id (integer, обязательное)
- business_id (string, обязательное)
- blockchain_id (integer, опциональное)

ПРЕИМУЩЕСТВА ФОРМАТА:
- Быстрый поиск по business_id (O(1))
- Быстрый поиск по SKU (O(1))
- Удобно для экспорт-скрипта (прямой доступ по ключу)
- Меньше памяти при больших объёмах данных

ИСПОЛЬЗОВАНИЕ:
- Поиск по business_id: mapping["mappings_by_business_id"][business_id]
- Поиск по SKU: mapping["mappings_by_sku"][sku]
- Проверка статистики: mapping["statistics"]

См. также: bot/docs/analysis/tasks/mapping-format-specification.md
"""

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Функции определения типа продукта
# ============================================================================

def identify_product_type(row: Dict) -> str:
    """
    Определяет тип строки CSV: 'variable', 'variation', 'simple', 'unknown'.
    
    Логика:
    1. Если есть колонка Type — использовать её напрямую
    2. Иначе определять по косвенным признакам:
       - variable: есть ID, SKU, business_id, нет цены, атрибуты = список
       - variation: есть ID, нет SKU, нет business_id, есть цена, атрибут = одно значение
       - simple: есть ID, SKU, business_id, есть цена
       - unknown: не подходит ни под один тип
    
    Args:
        row: Словарь с данными строки CSV (ключи = названия колонок)
        
    Returns:
        str: Тип продукта ('variable', 'variation', 'simple', 'unknown')
    """
    # Приоритет 1: Явная колонка Type
    type_value = row.get('Type', '').strip().lower()
    if type_value in ('variable', 'variation', 'simple'):
        return type_value
    
    # Приоритет 2: Косвенные признаки
    id_value = row.get('ID', '').strip()
    sku_value = row.get('SKU', '').strip()
    business_id = row.get('Meta: business_id', '').strip()
    price = row.get('Regular price', '').strip()
    attr_values = row.get('Attribute 1 value(s)', '').strip()
    
    if not id_value:
        return 'unknown'
    
    # Вариация: нет SKU, нет business_id, есть цена
    if not sku_value and not business_id and price:
        return 'variation'
    
    # Variable: есть SKU, есть business_id, нет цены, атрибуты = список
    if sku_value and business_id and not price:
        if ',' in attr_values:  # Список значений через запятую
            return 'variable'
    
    # Simple: есть SKU, business_id и цена
    if sku_value and business_id and price:
        return 'simple'
    
    # Если есть SKU и business_id, но нет атрибутов-списка — simple по умолчанию
    if sku_value and business_id:
        return 'simple'
    
    return 'unknown'


def link_variations_to_parent(rows: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Связывает вариации с родительскими продуктами.
    
    ⚠️ ВАЖНО: Вариации идут НЕ сразу после родителя, а ВСЕ ВМЕСТЕ после всех родителей!
    
    Алгоритм:
    1. Собрать всех родителей в порядке появления
    2. Для каждого родителя подсчитать ожидаемое количество вариаций
    3. Собрать все вариации в порядке появления
    4. Распределить вариации по родителям в порядке очереди
    5. Валидировать: attribute_value вариации должен входить в список атрибутов родителя
    
    Args:
        rows: Список словарей с данными строк CSV
        
    Returns:
        Dict[str, List[Dict]]: {parent_business_id: [variation_rows]}
    """
    # Шаг 1: Собрать родителей
    parents = []  # [(business_id, woo_id, expected_count, attribute_values_set)]
    for row in rows:
        if identify_product_type(row) == 'variable':
            business_id = row.get('Meta: business_id', '').strip()
            woo_id = row.get('ID', '').strip()
            attr_values_str = row.get('Attribute 1 value(s)', '').strip()
            # Парсим атрибуты: "30g, 50g, 100g" → {"30g", "50g", "100g"}
            attr_values = set(v.strip() for v in attr_values_str.split(',') if v.strip())
            expected_count = len(attr_values)
            parents.append((business_id, woo_id, expected_count, attr_values))
            logger.info(f"📦 Родитель: {business_id} (ID={woo_id}), ожидаемых вариаций: {expected_count}")
    
    # Шаг 2: Собрать вариации
    variations = []
    for row in rows:
        if identify_product_type(row) == 'variation':
            variations.append(row)
    
    logger.info(f"🔢 Всего родителей: {len(parents)}, всего вариаций: {len(variations)}")
    
    # Шаг 3: Распределить вариации по родителям
    result = {business_id: [] for business_id, _, _, _ in parents}
    variation_index = 0
    
    for business_id, woo_id, expected_count, attr_values in parents:
        assigned = 0
        while assigned < expected_count and variation_index < len(variations):
            var_row = variations[variation_index]
            var_attr = var_row.get('Attribute 1 value(s)', '').strip()
            
            # Валидация: атрибут вариации должен входить в атрибуты родителя
            if var_attr in attr_values:
                result[business_id].append(var_row)
                assigned += 1
                logger.debug(f"  ✅ Вариация {var_row.get('ID')} ({var_attr}) → {business_id}")
            else:
                logger.warning(
                    f"  ⚠️ Вариация {var_row.get('ID')} ({var_attr}) не соответствует "
                    f"атрибутам родителя {business_id}: {attr_values}"
                )
            variation_index += 1
        
        if assigned < expected_count:
            logger.warning(
                f"⚠️ Родитель {business_id}: ожидалось {expected_count} вариаций, "
                f"найдено {assigned}"
            )
        else:
            logger.info(f"  ✅ Родитель {business_id}: присвоено {assigned} вариаций")
    
    # Проверка на неприсвоенные вариации
    if variation_index < len(variations):
        logger.warning(
            f"⚠️ {len(variations) - variation_index} вариаций не присвоены ни одному родителю"
        )
    
    return result


# ============================================================================
# Функции чтения и валидации CSV
# ============================================================================

def read_woo_export(csv_path: Path) -> Tuple[List[Dict], List[str]]:
    """
    Читает и парсит WooCommerce экспорт CSV файл.
    
    Функция выполняет:
    1. Чтение CSV через csv.DictReader с обработкой BOM (utf-8-sig)
    2. Нормализацию названий колонок (удаление пробелов)
    3. Валидацию обязательных полей (ID, SKU, Meta: business_id)
    4. Логирование пропусков и ошибок
    5. Возврат списка словарей с данными и списка ошибок
    
    Обработка BOM:
    - Использует encoding='utf-8-sig' для автоматического удаления BOM
    - Это решает проблему, когда первая колонка читается как '\\ufeffID' вместо 'ID'
    
    Нормализация колонок:
    - Удаляет ведущие и замыкающие пробелы из названий колонок
    - Улучшает устойчивость к разным форматам CSV
    
    Args:
        csv_path: Путь к CSV файлу экспорта WooCommerce
        
    Returns:
        Tuple[List[Dict], List[str]]: 
        - Список словарей с данными продуктов (каждый словарь = одна строка CSV)
        - Список ошибок валидации (пустые строки для пропущенных строк)
        
    Raises:
        FileNotFoundError: Если файл не найден
        IOError: Если не удалось прочитать файл
    """
    logger.info(f"📖 Чтение WooCommerce экспорта: {csv_path}")
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Файл не найден: {csv_path}")
    
    rows: List[Dict] = []
    errors: List[str] = []
    
    try:
        # Используем utf-8-sig для автоматической обработки BOM (Byte Order Mark)
        # Это решает проблему, когда WooCommerce экспортирует CSV с BOM для Excel
        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            
            # Проверка наличия заголовков
            if not reader.fieldnames:
                raise ValueError("CSV файл не содержит заголовков")
            
            # Нормализация названий колонок (убрать пробелы)
            reader.fieldnames = [col.strip() for col in reader.fieldnames]
            
            logger.info(f"✅ Заголовки CSV: {len(reader.fieldnames)} колонок")
            logger.debug(f"   Колонки: {', '.join(reader.fieldnames)}")
            logger.debug(f"   Первая колонка (repr): {repr(reader.fieldnames[0]) if reader.fieldnames else 'None'}")
            
            # Проверка наличия обязательных колонок
            required_columns = ['ID', 'SKU', 'Meta: business_id']
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                # Дополнительная диагностика
                logger.error(f"Доступные колонки: {reader.fieldnames}")
                raise ValueError(f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}")
            
            # Обработка строк
            row_num = 1  # Счётчик строк (начинается с 1, т.к. строка 0 = заголовки)
            for row in reader:
                row_num += 1
                
                # Определяем тип строки для адаптивной валидации
                row_type = identify_product_type(row)
                
                # Валидация обязательных полей
                validation_errors = []
                
                # Проверка ID (обязательно для всех типов)
                id_value = row.get('ID', '').strip()
                if not id_value:
                    validation_errors.append(f"Строка {row_num}: отсутствует обязательное поле 'ID'")
                else:
                    try:
                        int(id_value)  # Проверка, что ID - число
                    except ValueError:
                        validation_errors.append(f"Строка {row_num}: поле 'ID' должно быть числом, получено: '{id_value}'")
                
                # Для вариаций SKU и business_id НЕ обязательны
                if row_type != 'variation':
                    # Проверка SKU (только для не-вариаций)
                    sku_value = row.get('SKU', '').strip()
                    if not sku_value:
                        validation_errors.append(f"Строка {row_num}: отсутствует обязательное поле 'SKU'")
                    
                    # Проверка Meta: business_id (только для не-вариаций)
                    business_id_value = row.get('Meta: business_id', '').strip()
                    if not business_id_value:
                        validation_errors.append(f"Строка {row_num}: отсутствует обязательное поле 'Meta: business_id'")
                else:
                    logger.debug(f"Строка {row_num}: вариация (ID={id_value}), SKU и business_id не требуются")
                
                # Если есть ошибки валидации, логируем и пропускаем строку
                if validation_errors:
                    for error in validation_errors:
                        logger.warning(f"⚠️ {error}")
                        errors.append(error)
                    continue
                
                # Строка прошла валидацию, добавляем в результат
                rows.append(row)
                logger.debug(f"Строка {row_num}: тип={row_type}, ID={id_value}")
                logger.debug(f"✅ Строка {row_num}: ID={id_value}, SKU={sku_value}, business_id={business_id_value}")
            
            logger.info(f"✅ Обработано строк: {len(rows)} успешно, {len(errors)} с ошибками")
            
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при чтении CSV файла: {e}")
        raise IOError(f"Не удалось прочитать CSV файл: {e}")
    
    return rows, errors


def validate_woo_row(row: Dict) -> Tuple[bool, List[str]]:
    """
    Валидирует строку WooCommerce экспорта.
    
    Проверяет:
    - Наличие обязательных полей (ID, SKU, Meta: business_id)
    - Типы данных (ID — число, SKU — строка)
    - Корректность значений
    
    Args:
        row: Словарь с данными строки CSV (ключи = названия колонок)
        
    Returns:
        Tuple[bool, List[str]]:
        - is_valid: True если строка валидна, False если есть ошибки
        - errors: Список строк с описанием ошибок (пустой если is_valid=True)
    """
    errors: List[str] = []
    
    # Проверка ID
    id_value = row.get('ID', '').strip()
    if not id_value:
        errors.append("Отсутствует обязательное поле 'ID'")
    else:
        try:
            id_int = int(id_value)
            if id_int <= 0:
                errors.append(f"Поле 'ID' должно быть положительным числом, получено: {id_int}")
        except ValueError:
            errors.append(f"Поле 'ID' должно быть числом, получено: '{id_value}'")
    
    # Проверка SKU
    sku_value = row.get('SKU', '').strip()
    if not sku_value:
        errors.append("Отсутствует обязательное поле 'SKU'")
    elif not isinstance(sku_value, str):
        errors.append(f"Поле 'SKU' должно быть строкой, получено: {type(sku_value).__name__}")
    
    # Проверка Meta: business_id
    business_id_value = row.get('Meta: business_id', '').strip()
    if not business_id_value:
        errors.append("Отсутствует обязательное поле 'Meta: business_id'")
    elif not isinstance(business_id_value, str):
        errors.append(f"Поле 'Meta: business_id' должно быть строкой, получено: {type(business_id_value).__name__}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def check_local_product_exists(business_id: str, products_dir: Path) -> bool:
    """
    Проверяет существование локального продукта по business_id.
    
    Проверяет наличие файла: products_dir / business_id / {business_id}.json
    
    Args:
        business_id: Business ID продукта
        products_dir: Путь к директории с продуктами (например, data/sellers/iveta/products)
        
    Returns:
        bool: True если продукт существует локально, False если нет
    """
    if not business_id or not business_id.strip():
        return False
    
    product_dir = products_dir / business_id.strip()
    product_json = product_dir / f"{business_id.strip()}.json"
    
    exists = product_json.exists() and product_json.is_file()
    
    if exists:
        logger.debug(f"✅ Локальный продукт найден: {product_json}")
    else:
        logger.debug(f"⚠️ Локальный продукт не найден: {product_json}")
    
    return exists


def collect_statistics(
    rows: List[Dict],
    local_checks: Dict[str, bool]
) -> Dict:
    """
    Собирает статистику обработки продуктов.
    
    Подсчитывает:
    - total_products: всего продуктов в CSV
    - mapped: успешно сопоставлено (есть в CSV и локально)
    - skipped: пропущено (отсутствуют обязательные поля или нет локально)
    - duplicates: дубликатов ID/SKU
    
    Args:
        rows: Список словарей с данными продуктов из CSV
        local_checks: Словарь {business_id: exists} с результатами проверки локальных продуктов
        
    Returns:
        Dict: Словарь со статистикой:
        {
            "total_products": int,
            "mapped": int,
            "skipped": int,
            "duplicates": int
        }
    """
    total_products = len(rows)
    
    # Подсчёт дубликатов ID и SKU
    ids: List[int] = []
    skus: List[str] = []
    duplicates_count = 0
    
    for row in rows:
        # Сбор ID
        id_value = row.get('ID', '').strip()
        if id_value:
            try:
                ids.append(int(id_value))
            except ValueError:
                pass
        
        # Сбор SKU
        sku_value = row.get('SKU', '').strip()
        if sku_value:
            skus.append(sku_value)
    
    # Подсчёт дубликатов ID
    id_counter = Counter(ids)
    id_duplicates = sum(count - 1 for count in id_counter.values() if count > 1)
    
    # Подсчёт дубликатов SKU
    sku_counter = Counter(skus)
    sku_duplicates = sum(count - 1 for count in sku_counter.values() if count > 1)
    
    duplicates_count = id_duplicates + sku_duplicates
    
    # Подсчёт успешно сопоставленных (есть в CSV и локально)
    mapped_count = 0
    skipped_count = 0
    
    for row in rows:
        business_id = row.get('Meta: business_id', '').strip()
        if business_id and local_checks.get(business_id, False):
            mapped_count += 1
        else:
            skipped_count += 1
    
    statistics = {
        "total_products": total_products,
        "mapped": mapped_count,
        "skipped": skipped_count,
        "duplicates": duplicates_count
    }
    
    logger.info(f"📊 Статистика:")
    logger.info(f"   Всего продуктов: {statistics['total_products']}")
    logger.info(f"   Сопоставлено: {statistics['mapped']}")
    logger.info(f"   Пропущено: {statistics['skipped']}")
    logger.info(f"   Дубликатов: {statistics['duplicates']}")
    
    return statistics


def generate_mapping(
    woo_rows: List[Dict],
    local_checks: Dict[str, bool],
    source_file: str = None
) -> Dict:
    """
    Генерирует JSON-маппинг из обработанных данных WooCommerce экспорта.
    
    Создаёт структуру:
    - mappings_by_business_id: объект с ключами = business_id (включая variations)
    - mappings_by_sku: объект с ключами = SKU
    - mappings_by_variation_id: объект с ключами = variation_id
    - Метаданные: version, generated_at, source_file
    - Статистика: total_products, variable_products, simple_products, total_variations, mapped, skipped, duplicates
    
    Args:
        woo_rows: Список словарей с данными продуктов из CSV (результат read_woo_export)
        local_checks: Словарь {business_id: exists} с результатами проверки локальных продуктов
        source_file: Имя исходного CSV файла (опционально, будет извлечено из пути если не указано)
        
    Returns:
        Dict: Готовый словарь для сериализации в JSON согласно спецификации формата
        
    Пример:
        >>> rows, errors = read_woo_export(Path("export.csv"))
        >>> local_checks = {"amanita1": True, "other": False}
        >>> mapping = generate_mapping(rows, local_checks, "export.csv")
        >>> json.dumps(mapping, indent=2, ensure_ascii=False)
    """
    logger.info("🔨 Генерация маппинга...")
    
    # Инициализация структур маппинга
    mappings_by_business_id: Dict[str, Dict] = {}
    mappings_by_sku: Dict[str, Dict] = {}
    mappings_by_variation_id: Dict[str, Dict] = {}
    
    # Счётчики для статистики
    variable_products = 0
    simple_products = 0
    total_variations = 0
    
    # Шаг 1: Связать вариации с родителями
    variations_by_parent = link_variations_to_parent(woo_rows)
    
    # Шаг 2: Обработка каждой строки WooCommerce экспорта (только родители и simple)
    for row in woo_rows:
        row_type = identify_product_type(row)
        
        # Пропускаем вариации — они обрабатываются через variations_by_parent
        if row_type == 'variation':
            continue
        
        # Извлечение обязательных полей
        id_value = row.get('ID', '').strip()
        sku_value = row.get('SKU', '').strip()
        business_id_value = row.get('Meta: business_id', '').strip()
        
        # Пропуск строк без обязательных полей
        if not id_value or not sku_value or not business_id_value:
            logger.warning(f"⚠️ Пропуск строки без обязательных полей: ID={id_value}, SKU={sku_value}, business_id={business_id_value}")
            continue
        
        try:
            woo_id = int(id_value)
        except ValueError:
            logger.warning(f"⚠️ Пропуск строки с невалидным ID: {id_value}")
            continue
        
        # Извлечение опциональных полей
        blockchain_id = None
        blockchain_id_str = row.get('Meta: blockchain_id', '').strip()
        if blockchain_id_str:
            try:
                blockchain_id = int(blockchain_id_str)
            except ValueError:
                logger.debug(f"⚠️ Невалидный blockchain_id для {business_id_value}: {blockchain_id_str}")
        
        component_ids = None
        component_ids_str = row.get('Meta: component_ids', '').strip()
        if component_ids_str:
            try:
                if ',' in component_ids_str:
                    component_ids = [int(x.strip()) for x in component_ids_str.split(',')]
                else:
                    component_ids = int(component_ids_str)
            except ValueError:
                logger.debug(f"⚠️ Невалидный component_ids для {business_id_value}: {component_ids_str}")
        
        form = row.get('Meta: form', '').strip() or None
        name = row.get('Name', '').strip() or None
        
        regular_price = row.get('Regular price', '').strip()
        if not regular_price:
            regular_price = None
        
        # Создание записи для mappings_by_business_id
        business_mapping = {
            "woo_id": woo_id,
            "sku": sku_value,
            "product_type": row_type  # 'variable' или 'simple'
        }
        
        # Добавление опциональных полей
        if blockchain_id is not None:
            business_mapping["blockchain_id"] = blockchain_id
        if component_ids is not None:
            business_mapping["component_ids"] = component_ids
        if form:
            business_mapping["form"] = form
        if name:
            business_mapping["name"] = name
        if regular_price is not None:
            business_mapping["regular_price"] = regular_price
        
        # Шаг 3: Добавление вариаций для variable продуктов
        if row_type == 'variable' and business_id_value in variations_by_parent:
            variations_list = []
            for var_row in variations_by_parent[business_id_value]:
                var_id_str = var_row.get('ID', '').strip()
                var_attr = var_row.get('Attribute 1 value(s)', '').strip()
                var_price = var_row.get('Regular price', '').strip()
                
                try:
                    var_id = int(var_id_str)
                except ValueError:
                    logger.warning(f"⚠️ Невалидный ID вариации: {var_id_str}")
                    continue
                
                variation_entry = {
                    "variation_id": var_id,
                    "attribute_value": var_attr,
                    "regular_price": var_price
                }
                variations_list.append(variation_entry)
                
                # Добавление в индекс mappings_by_variation_id
                mappings_by_variation_id[str(var_id)] = {
                    "parent_business_id": business_id_value,
                    "parent_woo_id": woo_id,
                    "attribute_value": var_attr,
                    "regular_price": var_price
                }
                total_variations += 1
            
            if variations_list:
                business_mapping["variations"] = variations_list
            variable_products += 1
        else:
            simple_products += 1
        
        mappings_by_business_id[business_id_value] = business_mapping
        
        # Создание записи для mappings_by_sku
        sku_mapping = {
            "woo_id": woo_id,
            "business_id": business_id_value
        }
        if blockchain_id is not None:
            sku_mapping["blockchain_id"] = blockchain_id
        
        mappings_by_sku[sku_value] = sku_mapping
        
        logger.debug(f"✅ Добавлен маппинг: business_id={business_id_value}, SKU={sku_value}, woo_id={woo_id}, type={row_type}")
    
    # Формирование статистики
    statistics = {
        "total_products": len(mappings_by_business_id),
        "variable_products": variable_products,
        "simple_products": simple_products,
        "total_variations": total_variations,
        "mapped": len(mappings_by_business_id),
        "skipped": 0,
        "duplicates": 0
    }
    
    # Формирование метаданных
    metadata = {
        "version": "2.0",  # Новая версия с поддержкой вариаций
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_file": source_file or "unknown.csv"
    }
    
    # Формирование финальной структуры
    mapping = {
        **metadata,
        "mappings_by_business_id": mappings_by_business_id,
        "mappings_by_sku": mappings_by_sku,
        "mappings_by_variation_id": mappings_by_variation_id,
        "statistics": statistics
    }
    
    logger.info(f"✅ Маппинг сгенерирован:")
    logger.info(f"   Записей по business_id: {len(mappings_by_business_id)}")
    logger.info(f"   Записей по SKU: {len(mappings_by_sku)}")
    logger.info(f"   Записей по variation_id: {len(mappings_by_variation_id)}")
    logger.info(f"   Variable продуктов: {variable_products}")
    logger.info(f"   Simple продуктов: {simple_products}")
    logger.info(f"   Всего вариаций: {total_variations}")
    
    return mapping


# ============================================================================
# Функции merge-режима
# ============================================================================

def load_existing_mapping(output_path: Path) -> Dict:
    """
    Загружает существующий mapping из файла.
    
    Args:
        output_path: Путь к файлу mapping.json
        
    Returns:
        Dict: Существующий mapping или None, если файл не существует
    """
    if not output_path.exists():
        logger.info(f"📄 Существующий mapping не найден: {output_path}")
        return None
    
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        logger.info(f"✅ Загружен существующий mapping: {len(existing.get('mappings_by_business_id', {}))} продуктов")
        return existing
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"⚠️ Ошибка чтения существующего mapping: {e}")
        return None


def merge_mappings(existing: Dict, new: Dict) -> Tuple[Dict, Dict]:
    """
    Мержит новый mapping в существующий.
    
    Логика:
    - Продукты из new обновляют/добавляют записи в existing
    - Продукты, которых нет в new, остаются без изменений
    - Вариации мержатся по variation_id (обновление или добавление)
    
    Args:
        existing: Существующий mapping (может быть None)
        new: Новый mapping из текущего CSV
        
    Returns:
        Tuple[Dict, Dict]: (merged_mapping, merge_stats)
        merge_stats = {
            "updated_products": int,
            "new_products": int,
            "unchanged_products": int,
            "updated_variations": int,
            "new_variations": int
        }
    """
    if existing is None:
        return new, {
            "updated_products": 0,
            "new_products": len(new.get("mappings_by_business_id", {})),
            "unchanged_products": 0,
            "updated_variations": 0,
            "new_variations": len(new.get("mappings_by_variation_id", {}))
        }
    
    merged = {
        "version": new.get("version", existing.get("version", "2.0")),
        "generated_at": new["generated_at"],
        "source_file": new["source_file"],
        "mappings_by_business_id": dict(existing.get("mappings_by_business_id", {})),
        "mappings_by_sku": dict(existing.get("mappings_by_sku", {})),
        "mappings_by_variation_id": dict(existing.get("mappings_by_variation_id", {})),
        "statistics": {}
    }
    
    stats = {
        "updated_products": 0,
        "new_products": 0,
        "unchanged_products": 0,
        "updated_variations": 0,
        "new_variations": 0
    }
    
    # Merge mappings_by_business_id
    for business_id, new_data in new.get("mappings_by_business_id", {}).items():
        if business_id in merged["mappings_by_business_id"]:
            # Обновление существующего продукта
            old_data = merged["mappings_by_business_id"][business_id]
            
            # Merge вариаций
            if "variations" in new_data:
                old_variations = {v["variation_id"]: v for v in old_data.get("variations", [])}
                for new_var in new_data["variations"]:
                    var_id = new_var["variation_id"]
                    if var_id in old_variations:
                        stats["updated_variations"] += 1
                    else:
                        stats["new_variations"] += 1
                    old_variations[var_id] = new_var
                new_data["variations"] = list(old_variations.values())
            
            merged["mappings_by_business_id"][business_id] = new_data
            stats["updated_products"] += 1
            logger.debug(f"  ↻ Обновлён продукт: {business_id}")
        else:
            # Новый продукт
            merged["mappings_by_business_id"][business_id] = new_data
            stats["new_products"] += 1
            if "variations" in new_data:
                stats["new_variations"] += len(new_data["variations"])
            logger.debug(f"  ➕ Новый продукт: {business_id}")
    
    # Подсчёт unchanged
    stats["unchanged_products"] = len(existing.get("mappings_by_business_id", {})) - stats["updated_products"]
    
    # Merge mappings_by_sku
    for sku, sku_data in new.get("mappings_by_sku", {}).items():
        merged["mappings_by_sku"][sku] = sku_data
    
    # Merge mappings_by_variation_id
    for var_id, var_data in new.get("mappings_by_variation_id", {}).items():
        merged["mappings_by_variation_id"][var_id] = var_data
    
    # Пересчёт статистики
    merged["statistics"] = {
        "total_products": len(merged["mappings_by_business_id"]),
        "total_variations": len(merged["mappings_by_variation_id"]),
        "variable_products": sum(
            1 for p in merged["mappings_by_business_id"].values()
            if p.get("product_type") == "variable"
        ),
        "simple_products": sum(
            1 for p in merged["mappings_by_business_id"].values()
            if p.get("product_type") in ("simple", None)
        ),
        "mapped": len(merged["mappings_by_business_id"]),
        "skipped": 0,
        "duplicates": 0
    }
    
    return merged, stats


def main():
    """
    Главная функция CLI для генерации маппинга WooCommerce ID ↔ business_id.
    
    Выполняет:
    1. Парсинг аргументов командной строки
    2. Чтение WooCommerce экспорта
    3. Валидацию и сопоставление с локальными данными
    4. Генерацию маппинга
    5. Запись JSON-файла
    6. Вывод статистики
    """
    parser = argparse.ArgumentParser(
        description="Генерация маппинга WooCommerce ID ↔ business_id для инкрементальных экспортов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Базовое использование (дефолтная выходная директория: data/sellers/iveta)
  python3 bot/utility/generate_woo_id_mapping.py \\
    --input data/sellers/iveta/catalog/wc-product-export-2-1-2026-1767372043965.csv

  # С указанием выходной директории
  python3 bot/utility/generate_woo_id_mapping.py \\
    --input export.csv \\
    --output-dir data/sellers/iveta

  # С указанием директории продуктов
  python3 bot/utility/generate_woo_id_mapping.py \\
    --input export.csv \\
    --output-dir data/sellers/iveta \\
    --products-dir data/sellers/iveta/products

  # С детальным логированием
  python3 bot/utility/generate_woo_id_mapping.py \\
    --input export.csv \\
    --output-dir data/sellers/iveta \\
    --verbose

  # Полная перезапись (без merge)
  python3 bot/utility/generate_woo_id_mapping.py \\
    --input full_export.csv \\
    --output-dir data/sellers/iveta \\
    --overwrite

  # Инкрементальное обновление (merge по умолчанию)
  python3 bot/utility/generate_woo_id_mapping.py \\
    --input partial_export.csv \\
    --output-dir data/sellers/iveta

Примечание: 
  - Выходной файл всегда сохраняется как {output_dir}/catalog/woo_id_mapping.json
  - По умолчанию используется merge-режим: новые данные объединяются с существующими
  - Используйте --overwrite для полной перезаписи
        """
    )
    
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Путь к CSV файлу WooCommerce экспорта (обязательный)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/sellers/iveta',
        help='Директория для сохранения выходного JSON файла (по умолчанию: data/sellers/iveta). Файл будет сохранён как {output_dir}/catalog/woo_id_mapping.json'
    )
    
    parser.add_argument(
        '--products-dir',
        type=str,
        default='data/sellers/iveta/products',
        help='Путь к директории с продуктами (по умолчанию: data/sellers/iveta/products)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Включить детальное логирование (DEBUG уровень)'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Полностью перезаписать mapping вместо merge (по умолчанию: merge с существующим)'
    )
    
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    print("=" * 70)
    print("Генерация маппинга WooCommerce ID ↔ business_id")
    print("=" * 70)
    print()
    
    try:
        # Преобразование путей в Path объекты
        input_path = Path(args.input)
        output_dir = Path(args.output_dir)
        # Формирование полного пути к выходному файлу: {output_dir}/catalog/woo_id_mapping.json
        output_path = output_dir / "catalog" / "woo_id_mapping.json"
        products_dir = Path(args.products_dir)
        
        # Валидация входных путей
        if not input_path.exists():
            print(f"❌ Ошибка: файл не найден: {input_path}")
            return 1
        
        if not input_path.is_file():
            print(f"❌ Ошибка: путь не является файлом: {input_path}")
            return 1
        
        # Создание директории для выходного файла, если её нет
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Выходная директория: {output_dir}")
        logger.info(f"📄 Выходной файл: {output_path}")
        
        # Шаг 1: Чтение WooCommerce экспорта
        print("📖 Шаг 1: Чтение WooCommerce экспорта...")
        woo_rows, errors = read_woo_export(input_path)
        
        if errors:
            print(f"⚠️ Обнаружено {len(errors)} ошибок валидации при чтении CSV")
            for error in errors[:5]:  # Показываем первые 5 ошибок
                print(f"   {error}")
            if len(errors) > 5:
                print(f"   ... и ещё {len(errors) - 5} ошибок")
        
        if not woo_rows:
            print("❌ Ошибка: не удалось прочитать ни одной валидной строки из CSV")
            return 1
        
        print(f"✅ Прочитано строк: {len(woo_rows)}")
        print()
        
        # Шаг 2: Проверка локальных продуктов
        print("🔍 Шаг 2: Проверка локальных продуктов...")
        local_checks: Dict[str, bool] = {}
        
        for row in woo_rows:
            business_id = row.get('Meta: business_id', '').strip()
            if business_id:
                exists = check_local_product_exists(business_id, products_dir)
                local_checks[business_id] = exists
        
        found_count = sum(1 for exists in local_checks.values() if exists)
        print(f"✅ Найдено локальных продуктов: {found_count} из {len(local_checks)}")
        print()
        
        # Шаг 3: Генерация маппинга
        print("🔨 Шаг 3: Генерация маппинга...")
        source_file = input_path.name
        new_mapping = generate_mapping(woo_rows, local_checks, source_file)
        print()
        
        # Шаг 4: Merge или перезапись
        merge_stats = None
        if args.overwrite:
            print("🔄 Шаг 4: Режим OVERWRITE — полная перезапись маппинга")
            mapping = new_mapping
        else:
            print("🔄 Шаг 4: Режим MERGE — объединение с существующим маппингом...")
            existing_mapping = load_existing_mapping(output_path)
            if existing_mapping:
                mapping, merge_stats = merge_mappings(existing_mapping, new_mapping)
                print(f"✅ Merge выполнен")
            else:
                mapping = new_mapping
                print(f"ℹ️ Существующий mapping не найден, создаётся новый")
        print()
        
        # Шаг 5: Запись JSON-файла
        print(f"💾 Шаг 5: Запись JSON-файла: {output_path}")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
            print(f"✅ JSON-файл успешно записан")
        except IOError as e:
            print(f"❌ Ошибка при записи JSON-файла: {e}")
            return 1
        print()
        
        # Шаг 6: Вывод статистики
        print("=" * 70)
        if merge_stats:
            print("РЕЗУЛЬТАТЫ (MERGE MODE)")
        else:
            print("РЕЗУЛЬТАТЫ")
        print("=" * 70)
        
        stats = mapping['statistics']
        print(f"Всего продуктов: {stats['total_products']}")
        print(f"  - Variable продуктов: {stats.get('variable_products', 0)}")
        print(f"  - Simple продуктов: {stats.get('simple_products', 0)}")
        print(f"Всего вариаций: {stats.get('total_variations', 0)}")
        print()
        
        if merge_stats:
            print("Merge статистика:")
            print(f"  Обновлено продуктов: {merge_stats['updated_products']}")
            print(f"  Новых продуктов: {merge_stats['new_products']}")
            print(f"  Без изменений: {merge_stats['unchanged_products']}")
            print(f"  Обновлено вариаций: {merge_stats['updated_variations']}")
            print(f"  Новых вариаций: {merge_stats['new_variations']}")
            print()
        
        print(f"Записей по business_id: {len(mapping['mappings_by_business_id'])}")
        print(f"Записей по SKU: {len(mapping['mappings_by_sku'])}")
        print(f"Записей по variation_id: {len(mapping.get('mappings_by_variation_id', {}))}")
        print()
        print(f"✅ Маппинг сохранён в: {output_path}")
        print()
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Ошибка: файл не найден: {e}")
        return 1
    except IOError as e:
        print(f"❌ Ошибка ввода/вывода: {e}")
        return 1
    except ValueError as e:
        print(f"❌ Ошибка валидации: {e}")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        logger.exception("Детали ошибки:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
