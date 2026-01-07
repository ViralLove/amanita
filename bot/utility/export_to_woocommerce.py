#!/usr/bin/env python3
"""
Скрипт экспорта продуктов из блокчейна в CSV для импорта в WooCommerce.

Использование:
    python utility/export_to_woocommerce.py [--language ru] [--output products.csv]
    
Примеры:
    # Экспорт на русском языке в файл по умолчанию
    python utility/export_to_woocommerce.py
    
    # Экспорт на английском языке в указанный файл
    python utility/export_to_woocommerce.py --language en --output woocommerce_en.csv
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# Добавить bot в путь (если запускается из корня проекта)
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.woocommerce.html_format_adapter import HTMLFormatAdapter
from services.woocommerce.export import export_to_woocommerce_csv
from dependencies import get_product_registry_service, get_formatter_service


def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Экспорт продуктов в CSV для WooCommerce",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s                                    # Экспорт на русском в woocommerce_products.csv
  %(prog)s --language en                     # Экспорт на английском
  %(prog)s --output custom_products.csv      # Указать выходной файл
  %(prog)s --language en --output en.csv     # Комбинация параметров
  
  # Дифф-экспорт: только цены с reuse WooCommerce ID
  %(prog)s --columns "ID,SKU,Regular price" --reuse-woo-id
  
  # Дифф-экспорт: только описания с reuse WooCommerce ID
  %(prog)s --columns "ID,SKU,Description" --reuse-woo-id
  
  # Дифф-экспорт с указанием mapping-файла
  %(prog)s --columns "ID,SKU,Regular price" --reuse-woo-id --mapping path/to/mapping.json
        """
    )
    parser.add_argument(
        "--language",
        type=str,
        default="ru",
        help="Язык локализации (по умолчанию: ru)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Путь к выходному CSV файлу (по умолчанию: data/sellers/{seller_name}/catalog/woocommerce_products.csv)"
    )
    parser.add_argument(
        "--seller-name",
        type=str,
        default=None,
        help="Имя продавца для пути (по умолчанию: из SELLER_BUSINESS_ID или 'iveta')"
    )
    parser.add_argument(
        "--columns",
        type=str,
        default=None,
        help="Список колонок для экспорта через запятую (по умолчанию: все колонки). Пример: 'ID,SKU,Regular price'"
    )
    parser.add_argument(
        "--reuse-woo-id",
        action='store_true',
        help="Использовать WooCommerce ID из mapping-файла для обновления существующих продуктов"
    )
    parser.add_argument(
        "--mapping",
        type=str,
        default=None,
        help="Путь к mapping-файлу (по умолчанию: data/sellers/{seller_name}/catalog/woo_id_mapping.json)"
    )
    return parser.parse_args()


async def main():
    """Главная функция скрипта"""
    import os
    args = parse_args()
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск экспорта продуктов в WooCommerce CSV")
    
    # Определение seller_name
    seller_name = args.seller_name
    if not seller_name:
        seller_name = os.getenv("SELLER_BUSINESS_ID", "iveta")
        logger.info(f"📋 Seller name из переменной окружения SELLER_BUSINESS_ID: {seller_name}")
    else:
        logger.info(f"📋 Seller name из аргумента: {seller_name}")
    
    # Определение project_root: data/ находится на уровень выше bot/
    # Структура: project_root/ (где data/) -> bot/ -> utility/ -> export_to_woocommerce.py
    project_root = Path(__file__).parent.parent.parent
    
    # Определение output_path
    if args.output:
        output_path = Path(args.output)
        # Если путь относительный, разрешаем относительно project_root
        if not output_path.is_absolute():
            output_path = project_root / output_path
        logger.info(f"📋 Output path из аргумента: {output_path}")
    else:
        # Путь по умолчанию: data/sellers/{seller_name}/catalog/woocommerce_products.csv
        # Используем project_root (на уровень выше bot/)
        output_path = project_root / "data" / "sellers" / seller_name / "catalog" / "woocommerce_products.csv"
        logger.info(f"📋 Output path по умолчанию: {output_path}")
    
    logger.info(f"📋 Параметры: language={args.language}, seller_name={seller_name}, output={output_path}")
    
    # Загрузка mapping-файла (если включён --reuse-woo-id)
    mapping_data = None
    if args.reuse_woo_id:
        if args.mapping:
            mapping_path = Path(args.mapping)
            if not mapping_path.is_absolute():
                mapping_path = project_root / mapping_path
        else:
            # Путь по умолчанию: data/sellers/{seller_name}/catalog/woo_id_mapping.json
            mapping_path = project_root / "data" / "sellers" / seller_name / "catalog" / "woo_id_mapping.json"
        
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                logger.info(f"✅ Mapping-файл загружен: {mapping_path}")
                
                # Валидация структуры mapping
                missing_fields = []
                if "mappings_by_business_id" not in mapping_data:
                    missing_fields.append("mappings_by_business_id")
                if "mappings_by_sku" not in mapping_data:
                    missing_fields.append("mappings_by_sku")
                
                if missing_fields:
                    logger.error(
                        f"❌ Mapping-файл имеет невалидную структуру. Отсутствуют обязательные поля: {', '.join(missing_fields)}. "
                        f"Ожидаемая структура: {{'mappings_by_business_id': {{...}}, 'mappings_by_sku': {{...}}}}"
                    )
                    logger.warning("⚠️ Продолжаем без reuse ID.")
                    mapping_data = None
                else:
                    # Логирование статистики mapping
                    stats = mapping_data.get("statistics", {})
                    total_products = stats.get("total_products", 0)
                    mapped = stats.get("mapped", 0)
                    logger.info(
                        f"📊 Статистика mapping: всего продуктов {total_products}, "
                        f"сопоставлено {mapped}, записей по business_id {len(mapping_data.get('mappings_by_business_id', {}))}, "
                        f"записей по SKU {len(mapping_data.get('mappings_by_sku', {}))}"
                    )
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга mapping-файла {mapping_path}: {e}")
                logger.warning("⚠️ Продолжаем без reuse ID.")
                mapping_data = None
            except Exception as e:
                logger.error(f"❌ Ошибка при загрузке mapping-файла {mapping_path}: {e}")
                logger.warning("⚠️ Продолжаем без reuse ID.")
                mapping_data = None
        else:
            # reuse_woo_id включён, но mapping-файл не найден
            logger.warning(
                f"⚠️ Mapping-файл не найден по пути: {mapping_path}. "
                "Колонка ID будет добавлена пустой."
            )
    
    # Парсинг списка колонок
    columns = None
    if args.columns:
        columns = [col.strip() for col in args.columns.split(',') if col.strip()]
        logger.info(f"📋 Выбранные колонки ({len(columns)}): {', '.join(columns)}")
    
    try:
        # 1. Создать сервисы через DI
        logger.info("🔧 Инициализация сервисов...")
        product_registry = get_product_registry_service()
        
        # Создать formatter_service с правильным языком
        from dependencies import get_localization_service
        localization_service = get_localization_service(lang=args.language)
        formatter_service = get_formatter_service(localization_service=localization_service)
        html_adapter = HTMLFormatAdapter(formatter_service=formatter_service)
        
        logger.info("✅ Сервисы инициализированы")
        
        # 2. Загрузить продукты из блокчейна
        logger.info("📦 Загрузка продуктов из блокчейна...")
        products = await product_registry.get_all_products(language=args.language)
        logger.info(f"✅ Загружено продуктов: {len(products)}")
        
        if not products:
            logger.warning("⚠️  Список продуктов пуст. CSV файл не будет создан.")
            return
        
        # 3. Экспорт в CSV
        logger.info("📝 Генерация CSV файла...")
        output_path = export_to_woocommerce_csv(
            products=products,
            language=args.language,
            output_path=str(output_path),
            html_adapter=html_adapter,
            columns=columns,
            mapping_data=mapping_data,
            reuse_woo_id=args.reuse_woo_id
        )
        
        logger.info(f"✅ CSV файл создан: {output_path}")
        logger.info("✨ Экспорт завершен успешно")
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Экспорт прерван пользователем")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

