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
            weight='100',
            weight_unit='g'
        )
        
        print('✅ PriceInfo создан успешно с валидацией')
        print(f'  - price: {price_info.price}')
        print(f'  - currency: {price_info.currency}')
        print(f'  - weight: {price_info.weight}')
        print(f'  - weight_unit: {price_info.weight_unit}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка валидации: {e}')
        assert False, "Тест не прошел"

def test_priceinfo_simple():
    """Тест создания простого PriceInfo без веса/объема"""
    try:
        # Создаем простой PriceInfo
        price_info = PriceInfo(
            price=50,
            currency='USD'
        )
        
        print('✅ Простой PriceInfo создан успешно')
        print(f'  - price: {price_info.price}')
        print(f'  - currency: {price_info.currency}')
        print(f'  - weight: {price_info.weight}')
        print(f'  - volume: {price_info.volume}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка создания простого PriceInfo: {e}')
        assert False, "Тест не прошел"

def test_priceinfo_volume():
    """Тест создания PriceInfo с объемом"""
    try:
        # Создаем PriceInfo с объемом
        price_info = PriceInfo(
            price=75,
            currency='EUR',
            volume='30',
            volume_unit='ml'
        )
        
        print('✅ PriceInfo с объемом создан успешно')
        print(f'  - price: {price_info.price}')
        print(f'  - volume: {price_info.volume}')
        print(f'  - volume_unit: {price_info.volume_unit}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка создания PriceInfo с объемом: {e}')
        assert False, "Тест не прошел"

if __name__ == '__main__':
    print('🧪 Тестирование валидации PriceInfo')
    print('=' * 50)
    
    test_priceinfo_validation()
    test_priceinfo_simple()
    test_priceinfo_volume()
    
    print('=' * 50)
    print('✅ Тестирование завершено')
