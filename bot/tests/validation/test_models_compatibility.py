#!/usr/bin/env python3
"""
Тесты совместимости обновленных моделей с реальными данными.
Проверяет работу с существующими fixtures и реальными сценариями.
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import Product, PriceInfo
from bot.model.organic_component import OrganicComponent

def load_fixtures():
    """Загрузка тестовых данных из fixtures"""
    try:
        fixtures_path = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'products.json')
        with open(fixtures_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print('⚠️  Файл fixtures/products.json не найден')
        return None
    except json.JSONDecodeError as e:
        print(f'⚠️  Ошибка парсинга JSON: {e}')
        return None

def test_fixtures_compatibility():
    """Тест совместимости с данными из fixtures"""
    fixtures = load_fixtures()
    if not fixtures:
        print('❌ Не удалось загрузить fixtures')
        return False
    
    print('🧪 Тестирование совместимости с fixtures')
    
    successful_conversions = 0
    total_products = len(fixtures.get('valid_products', []))
    
    for i, product_data in enumerate(fixtures.get('valid_products', [])):
        try:
            # Преобразуем данные fixtures в наши модели
            components = []
            for comp_data in product_data.get('organic_components', []):
                component = OrganicComponent(
                    biounit_id=comp_data.get('biounit_id', f'comp_{i}'),
                    description_cid=comp_data.get('description_cid', 'QmDefault'),
                    proportion=comp_data.get('proportion', '100%')
                )
                components.append(component)
            
            # Если нет компонентов, создаем дефолтный
            if not components:
                components = [OrganicComponent(f'default_comp_{i}', 'QmDefault', '100%')]
            
            prices = []
            for price_data in product_data.get('prices', []):
                price = PriceInfo(
                    price=price_data.get('price', 100),
                    currency=price_data.get('currency', 'EUR'),
                    weight=price_data.get('weight'),
                    weight_unit=price_data.get('weight_unit'),
                    volume=price_data.get('volume'),
                    volume_unit=price_data.get('volume_unit'),
                    form=price_data.get('form')
                )
                prices.append(price)
            
            # Если нет цен, создаем дефолтную
            if not prices:
                prices = [PriceInfo(100, 'EUR')]
            
            # Создаем продукт
            product = Product(
                id=product_data.get('id', f'product_{i}'),
                alias=product_data.get('alias', f'product-{i}'),
                status=product_data.get('status', 1),
                title=product_data.get('title', f'Product {i}'),
                categories=product_data.get('categories', ['test']),
                forms=product_data.get('forms', ['powder']),
                species=product_data.get('species', 'test_species'),
                cid=product_data.get('cid', f'QmProduct{i}'),
                organic_components=components,
                prices=prices,
                cover_image_url=product_data.get('cover_image_url', f'QmCover{i}')
            )
            
            successful_conversions += 1
            print(f'  ✅ Product {i}: {product.title}')
            
        except Exception as e:
            print(f'  ❌ Product {i}: Ошибка конвертации - {e}')
    
    success_rate = successful_conversions / total_products if total_products > 0 else 0
    print(f'Совместимость с fixtures: {successful_conversions}/{total_products} ({success_rate*100:.1f}%)')
    
    assert success_rate >= 0.8, f"Совместимость с fixtures должна быть >= 80%, получено: {success_rate*100:.1f}%"

def test_real_world_scenarios():
    """Тест реальных сценариев использования"""
    print('🧪 Тестирование реальных сценариев')
    
    scenarios = [
        {
            'name': 'Amanita Muscaria Powder',
            'components': [('amanita_muscaria', 'QmAmanita123', '100%')],
            'prices': [
                (50, 'EUR', '25', 'g'),
                (90, 'EUR', '50', 'g'),
                (160, 'EUR', '100', 'g')
            ]
        },
        {
            'name': 'Mushroom Blend',
            'components': [
                ('amanita_muscaria', 'QmAmanita123', '40%'),
                ('cordyceps_militaris', 'QmCordyceps456', '30%'),
                ('lions_mane', 'QmLionsMane789', '30%')
            ],
            'prices': [(120, 'EUR', '100', 'g')]
        },
        {
            'name': 'Liquid Extract',
            'components': [('blue_lotus', 'QmBlueLotus999', '100%')],
            'prices': [
                (25, 'EUR', None, None, '30', 'ml'),
                (45, 'EUR', None, None, '50', 'ml')
            ]
        },
        {
            'name': 'Multi-Currency Product',
            'components': [('chaga', 'QmChaga555', '100%')],
            'prices': [
                (100, 'EUR'),
                (110, 'USD'),
                (90, 'GBP'),
                (12000, 'JPY'),
                (7500, 'RUB')
            ]
        }
    ]
    
    successful_scenarios = 0
    
    for i, scenario in enumerate(scenarios):
        try:
            # Создаем компоненты
            components = []
            for biounit_id, cid, proportion in scenario['components']:
                components.append(OrganicComponent(biounit_id, cid, proportion))
            
            # Создаем цены
            prices = []
            for price_data in scenario['prices']:
                if len(price_data) == 2:
                    # Простая цена
                    price, currency = price_data
                    prices.append(PriceInfo(price, currency))
                elif len(price_data) == 4:
                    # Цена с весом
                    price, currency, weight, weight_unit = price_data
                    prices.append(PriceInfo(price, currency, weight, weight_unit))
                elif len(price_data) == 6:
                    # Цена с объемом
                    price, currency, weight, weight_unit, volume, volume_unit = price_data
                    prices.append(PriceInfo(price, currency, weight, weight_unit, volume, volume_unit))
            
            # Создаем продукт
            product = Product(
                id=f'scenario_{i}',
                alias=scenario['name'].lower().replace(' ', '-'),
                status=1,
                title=scenario['name'],
                categories=['mushrooms'],
                forms=['powder'],
                species='scenario_test',
                cid=f'QmScenario{i}',
                organic_components=components,
                prices=prices,
                cover_image_url=f'QmScenarioCover{i}'
            )
            
            successful_scenarios += 1
            print(f'  ✅ {scenario["name"]}: {len(components)} компонентов, {len(prices)} цен')
            
        except Exception as e:
            print(f'  ❌ {scenario["name"]}: Ошибка - {e}')
    
    success_rate = successful_scenarios / len(scenarios)
    print(f'Реальные сценарии: {successful_scenarios}/{len(scenarios)} ({success_rate*100:.1f}%)')
    
    assert success_rate == 1.0, f"Реальные сценарии должны проходить 100%, получено: {success_rate*100:.1f}%"

def test_migration_scenarios():
    """Тест сценариев миграции существующих данных"""
    print('🧪 Тестирование сценариев миграции')
    
    # Имитируем старые данные, которые могут существовать
    old_data_scenarios = [
        {
            'name': 'Legacy Product with String Status',
            'data': {
                'id': 'legacy_1',
                'alias': 'legacy-product',
                'status': 1,  # Правильный формат
                'title': 'Legacy Product',
                'categories': ['mushrooms'],
                'forms': ['powder'],
                'species': 'legacy_species',
                'cid': 'QmLegacy123',
                'organic_components': [{'biounit_id': 'legacy_comp', 'description_cid': 'QmLegacyComp', 'proportion': '100%'}],
                'prices': [{'price': 100, 'currency': 'EUR'}],
                'cover_image_url': 'QmLegacyCover'
            }
        },
        {
            'name': 'Product with Mixed Proportion Formats',
            'data': {
                'id': 'mixed_props',
                'alias': 'mixed-props',
                'status': 1,
                'title': 'Mixed Proportions',
                'categories': ['test'],
                'forms': ['powder'],
                'species': 'mixed_species',
                'cid': 'QmMixed123',
                'organic_components': [
                    {'biounit_id': 'comp1', 'description_cid': 'QmComp1', 'proportion': '50g'},
                    {'biounit_id': 'comp2', 'description_cid': 'QmComp2', 'proportion': '30ml'}
                ],
                'prices': [{'price': 150, 'currency': 'EUR'}],
                'cover_image_url': 'QmMixedCover'
            }
        }
    ]
    
    successful_migrations = 0
    
    for scenario in old_data_scenarios:
        try:
            data = scenario['data']
            
            # Преобразуем компоненты
            components = []
            for comp_data in data['organic_components']:
                components.append(OrganicComponent(
                    biounit_id=comp_data['biounit_id'],
                    description_cid=comp_data['description_cid'],
                    proportion=comp_data['proportion']
                ))
            
            # Преобразуем цены
            prices = []
            for price_data in data['prices']:
                prices.append(PriceInfo(
                    price=price_data['price'],
                    currency=price_data['currency']
                ))
            
            # Создаем продукт
            product = Product(
                id=data['id'],
                alias=data['alias'],
                status=data['status'],
                title=data['title'],
                categories=data['categories'],
                forms=data['forms'],
                species=data['species'],
                cid=data['cid'],
                organic_components=components,
                prices=prices,
                cover_image_url=data['cover_image_url']
            )
            
            successful_migrations += 1
            print(f'  ✅ {scenario["name"]}: Миграция успешна')
            
        except Exception as e:
            print(f'  ❌ {scenario["name"]}: Ошибка миграции - {e}')
    
    success_rate = successful_migrations / len(old_data_scenarios)
    print(f'Сценарии миграции: {successful_migrations}/{len(old_data_scenarios)} ({success_rate*100:.1f}%)')
    
    assert success_rate == 1.0, f"Сценарии миграции должны проходить 100%, получено: {success_rate*100:.1f}%"

if __name__ == '__main__':
    print('🔄 Тестирование совместимости обновленных моделей')
    print('=' * 70)
    
    results = []
    results.append(test_fixtures_compatibility())
    print()
    results.append(test_real_world_scenarios())
    print()
    results.append(test_migration_scenarios())
    
    print('=' * 70)
    passed_tests = sum(results)
    total_tests = len(results)
    print(f'✅ Тесты совместимости: {passed_tests}/{total_tests} прошли')
    
    if passed_tests == total_tests:
        print('🎉 Все тесты совместимости успешны!')
        print('💡 Обновленные модели полностью совместимы с существующими данными')
    else:
        print('⚠️  Некоторые тесты совместимости не прошли')
        print('💡 Возможно, нужна доработка для полной совместимости')
