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
        default="woocommerce_products.csv",
        help="Путь к выходному CSV файлу (по умолчанию: woocommerce_products.csv)"
    )
    return parser.parse_args()


async def main():
    """Главная функция скрипта"""
    args = parse_args()
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск экспорта продуктов в WooCommerce CSV")
    logger.info(f"📋 Параметры: language={args.language}, output={args.output}")
    
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
            output_path=args.output,
            html_adapter=html_adapter
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

