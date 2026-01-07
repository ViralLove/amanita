#!/usr/bin/env python3
"""
Интеграционные тесты для обновленных моделей с единой валидацией.
Проверяет взаимодействие Product, OrganicComponent и PriceInfo.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import Product, PriceInfo
from bot.model.organic_component import OrganicComponent

def test_complete_product_integration():
    """Тест полной интеграции всех моделей"""
    try:
        # Создаем компоненты с разными типами пропорций
        component1 = OrganicComponent(
            component_id='amanita_muscaria',
            description_cid='QmAmanita123',
            proportion='60%'
        )
        
        component2 = OrganicComponent(
            component_id='cordyceps_militaris', 
            description_cid='QmCordyceps456',
            proportion='40%'
        )
        
        # Создаем разные типы цен
        price_quantity_g = PriceInfo(
            price=150,
            currency='EUR',
            quantity='100',
            unit='g'
        )
        
        price_quantity_ml = PriceInfo(
            price=75,
            currency='USD', 
            quantity='50',
            unit='ml'
        )
        
        price_simple = PriceInfo(
            price=25,
            currency='EUR'
        )
        
        # Создаем полный продукт
        product = Product(
            id='integration_test_product',
            alias='integration-test',
            status=1,
            title='Integration Test Product',
            categories=['mushrooms', 'adaptogens'],
            forms=['powder', 'capsules'],
            species='amanita_cordyceps_blend',
            cid='QmProductIntegration789',
            organic_components=[component1, component2],
            prices=[price_quantity_g, price_quantity_ml, price_simple],
            cover_image_url='QmCoverIntegration999'
        )
        
        print('✅ Полная интеграция моделей успешна')
        print(f'  - Product ID: {product.id}')
        print(f'  - Components: {len(product.organic_components)}')
        print(f'  - Prices: {len(product.prices)}')
        print(f'  - Total proportion: {sum(float(c.proportion.rstrip("%")) for c in product.organic_components)}%')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка интеграции моделей: {e}')
        assert False, "Тест не прошел"

def test_multi_component_proportions():
    """Тест с множественными компонентами и проверкой пропорций"""
    try:
        # Создаем 5 компонентов с точными пропорциями
        components = [
            OrganicComponent('comp1', 'QmComp1', '20%'),
            OrganicComponent('comp2', 'QmComp2', '20%'),
            OrganicComponent('comp3', 'QmComp3', '20%'),
            OrganicComponent('comp4', 'QmComp4', '20%'),
            OrganicComponent('comp5', 'QmComp5', '20%')
        ]
        
        price = PriceInfo(price=100, currency='EUR')
        
        product = Product(
            id='multi_comp_test',
            alias='multi-comp',
            status=1,
            title='Multi Component Test',
            categories=['blend'],
            forms=['powder'],
            species='multi_blend',
            cid='QmMultiComp',
            organic_components=components,
            prices=[price],
            cover_image_url='QmMultiCover'
        )
        
        print('✅ Тест множественных компонентов успешен')
        print(f'  - Components: {len(product.organic_components)}')
        print(f'  - All unique component_ids: {len(set(c.component_id for c in components)) == 5}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка теста множественных компонентов: {e}')
        assert False, "Тест не прошел"

def test_price_variations():
    """Тест различных вариантов цен"""
    try:
        component = OrganicComponent('test_comp', 'QmTestComp', '100%')
        
        # Разные варианты цен
        prices = [
            PriceInfo(price=50, currency='EUR'),  # Простая цена
            PriceInfo(price=100, currency='USD', quantity='50', unit='g'),  # Количество (вес)
            PriceInfo(price=75, currency='EUR', quantity='30', unit='ml'),  # Количество (объем)
            PriceInfo(price=200, currency='GBP', quantity='100', unit='oz'),  # Другая единица (вес)
            PriceInfo(price=150, currency='JPY', quantity='100', unit='l')   # Другая единица (объем)
        ]
        
        product = Product(
            id='price_variations_test',
            alias='price-variations',
            status=1,
            title='Price Variations Test',
            categories=['test'],
            forms=['various'],
            species='test_species',
            cid='QmPriceTest',
            organic_components=[component],
            prices=prices,
            cover_image_url='QmPriceCover'
        )
        
        print('✅ Тест вариантов цен успешен')
        print(f'  - Total prices: {len(product.prices)}')
        print(f'  - Quantity-based prices: {sum(1 for p in prices if p.is_quantity_based)}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка теста вариантов цен: {e}')
        assert False, "Тест не прошел"

if __name__ == '__main__':
    print('🧪 Интеграционное тестирование обновленных моделей')
    print('=' * 70)
    
    test_complete_product_integration()
    test_multi_component_proportions()
    test_price_variations()
    
    print('=' * 70)
    print('✅ Интеграционное тестирование завершено')
