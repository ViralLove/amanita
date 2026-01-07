#!/usr/bin/env python3
"""
Тест валидации PriceInfo класса с единой системой валидации.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from bot.model.product import PriceInfo

def test_priceinfo_validation():
    """Тест создания PriceInfo с валидацией"""
    try:
        # Создаем тестовые данные
        price_info = PriceInfo(
            price=100,
            currency='EUR',
            quantity='100',
            unit='g'
        )
        
        print('✅ PriceInfo создан успешно с валидацией')
        print(f'  - price: {price_info.price}')
        print(f'  - currency: {price_info.currency}')
        print(f'  - quantity: {price_info.quantity}')
        print(f'  - unit: {price_info.unit}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка валидации: {e}')
        assert False, "Тест не прошел"

def test_priceinfo_simple():
    """Тест создания простого PriceInfo без quantity"""
    try:
        # Создаем простой PriceInfo
        price_info = PriceInfo(
            price=50,
            currency='USD'
        )
        
        print('✅ Простой PriceInfo создан успешно')
        print(f'  - price: {price_info.price}')
        print(f'  - currency: {price_info.currency}')
        print(f'  - quantity: {price_info.quantity}')
        print(f'  - unit: {price_info.unit}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка создания простого PriceInfo: {e}')
        assert False, "Тест не прошел"

def test_priceinfo_volume():
    """Тест создания PriceInfo с количеством (объем)"""
    try:
        # Создаем PriceInfo с количеством (например, объем)
        price_info = PriceInfo(
            price=75,
            currency='EUR',
            quantity='30',
            unit='ml'
        )
        
        print('✅ PriceInfo с количеством создан успешно')
        print(f'  - price: {price_info.price}')
        print(f'  - quantity: {price_info.quantity}')
        print(f'  - unit: {price_info.unit}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка создания PriceInfo с количеством: {e}')
        assert False, "Тест не прошел"

if __name__ == '__main__':
    print('🧪 Тестирование валидации PriceInfo')
    print('=' * 50)
    
    test_priceinfo_validation()
    test_priceinfo_simple()
    test_priceinfo_with_quantity()
    
    print('=' * 50)
    print('✅ Тестирование завершено')
