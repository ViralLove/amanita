#!/usr/bin/env python3
"""
Тест ошибок валидации PriceInfo класса.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import PriceInfo

def test_invalid_price():
    """Тест невалидной цены"""
    try:
        PriceInfo(price=-10, currency='EUR')
        print('❌ Ожидалась ошибка для отрицательной цены')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации цены: {e}')
        pass

def test_invalid_currency():
    """Тест невалидной валюты"""
    try:
        PriceInfo(price=100, currency='INVALID')
        print('❌ Ожидалась ошибка для невалидной валюты')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации валюты: {e}')
        pass

def test_quantity_without_unit():
    """Тест количества без единицы измерения"""
    try:
        PriceInfo(price=100, currency='EUR', quantity='100')
        print('❌ Ожидалась ошибка для количества без единицы измерения')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации количества без единицы: {e}')
        pass

def test_invalid_unit():
    """Тест невалидной единицы измерения"""
    try:
        PriceInfo(price=100, currency='EUR', quantity='100', unit='invalid')
        print('❌ Ожидалась ошибка для невалидной единицы измерения')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации единицы измерения: {e}')
        pass

def test_negative_quantity():
    """Тест отрицательного количества"""
    try:
        PriceInfo(price=100, currency='EUR', quantity='-50', unit='g')
        print('❌ Ожидалась ошибка для отрицательного количества')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации отрицательного количества: {e}')
        pass

if __name__ == '__main__':
    print('🧪 Тестирование ошибок валидации PriceInfo')
    print('=' * 60)
    
    test_invalid_price()
    test_invalid_currency()
    test_quantity_without_unit()
    test_invalid_unit()
    test_negative_quantity()
    
    print('=' * 60)
    print('✅ Тестирование ошибок завершено')
