#!/usr/bin/env python3
"""
Тест валидации Product класса с обновленным PriceInfo.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import Product, PriceInfo
from bot.model.organic_component import OrganicComponent

def test_product_with_priceinfo():
    """Тест создания Product с PriceInfo"""
    try:
        # Создаем компоненты
        component1 = OrganicComponent(
            biounit_id='amanita_muscaria',
            description_cid='QmTest1',
            proportion='50%'
        )
        
        component2 = OrganicComponent(
            biounit_id='cordyceps_militaris',
            description_cid='QmTest2',
            proportion='50%'
        )
        
        # Создаем цены
        price1 = PriceInfo(
            price=100,
            currency='EUR',
            weight='100',
            weight_unit='g'
        )
        
        price2 = PriceInfo(
            price=200,
            currency='EUR',
            weight='200',
            weight_unit='g'
        )
        
        # Создаем продукт
        product = Product(
            id='test_product_1',
            alias='test-product',
            status=1,
            title='Test Product',
            categories=['mushrooms'],
            forms=['powder'],
            species='amanita',
            cid='QmProductTest',
            organic_components=[component1, component2],
            prices=[price1, price2],
            cover_image_url='QmCoverTest'
        )
        
        print('✅ Product создан успешно с обновленным PriceInfo')
        print(f'  - id: {product.id}')
        print(f'  - title: {product.title}')
        print(f'  - components: {len(product.organic_components)}')
        print(f'  - prices: {len(product.prices)}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка создания Product: {e}')
        assert False, "Тест не прошел"

def test_product_simple():
    """Тест создания простого Product"""
    try:
        # Создаем простой компонент
        component = OrganicComponent(
            biounit_id='simple_component',
            description_cid='QmSimple',
            proportion='100%'
        )
        
        # Создаем простую цену
        price = PriceInfo(
            price=50,
            currency='USD'
        )
        
        # Создаем продукт
        product = Product(
            id='simple_product',
            alias='simple-product',
            status=1,
            title='Simple Product',
            categories=['herbs'],
            forms=['whole'],
            species='chamomile',
            cid='QmSimpleProduct',
            organic_components=[component],
            prices=[price],
            cover_image_url='QmSimpleCover'
        )
        
        print('✅ Простой Product создан успешно')
        print(f'  - id: {product.id}')
        print(f'  - title: {product.title}')
        print(f'  - components: {len(product.organic_components)}')
        print(f'  - prices: {len(product.prices)}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка создания простого Product: {e}')
        assert False, "Тест не прошел"

if __name__ == '__main__':
    print('🧪 Тестирование Product с обновленным PriceInfo')
    print('=' * 60)
    
    test_product_with_priceinfo()
    test_product_simple()
    
    print('=' * 60)
    print('✅ Тестирование завершено')
