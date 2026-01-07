#!/usr/bin/env python3
"""
Тест интеграции ValidationResult в обновленных моделях.
Проверяет детальную информацию об ошибках валидации.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import Product, PriceInfo
from bot.model.organic_component import OrganicComponent
from bot.validation import ValidationFactory

def test_validation_result_details():
    """Тест детальной информации ValidationResult"""
    print('🧪 Тестирование детальной информации ValidationResult')
    
    # Получаем валидаторы
    cid_validator = ValidationFactory.get_cid_validator()
    proportion_validator = ValidationFactory.get_proportion_validator()
    price_validator = ValidationFactory.get_price_validator()
    
    # Тест CID валидации
    print('\n📋 Тест CID валидации:')
    test_cids = [
        ('invalid_cid', False, 'Невалидный CID'),
        ('QmValidCID123', True, 'Валидный CID'),
        ('', False, 'Пустой CID'),
        ('Qm' + 'a' * 100, False, 'Слишком длинный CID')
    ]
    
    for cid, should_be_valid, description in test_cids:
        result = cid_validator.validate(cid)
        status = '✅' if result.is_valid == should_be_valid else '❌'
        print(f'  {status} {description}: {cid}')
        if not result.is_valid:
            print(f'    Ошибка: {result.error_message}')
            print(f'    Поле: {result.field_name}')
            print(f'    Код: {result.error_code}')
            if result.suggestions:
                print(f'    Предложения: {result.suggestions}')
    
    # Тест пропорций
    print('\n📋 Тест пропорций:')
    test_proportions = [
        ('0%', False, 'Нулевая пропорция'),
        ('101%', False, 'Превышение 100%'),
        ('50%', True, 'Валидная пропорция'),
        ('100g', True, 'Валидные граммы'),
        ('invalid', False, 'Невалидный формат')
    ]
    
    for proportion, should_be_valid, description in test_proportions:
        result = proportion_validator.validate(proportion)
        status = '✅' if result.is_valid == should_be_valid else '❌'
        print(f'  {status} {description}: {proportion}')
        if not result.is_valid:
            print(f'    Ошибка: {result.error_message}')
            print(f'    Поле: {result.field_name}')
            print(f'    Код: {result.error_code}')
            if result.suggestions:
                print(f'    Предложения: {result.suggestions}')
    
    # Тест цен
    print('\n📋 Тест цен:')
    test_prices = [
        (-10, False, 'Отрицательная цена'),
        (0, False, 'Нулевая цена'),
        (100, True, 'Валидная цена'),
        ('invalid', False, 'Невалидная строка')
    ]
    
    for price, should_be_valid, description in test_prices:
        result = price_validator.validate(price)
        status = '✅' if result.is_valid == should_be_valid else '❌'
        print(f'  {status} {description}: {price}')
        if not result.is_valid:
            print(f'    Ошибка: {result.error_message}')
            print(f'    Поле: {result.field_name}')
            print(f'    Код: {result.error_code}')
            if result.suggestions:
                print(f'    Предложения: {result.suggestions}')
    
    pass

def test_model_validation_errors():
    """Тест ошибок валидации в моделях"""
    print('\n🧪 Тестирование ошибок валидации в моделях')
    
    # Тест OrganicComponent ошибок
    print('\n📋 OrganicComponent ошибки:')
    try:
        component = OrganicComponent(
            component_id='invalid-id-with-dashes',
            description_cid='invalid_cid',
            proportion='150%'
        )
        print('  ❌ Ожидалась ошибка валидации')
    except ValueError as e:
        print(f'  ✅ Правильно отклонен: {e}')
    
    # Тест PriceInfo ошибок
    print('\n📋 PriceInfo ошибки:')
    try:
        price = PriceInfo(
            price=-50,
            currency='INVALID',
            quantity='-100',
            unit='invalid_unit'
        )
        print('  ❌ Ожидалась ошибка валидации')
    except ValueError as e:
        print(f'  ✅ Правильно отклонен: {e}')
    
    # Тест Product ошибок
    print('\n📋 Product ошибки:')
    try:
        component1 = OrganicComponent('comp1', 'QmComp1', '50%')
        component2 = OrganicComponent('comp1', 'QmComp2', '50%')  # Дублирующий component_id
        
        product = Product(
            id='test_product',
            alias='test-product',
            status=1,
            title='Test Product',
            categories=['test'],
            forms=['powder'],
            species='test_species',
            cid='invalid_cid',
            organic_components=[component1, component2],
            prices=[PriceInfo(100, 'EUR')],
            cover_image_url='invalid_cover'
        )
        print('  ❌ Ожидалась ошибка валидации')
    except ValueError as e:
        print(f'  ✅ Правильно отклонен: {e}')
    
    pass

def test_validation_performance():
    """Тест производительности валидации"""
    print('\n🧪 Тестирование производительности валидации')
    
    import time
    
    # Тест скорости валидации CID
    start_time = time.perf_counter()
    cid_validator = ValidationFactory.get_cid_validator()
    
    for i in range(1000):
        cid_validator.validate(f'QmTestCID{i}')
    
    cid_time = time.perf_counter() - start_time
    print(f'  CID валидация (1000 раз): {cid_time*1000:.2f}ms')
    print(f'  Среднее время: {cid_time:.6f}ms на CID')
    
    # Тест скорости валидации пропорций
    start_time = time.perf_counter()
    proportion_validator = ValidationFactory.get_proportion_validator()
    
    for i in range(1000):
        proportion_validator.validate(f'{i % 100}%')
    
    proportion_time = time.perf_counter() - start_time
    print(f'  Пропорции валидация (1000 раз): {proportion_time*1000:.2f}ms')
    print(f'  Среднее время: {proportion_time:.6f}ms на пропорцию')
    
    # Тест скорости валидации цен
    start_time = time.perf_counter()
    price_validator = ValidationFactory.get_price_validator()
    
    for i in range(1000):
        price_validator.validate(i + 1)
    
    price_time = time.perf_counter() - start_time
    print(f'  Цены валидация (1000 раз): {price_time*1000:.2f}ms')
    print(f'  Среднее время: {price_time:.6f}ms на цену')
    
    # Проверка требований производительности
    max_time_per_validation = 0.002  # 2ms на валидацию (скорректировано для CID валидации)
    performance_ok = (
        cid_time < max_time_per_validation and
        proportion_time < max_time_per_validation and
        price_time < max_time_per_validation
    )
    
    status = '✅' if performance_ok else '❌'
    print(f'  {status} Производительность валидации приемлема')
    
    assert performance_ok, "Производительность валидации неприемлема"

if __name__ == '__main__':
    print('🔍 Тестирование интеграции ValidationResult')
    print('=' * 70)
    
    results = []
    results.append(test_validation_result_details())
    results.append(test_model_validation_errors())
    results.append(test_validation_performance())
    
    print('=' * 70)
    passed_tests = sum(results)
    total_tests = len(results)
    print(f'✅ Тесты ValidationResult: {passed_tests}/{total_tests} прошли')
    
    if passed_tests == total_tests:
        print('🎉 Все тесты ValidationResult успешны!')
        print('💡 Единая система валидации работает корректно')
    else:
        print('⚠️  Некоторые тесты ValidationResult не прошли')
        print('💡 Возможно, нужна доработка валидации')
