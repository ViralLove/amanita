#!/usr/bin/env python3
"""
Тесты граничных случаев для обновленных моделей.
Проверяет пограничные значения и исключительные ситуации.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import Product, PriceInfo
from bot.model.organic_component import OrganicComponent

def test_component_id_edge_cases():
    """Тест граничных случаев для component_id"""
    test_cases = [
        ('a', True, 'Минимальная длина'),
        ('a' * 50, True, 'Максимальная длина'),
        ('a' * 51, False, 'Превышение максимальной длины'),
        ('test_123', True, 'Подчеркивания и цифры'),
        ('TestComp', True, 'Заглавные буквы'),
        ('test-comp', True, 'Дефисы допустимы'),
        ('test comp', False, 'Пробелы недопустимы'),
        ('test@comp', False, 'Спецсимволы недопустимы'),
        ('', False, 'Пустая строка'),
        ('   ', False, 'Только пробелы')
    ]
    
    passed = 0
    total = len(test_cases)
    
    for component_id, should_pass, description in test_cases:
        try:
            component = OrganicComponent(
                component_id=component_id,
                description_cid='QmTest123',
                proportion='100%'
            )
            if should_pass:
                print(f'✅ {description}: {component_id}')
                passed += 1
            else:
                print(f'❌ {description}: Ожидалась ошибка для {component_id}')
        except ValueError as e:
            if not should_pass:
                print(f'✅ {description}: Правильно отклонен {component_id}')
                passed += 1
            else:
                print(f'❌ {description}: Неожиданная ошибка для {component_id}: {e}')
        except Exception as e:
            print(f'❌ {description}: Неожиданная ошибка {type(e).__name__}: {e}')
    
    print(f'Тест component_id: {passed}/{total} прошли')
    assert passed == total, f"Тест не прошел: {passed}/{total}"

def test_proportion_edge_cases():
    """Тест граничных случаев для пропорций"""
    test_cases = [
        ('0%', False, 'Нулевая пропорция'),
        ('1%', True, 'Минимальная пропорция'),
        ('100%', True, 'Максимальная пропорция'),
        ('100.00%', True, 'Пропорция с десятичными'),
        ('101%', False, 'Превышение 100%'),
        ('-1%', False, 'Отрицательная пропорция'),
        ('50.5%', True, 'Десятичная пропорция'),
        ('1g', True, 'Граммы'),
        ('0g', False, 'Нулевые граммы'),
        ('1000g', True, 'Большие граммы'),
        ('50ml', True, 'Миллилитры'),
        ('0ml', False, 'Нулевые миллилитры'),
        ('invalid', False, 'Невалидный формат')
    ]
    
    passed = 0
    total = len(test_cases)
    
    for proportion, should_pass, description in test_cases:
        try:
            component = OrganicComponent(
                component_id='test_comp',
                description_cid='QmTest123',
                proportion=proportion
            )
            if should_pass:
                print(f'✅ {description}: {proportion}')
                passed += 1
            else:
                print(f'❌ {description}: Ожидалась ошибка для {proportion}')
        except ValueError as e:
            if not should_pass:
                print(f'✅ {description}: Правильно отклонен {proportion}')
                passed += 1
            else:
                print(f'❌ {description}: Неожиданная ошибка для {proportion}: {e}')
        except Exception as e:
            print(f'❌ {description}: Неожиданная ошибка {type(e).__name__}: {e}')
    
    print(f'Тест пропорций: {passed}/{total} прошли')
    assert passed == total, f"Тест не прошел: {passed}/{total}"

def test_price_edge_cases():
    """Тест граничных случаев для цен"""
    test_cases = [
        (0.01, True, 'Минимальная цена'),
        (0, False, 'Нулевая цена'),
        (-1, False, 'Отрицательная цена'),
        (999999, True, 'Большая цена'),
        ('10.50', True, 'Строковая цена'),
        ('invalid', False, 'Невалидная строка'),
        (None, False, 'None цена')
    ]
    
    passed = 0
    total = len(test_cases)
    
    for price, should_pass, description in test_cases:
        try:
            price_info = PriceInfo(
                price=price,
                currency='EUR'
            )
            if should_pass:
                print(f'✅ {description}: {price}')
                passed += 1
            else:
                print(f'❌ {description}: Ожидалась ошибка для {price}')
        except (ValueError, TypeError) as e:
            if not should_pass:
                print(f'✅ {description}: Правильно отклонена {price}')
                passed += 1
            else:
                print(f'❌ {description}: Неожиданная ошибка для {price}: {e}')
        except Exception as e:
            print(f'❌ {description}: Неожиданная ошибка {type(e).__name__}: {e}')
    
    print(f'Тест цен: {passed}/{total} прошли')
    assert passed == total, f"Тест не прошел: {passed}/{total}"

def test_proportion_sum_edge_cases():
    """Тест граничных случаев для суммы пропорций"""
    test_cases = [
        (['50%', '50%'], True, 'Точно 100%'),
        (['33.33%', '33.33%', '33.34%'], True, 'Сумма 100% с округлением'),
        (['50%', '49%'], False, 'Сумма 99%'),
        (['50%', '51%'], False, 'Сумма 101%'),
        (['100%'], True, 'Один компонент 100%'),
        (['25%', '25%', '25%', '25%'], True, 'Четыре компонента по 25%'),
        (['1g', '2g'], True, 'Граммы (не проверяется сумма)'),
        (['50ml', '30ml'], True, 'Миллилитры (не проверяется сумма)')
    ]
    
    passed = 0
    total = len(test_cases)
    
    for proportions, should_pass, description in test_cases:
        try:
            components = []
            for i, proportion in enumerate(proportions):
                components.append(OrganicComponent(
                    component_id=f'comp_{i}',
                    description_cid=f'QmComp{i}',
                    proportion=proportion
                ))
            
            price = PriceInfo(price=100, currency='EUR')
            
            product = Product(
                id='test_proportions',
                alias='test-proportions',
                status=1,
                title='Test Proportions',
                categories=['test'],
                forms=['test'],
                species='test',
                cid='QmTestProp',
                organic_components=components,
                prices=[price],
                cover_image_url='QmTestCover'
            )
            
            if should_pass:
                print(f'✅ {description}: {proportions}')
                passed += 1
            else:
                print(f'❌ {description}: Ожидалась ошибка для {proportions}')
                
        except ValueError as e:
            if not should_pass:
                print(f'✅ {description}: Правильно отклонено {proportions}')
                passed += 1
            else:
                print(f'❌ {description}: Неожиданная ошибка для {proportions}: {e}')
        except Exception as e:
            print(f'❌ {description}: Неожиданная ошибка {type(e).__name__}: {e}')
    
    print(f'Тест сумм пропорций: {passed}/{total} прошли')
    assert passed == total, f"Тест не прошел: {passed}/{total}"

if __name__ == '__main__':
    print('🧪 Тестирование граничных случаев моделей')
    print('=' * 60)
    
    results = []
    results.append(test_component_id_edge_cases())
    results.append(test_proportion_edge_cases())
    results.append(test_price_edge_cases())
    results.append(test_proportion_sum_edge_cases())
    
    print('=' * 60)
    passed_tests = sum(results)
    total_tests = len(results)
    print(f'✅ Граничные тесты: {passed_tests}/{total_tests} прошли')
    
    if passed_tests == total_tests:
        print('🎉 Все граничные тесты успешны!')
    else:
        print('⚠️  Некоторые граничные тесты не прошли')
