#!/usr/bin/env python3
"""
Тест валидации OrganicComponent класса с единой системой валидации.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from model.organic_component import OrganicComponent

def test_organic_component_validation():
    """Тест создания OrganicComponent с валидацией"""
    try:
        # Создаем тестовые данные
        component = OrganicComponent(
            biounit_id='test_id',
            description_cid='Qm123456789',
            proportion='100%'
        )
        
        print('✅ OrganicComponent создан успешно с валидацией')
        print(f'  - biounit_id: {component.biounit_id}')
        print(f'  - description_cid: {component.description_cid}')
        print(f'  - proportion: {component.proportion}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка валидации: {e}')
        assert False, "Тест не прошел"

def test_validate_proportion_method():
    """Тест метода validate_proportion"""
    try:
        component = OrganicComponent(
            biounit_id='test_id',
            description_cid='Qm123456789',
            proportion='100%'
        )
        
        # Тестируем валидную пропорцию
        is_valid = component.validate_proportion()
        print(f'✅ validate_proportion() для "100%": {is_valid}')
        
        pass
        
    except Exception as e:
        print(f'❌ Ошибка в validate_proportion: {e}')
        assert False, "Тест не прошел"

if __name__ == '__main__':
    print('🧪 Тестирование валидации OrganicComponent')
    print('=' * 50)
    
    test_organic_component_validation()
    test_validate_proportion_method()
    
    print('=' * 50)
    print('✅ Тестирование завершено')
