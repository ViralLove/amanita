#!/usr/bin/env python3
"""
Тест валидации Product класса с единой системой валидации.
"""

from model.product import Product, PriceInfo
from model.organic_component import OrganicComponent

def test_product_validation():
    """Тест создания Product с валидацией"""
    try:
        # Создаем тестовые данные
        component = OrganicComponent('test_id', 'Qm123456789', '100%')
        price = PriceInfo(price=100, currency='EUR', weight='100', weight_unit='g')
        
        # Создаем Product (должен вызвать __post_init__ с валидацией)
        product = Product(
            id=1,
            alias='test',
            status=1,
            cid='Qm123456789',
            title='Test Product',
            organic_components=[component],
            cover_image_url='Qm123456789',
            categories=['test'],
            forms=['powder'],
            species='test',
            prices=[price]
        )
        
        print('✅ Product создан успешно с валидацией')
        print(f'  - ID: {product.id}')
        print(f'  - Title: {product.title}')
        print(f'  - Components: {len(product.organic_components)}')
        print(f'  - Prices: {len(product.prices)}')
        
        return True
        
    except Exception as e:
        print(f'❌ Ошибка валидации: {e}')
        return False

if __name__ == '__main__':
    test_product_validation()
