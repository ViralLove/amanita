#!/usr/bin/env python3
"""
Тесты валидации продуктов
"""

import pytest
from bot.model.product import Product, OrganicComponent, PriceInfo

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
            business_id='test_product_1',
            blockchain_id=1,
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
        print(f'  - business_id: {product.business_id}')
        print(f'  - blockchain_id: {product.blockchain_id}')
        print(f'  - status: {product.status}')
        print(f'  - title: {product.title}')
        print(f'  - components: {len(product.organic_components)}')
        print(f'  - prices: {len(product.prices)}')

        # Проверяем, что поля установлены корректно
        assert product.business_id == 'test_product_1'
        assert product.blockchain_id == 1
        assert product.status == 1
        assert product.title == 'Test Product'
        assert len(product.organic_components) == 2
        assert len(product.prices) == 2

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
            business_id='simple_product',
            blockchain_id=2,
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
        print(f'  - business_id: {product.business_id}')
        print(f'  - blockchain_id: {product.blockchain_id}')
        print(f'  - status: {product.status}')
        print(f'  - title: {product.title}')
        print(f'  - components: {len(product.organic_components)}')
        print(f'  - prices: {len(product.prices)}')

        # Проверяем, что поля установлены корректно
        assert product.business_id == 'simple_product'
        assert product.blockchain_id == 2
        assert product.status == 1
        assert product.title == 'Simple Product'
        assert len(product.organic_components) == 1
        assert len(product.prices) == 1

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
