#!/usr/bin/env python3
"""
Интеграционный тест OrganicComponent в контексте Product.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from model.organic_component import OrganicComponent
from model.product import Product, PriceInfo

def test_multi_component_product():
    """Тест создания продукта с несколькими компонентами"""
    try:
        # Создаем несколько компонентов (используем keyword arguments)
        component1 = OrganicComponent(
            component_id='amanita_muscaria',
            description_cid='Qm123456789',
            proportion='60%'
        )
        component2 = OrganicComponent(
            component_id='blue_lotus',
            description_cid='Qm987654321',
            proportion='40%'
        )
        
        # Создаем цену
        price = PriceInfo(price=100, currency='EUR', weight='100', weight_unit='g')
        
        # Создаем продукт с несколькими компонентами
        product = Product(
            id=1,
            alias='multi_component_product',
            status=1,
            cid='QmProductCID123',
            title='Multi-Component Product',
            organic_components=[component1, component2],
            cover_image_url='QmImageCID123',
            categories=['mushroom', 'flower'],
            forms=['powder', 'tincture'],
            species='Mixed',
            prices=[price]
        )
        
        print('✅ Многокомпонентный продукт создан успешно')
        print(f'  - Компонентов: {len(product.organic_components)}')
        print(f'  - Сумма пропорций: 60% + 40% = 100%')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка создания многокомпонентного продукта: {e}')
        assert False, "Тест не прошел"

def test_percentage_proportion_validation():
    """Тест валидации процентных пропорций"""
    try:
        # Компоненты с процентными пропорциями (используем keyword arguments)
        component1 = OrganicComponent(
            component_id='component1',
            description_cid='Qm123456789',
            proportion='25%'
        )
        component2 = OrganicComponent(
            component_id='component2',
            description_cid='Qm987654321',
            proportion='75%'
        )
        
        # Создаем продукт
        price = PriceInfo(price=100, currency='EUR', weight='100', weight_unit='g')
        product = Product(
            id=2,
            alias='percentage_product',
            status=1,
            cid='QmProductCID456',
            title='Percentage Product',
            organic_components=[component1, component2],
            cover_image_url='QmImageCID456',
            categories=['test'],
            forms=['powder'],
            species='Test',
            prices=[price]
        )
        
        print('✅ Продукт с процентными пропорциями создан успешно')
        print(f'  - Сумма: 25% + 75% = 100%')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка валидации процентных пропорций: {e}')
        assert False, "Тест не прошел"

def test_weight_based_proportions():
    """Тест валидации пропорций на основе веса"""
    try:
        # Компоненты с весовыми пропорциями (используем keyword arguments)
        component1 = OrganicComponent(
            component_id='component1',
            description_cid='Qm123456789',
            proportion='50g'
        )
        component2 = OrganicComponent(
            component_id='component2',
            description_cid='Qm987654321',
            proportion='50g'
        )
        
        # Создаем продукт
        price = PriceInfo(price=100, currency='EUR', weight='100', weight_unit='g')
        product = Product(
            id=3,
            alias='weight_product',
            status=1,
            cid='QmProductCID789',
            title='Weight-Based Product',
            organic_components=[component1, component2],
            cover_image_url='QmImageCID789',
            categories=['test'],
            forms=['powder'],
            species='Test',
            prices=[price]
        )
        
        print('✅ Продукт с весовыми пропорциями создан успешно')
        print(f'  - Компонент 1: 50g')
        print(f'  - Компонент 2: 50g')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка валидации весовых пропорций: {e}')
        assert False, "Тест не прошел"

if __name__ == '__main__':
    print('🧪 Интеграционное тестирование OrganicComponent в Product')
    print('=' * 60)
    
    test_multi_component_product()
    test_percentage_proportion_validation()
    test_weight_based_proportions()
    
    print('=' * 60)
    print('✅ Интеграционное тестирование завершено')
