#!/usr/bin/env python3
"""
Скрипт для быстрой отладки каталога с использованием мок-данных
"""
import sys
import os
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.mock_catalog_service import MockCatalogService
from services.application.catalog.catalog_service import CatalogService
from services.application.catalog.product_service import ProductService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_mock_catalog():
    """Тестирует мок-каталог"""
    logger.info("🚀 Начинаем тестирование мок-каталога")
    
    try:
        # Создаем мок-сервис
        mock_service = MockCatalogService()
        
        # Получаем все продукты
        products = mock_service.get_all_products()
        logger.info(f"📦 Получено {len(products)} продуктов")
        
        # Выводим информацию о каждом продукте
        for i, product in enumerate(products, 1):
            logger.info(f"\n📋 Продукт {i}:")
            logger.info(f"  Business ID: {product.business_id}")
            logger.info(f"  Title: {product.title}")
            logger.info(f"  Blockchain ID: {product.blockchain_id}")
            logger.info(f"  Categories: {product.categories}")
            logger.info(f"  Forms: {product.forms}")
            logger.info(f"  Components: {len(product.organic_components)}")
            
            for j, component in enumerate(product.organic_components, 1):
                logger.info(f"    Компонент {j}: {component.biounit_id} ({component.proportion})")
        
        # Тестируем поиск по ID
        test_product = mock_service.get_product_by_id("amanita_lux")
        if test_product:
            logger.info(f"\n✅ Тест поиска успешен: найден {test_product.title}")
        else:
            logger.error("❌ Тест поиска провален")
        
        logger.info("\n🎉 Тестирование мок-каталога завершено успешно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании мок-каталога: {e}")
        return False

def test_product_validation():
    """Тестирует валидацию продуктов"""
    logger.info("\n🔍 Тестируем валидацию продуктов...")
    
    try:
        from model.organic_component import OrganicComponent
        from model.component_description import ComponentDescription
        
        # Тестируем компонент с дефисом
        component_data = {
            "biounit_id": "lions-mane",
            "description_cid": "QmTestDescription2",
            "proportion": "100%"
        }
        
        component = OrganicComponent.from_dict(component_data)
        logger.info(f"✅ Компонент с дефисом создан успешно: {component.biounit_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка валидации: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("🎯 Запуск отладочного скрипта каталога")
    
    # Тест 1: Мок-каталог
    test1_success = test_mock_catalog()
    
    # Тест 2: Валидация продуктов
    test2_success = test_product_validation()
    
    # Результаты
    logger.info(f"\n📊 Результаты тестирования:")
    logger.info(f"  Мок-каталог: {'✅' if test1_success else '❌'}")
    logger.info(f"  Валидация: {'✅' if test2_success else '❌'}")
    
    if test1_success and test2_success:
        logger.info("🎉 Все тесты прошли успешно!")
        return 0
    else:
        logger.error("❌ Некоторые тесты провалились")
        return 1

if __name__ == "__main__":
    exit(main())
