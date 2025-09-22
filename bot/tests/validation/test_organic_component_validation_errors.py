#!/usr/bin/env python3
"""
Тест обработки ошибок валидации OrganicComponent класса.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from model.organic_component import OrganicComponent

def test_invalid_biounit_id():
    """Тест невалидного biounit_id"""
    try:
        # Невалидный biounit_id с недопустимыми символами
        component = OrganicComponent(
            biounit_id='invalid@id-with-special-chars',  # Содержит спецсимволы
            description_cid='Qm123456789',
            proportion='100%'
        )
        print('❌ Ошибка: невалидный biounit_id должен вызвать исключение')
        assert False, "Тест не прошел"
        
    except ValueError as e:
        print(f'✅ Правильно обработана ошибка biounit_id: {e}')
        pass
    except Exception as e:
        print(f'❌ Неожиданная ошибка: {e}')
        assert False, "Тест не прошел"

def test_invalid_description_cid():
    """Тест невалидного description_cid"""
    try:
        # Невалидный CID
        component = OrganicComponent(
            biounit_id='test_id',
            description_cid='invalid_cid',  # Невалидный CID
            proportion='100%'
        )
        print('❌ Ошибка: невалидный description_cid должен вызвать исключение')
        assert False, "Тест не прошел"
        
    except ValueError as e:
        print(f'✅ Правильно обработана ошибка description_cid: {e}')
        pass
    except Exception as e:
        print(f'❌ Неожиданная ошибка: {e}')
        assert False, "Тест не прошел"

def test_invalid_proportion():
    """Тест невалидной пропорции"""
    try:
        # Невалидная пропорция
        component = OrganicComponent(
            biounit_id='test_id',
            description_cid='Qm123456789',
            proportion='invalid_proportion'  # Невалидная пропорция
        )
        print('❌ Ошибка: невалидная пропорция должна вызвать исключение')
        assert False, "Тест не прошел"
        
    except ValueError as e:
        print(f'✅ Правильно обработана ошибка пропорции: {e}')
        pass
    except Exception as e:
        print(f'❌ Неожиданная ошибка: {e}')
        assert False, "Тест не прошел"

def test_empty_biounit_id():
    """Тест пустого biounit_id"""
    try:
        # Пустой biounit_id
        component = OrganicComponent(
            biounit_id='',  # Пустой ID
            description_cid='Qm123456789',
            proportion='100%'
        )
        print('❌ Ошибка: пустой biounit_id должен вызвать исключение')
        assert False, "Тест не прошел"
        
    except ValueError as e:
        print(f'✅ Правильно обработана ошибка пустого biounit_id: {e}')
        pass
    except Exception as e:
        print(f'❌ Неожиданная ошибка: {e}')
        assert False, "Тест не прошел"

if __name__ == '__main__':
    print('🧪 Тестирование обработки ошибок валидации OrganicComponent')
    print('=' * 60)
    
    test_invalid_biounit_id()
    test_invalid_description_cid()
    test_invalid_proportion()
    test_empty_biounit_id()
    
    print('=' * 60)
    print('✅ Тестирование завершено')
