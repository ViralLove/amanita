#!/usr/bin/env python3
"""
Тесты производительности для обновленных моделей.
Проверяет скорость валидации и отсутствие деградации производительности.
"""

import sys
import os
import time
from typing import List
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import Product, PriceInfo
from bot.model.organic_component import OrganicComponent

def measure_time(func):
    """Декоратор для измерения времени выполнения"""
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        return result, execution_time
    return wrapper

@measure_time
def create_single_component():
    """Создание одного OrganicComponent"""
    return OrganicComponent(
        component_id='test_component',
        description_cid='QmTestComponent123',
        proportion='100%'
    )

@measure_time
def create_single_price():
    """Создание одного PriceInfo"""
    return PriceInfo(
        price=100,
        currency='EUR',
        weight='100',
        weight_unit='g'
    )

@measure_time
def create_single_product():
    """Создание одного Product"""
    component = OrganicComponent('comp1', 'QmComp1', '100%')
    price = PriceInfo(100, 'EUR')
    
    return Product(
        id='test_product',
        alias='test-product',
        status=1,
        title='Test Product',
        categories=['test'],
        forms=['powder'],
        species='test_species',
        cid='QmTestProduct',
        organic_components=[component],
        prices=[price],
        cover_image_url='QmTestCover'
    )

@measure_time
def create_complex_product():
    """Создание сложного Product с множественными компонентами и ценами"""
    components = []
    for i in range(5):
        components.append(OrganicComponent(
            component_id=f'component_{i}',
            description_cid=f'QmComp{i}',
            proportion='20%'
        ))
    
    prices = []
    currencies = ['EUR', 'USD', 'GBP', 'JPY', 'RUB']
    weight_units = ['g', 'kg', 'oz', 'lb']
    
    for i in range(10):
        prices.append(PriceInfo(
            price=100 + i * 10,
            currency=currencies[i % len(currencies)],
            weight=str((i + 1) * 50),
            weight_unit=weight_units[i % len(weight_units)]
        ))
    
    return Product(
        id='complex_product',
        alias='complex-product',
        status=1,
        title='Complex Test Product',
        categories=['mushrooms', 'adaptogens', 'nootropics'],
        forms=['powder', 'capsules', 'extract'],
        species='complex_blend',
        cid='QmComplexProduct',
        organic_components=components,
        prices=prices,
        cover_image_url='QmComplexCover'
    )

@measure_time
def create_batch_products(count: int):
    """Создание множества продуктов"""
    products = []
    
    for i in range(count):
        component = OrganicComponent(f'comp_{i}', f'QmComp{i}', '100%')
        price = PriceInfo(100 + i, 'EUR')
        
        product = Product(
            id=f'product_{i}',
            alias=f'product-{i}',
            status=1,
            title=f'Product {i}',
            categories=['test'],
            forms=['powder'],
            species=f'species_{i}',
            cid=f'QmProduct{i}',
            organic_components=[component],
            prices=[price],
            cover_image_url=f'QmCover{i}'
        )
        products.append(product)
    
    return products

def test_single_operations_performance():
    """Тест производительности отдельных операций"""
    print('🚀 Тестирование производительности отдельных операций')
    
    # Тест создания компонента
    component, comp_time = create_single_component()
    print(f'  OrganicComponent: {comp_time*1000:.2f}ms')
    
    # Тест создания цены
    price, price_time = create_single_price()
    print(f'  PriceInfo: {price_time*1000:.2f}ms')
    
    # Тест создания продукта
    product, prod_time = create_single_product()
    print(f'  Product: {prod_time*1000:.2f}ms')
    
    # Проверка требований производительности
    max_time = 0.001  # 1ms
    
    results = {
        'OrganicComponent': comp_time < max_time,
        'PriceInfo': price_time < max_time,
        'Product': prod_time < max_time
    }
    
    print(f'  Требования производительности (<1ms):')
    for operation, passed in results.items():
        status = '✅' if passed else '❌'
        print(f'    {status} {operation}')
    
    assert all(results.values()), "Не все операции соответствуют требованиям производительности"

def test_complex_operations_performance():
    """Тест производительности сложных операций"""
    print('🚀 Тестирование производительности сложных операций')
    
    # Тест создания сложного продукта
    complex_product, complex_time = create_complex_product()
    print(f'  Сложный Product (5 компонентов, 10 цен): {complex_time*1000:.2f}ms')
    
    # Тест пакетного создания
    batch_products, batch_time = create_batch_products(100)
    avg_time = batch_time / 100
    print(f'  Пакетное создание 100 продуктов: {batch_time*1000:.2f}ms')
    print(f'  Среднее время на продукт: {avg_time*1000:.2f}ms')
    
    # Проверка требований производительности
    max_complex_time = 0.010  # 10ms для сложного продукта
    max_avg_time = 0.005     # 5ms в среднем на продукт
    
    results = {
        'Сложный продукт': complex_time < max_complex_time,
        'Среднее время': avg_time < max_avg_time
    }
    
    print(f'  Требования производительности:')
    for operation, passed in results.items():
        status = '✅' if passed else '❌'
        print(f'    {status} {operation}')
    
    assert all(results.values()), "Не все сложные операции соответствуют требованиям производительности"

def test_validation_overhead():
    """Тест накладных расходов валидации"""
    print('🚀 Тестирование накладных расходов валидации')
    
    # Измеряем время создания без валидации (теоретическое)
    start_time = time.perf_counter()
    
    # Создаем объекты напрямую (минимальные накладные расходы)
    for i in range(1000):
        # Просто создаем строки и числа - минимальные операции
        test_id = f'test_{i}'
        test_price = 100 + i
        test_cid = f'QmTest{i}'
    
    baseline_time = time.perf_counter() - start_time
    
    # Измеряем время создания с валидацией
    start_time = time.perf_counter()
    
    for i in range(100):  # Меньше итераций для реальных объектов
        component = OrganicComponent(f'comp_{i}', f'QmComp{i}', '100%')
    
    validation_time = time.perf_counter() - start_time
    avg_validation_time = validation_time / 100
    
    print(f'  Базовое время (1000 операций): {baseline_time*1000:.2f}ms')
    print(f'  Время с валидацией (100 компонентов): {validation_time*1000:.2f}ms')
    print(f'  Среднее время валидации на компонент: {avg_validation_time*1000:.2f}ms')
    
    # Проверяем, что валидация не добавляет значительных накладных расходов
    max_overhead = 0.005  # 5ms на компонент максимум
    overhead_ok = avg_validation_time < max_overhead
    
    status = '✅' if overhead_ok else '❌'
    print(f'    {status} Накладные расходы валидации приемлемы')
    
    assert overhead_ok, "Накладные расходы валидации неприемлемы"

if __name__ == '__main__':
    print('⚡ Тестирование производительности обновленных моделей')
    print('=' * 70)
    
    results = []
    results.append(test_single_operations_performance())
    print()
    results.append(test_complex_operations_performance())
    print()
    results.append(test_validation_overhead())
    
    print('=' * 70)
    passed_tests = sum(results)
    total_tests = len(results)
    print(f'✅ Тесты производительности: {passed_tests}/{total_tests} прошли')
    
    if passed_tests == total_tests:
        print('🎉 Все тесты производительности успешны!')
        print('💡 Валидация работает быстро и эффективно')
    else:
        print('⚠️  Некоторые тесты производительности не прошли')
        print('💡 Возможно, нужна оптимизация валидации')
