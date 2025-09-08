#!/usr/bin/env python3
"""
Скрипт для анализа недостающих изображений в каталоге продуктов
"""

import sys
import os
sys.path.append('.')

from services.core.blockchain import BlockchainService
from services.product.registry import ProductRegistryService
from services.product.validation import ProductValidationService
from services.core.account import AccountService
from services.core.ipfs_factory import IPFSFactory
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

def analyze_missing_images():
    """Анализирует все продукты и выявляет недостающие изображения"""
    
    print("🔍 Анализ недостающих изображений в каталоге продуктов")
    print("=" * 60)
    
    # Инициализируем сервисы
    blockchain_service = BlockchainService()
    storage_service = IPFSFactory().get_storage()
    validation_service = ProductValidationService()
    account_service = AccountService(blockchain_service)
    
    product_registry = ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    )
    
    # Получаем все продукты
    products = product_registry.get_all_products()
    
    print(f"📊 Всего продуктов в каталоге: {len(products)}")
    print()
    
    # Анализируем каждый продукт
    products_with_images = []
    products_without_images = []
    
    for i, product in enumerate(products, 1):
        product_info = {
            'id': product.id,
            'title': product.title,
            'cover_image_cid': product.cid,
            'cover_image_url': product.cover_image_url,
            'species': product.species,
            'form': product.forms[0] if product.forms else 'N/A'
        }
        
        # Проверяем наличие изображения
        if product.cid and product.cid.strip() and product.cover_image_url and product.cover_image_url.strip():
            products_with_images.append(product_info)
        else:
            products_without_images.append(product_info)
    
    # Выводим результаты
    print(f"✅ Продукты С изображениями: {len(products_with_images)}")
    print(f"❌ Продукты БЕЗ изображений: {len(products_without_images)}")
    print()
    
    if products_without_images:
        print("🚨 СПИСОК ПРОДУКТОВ БЕЗ ИЗОБРАЖЕНИЙ:")
        print("-" * 60)
        for i, product in enumerate(products_without_images, 1):
            print(f"{i:2d}. ID: {product['id']}")
            print(f"    Название: {product['title']}")
            print(f"    Вид: {product['species']}")
            print(f"    Форма: {product['form']}")
            print(f"    CID: '{product['cover_image_cid']}'")
            print(f"    URL: '{product['cover_image_url']}'")
            print()
    
    if products_with_images:
        print("✅ ПРОДУКТЫ С ИЗОБРАЖЕНИЯМИ:")
        print("-" * 60)
        for i, product in enumerate(products_with_images, 1):
            print(f"{i:2d}. {product['title']} ({product['species']})")
            print(f"    CID: {product['cover_image_cid']}")
            print(f"    URL: {product['cover_image_url']}")
            print()
    
    # Статистика
    print("📈 СТАТИСТИКА:")
    print("-" * 60)
    print(f"Всего продуктов: {len(products)}")
    print(f"С изображениями: {len(products_with_images)} ({len(products_with_images)/len(products)*100:.1f}%)")
    print(f"Без изображений: {len(products_without_images)} ({len(products_without_images)/len(products)*100:.1f}%)")
    
    if products_without_images:
        print()
        print("🔧 РЕКОМЕНДАЦИИ:")
        print("-" * 60)
        print("1. Продавцу необходимо добавить изображения для следующих продуктов:")
        for product in products_without_images:
            print(f"   - {product['title']} ({product['species']})")
        print()
        print("2. После добавления изображений обновить метаданные в IPFS")
        print("3. Обновить данные в блокчейне")

if __name__ == "__main__":
    analyze_missing_images() 