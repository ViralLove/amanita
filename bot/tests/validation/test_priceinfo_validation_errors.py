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

def test_weight_without_unit():
    """Тест веса без единицы измерения"""
    try:
        PriceInfo(price=100, currency='EUR', weight='100')
        print('❌ Ожидалась ошибка для веса без единицы измерения')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации веса без единицы: {e}')
        pass

def test_invalid_weight_unit():
    """Тест невалидной единицы веса"""
    try:
        PriceInfo(price=100, currency='EUR', weight='100', weight_unit='invalid')
        print('❌ Ожидалась ошибка для невалидной единицы веса')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации единицы веса: {e}')
        pass

def test_volume_without_unit():
    """Тест объема без единицы измерения"""
    try:
        PriceInfo(price=100, currency='EUR', volume='30')
        print('❌ Ожидалась ошибка для объема без единицы измерения')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации объема без единицы: {e}')
        pass

def test_invalid_volume_unit():
    """Тест невалидной единицы объема"""
    try:
        PriceInfo(price=100, currency='EUR', volume='30', volume_unit='invalid')
        print('❌ Ожидалась ошибка для невалидной единицы объема')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации единицы объема: {e}')
        pass

def test_weight_and_volume_together():
    """Тест одновременного указания веса и объема"""
    try:
        PriceInfo(
            price=100, 
            currency='EUR', 
            weight='100', 
            weight_unit='g',
            volume='30',
            volume_unit='ml'
        )
        print('❌ Ожидалась ошибка для одновременного указания веса и объема')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации веса и объема: {e}')
        pass

def test_negative_weight():
    """Тест отрицательного веса"""
    try:
        PriceInfo(price=100, currency='EUR', weight='-50', weight_unit='g')
        print('❌ Ожидалась ошибка для отрицательного веса')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации отрицательного веса: {e}')
        pass

def test_negative_volume():
    """Тест отрицательного объема"""
    try:
        PriceInfo(price=100, currency='EUR', volume='-20', volume_unit='ml')
        print('❌ Ожидалась ошибка для отрицательного объема')
        assert False, "Тест не прошел"
    except ValueError as e:
        print(f'✅ Ошибка валидации отрицательного объема: {e}')
        pass

if __name__ == '__main__':
    print('🧪 Тестирование ошибок валидации PriceInfo')
    print('=' * 60)
    
    test_invalid_price()
    test_invalid_currency()
    test_weight_without_unit()
    test_invalid_weight_unit()
    test_volume_without_unit()
    test_invalid_volume_unit()
    test_weight_and_volume_together()
    test_negative_weight()
    test_negative_volume()
    
    print('=' * 60)
    print('✅ Тестирование ошибок завершено')
