"""
Тесты для FallbackLocalizationService

Проверяет каскадную стратегию fallback:
- Запрошенный язык → Русский → Ключ перевода → Placeholder
- Статистика и метрики качества
- Конфигурация и настройки
- Обработка ошибок
"""

import unittest
import sys
import os

# Добавляем путь к модулям проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
bot_dir = os.path.join(current_dir, '..')
sys.path.insert(0, os.path.abspath(bot_dir))

from services.common.fallback_localization_service import (
    FallbackLocalizationService, 
    FallbackLevel, 
    FallbackResult
)

class TestFallbackLocalizationService(unittest.TestCase):
    """Тесты для FallbackLocalizationService"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.fallback_service = FallbackLocalizationService(default_language='ru')
        
        # Тестовые данные переводов
        self.translation_sources = {
            'en': {
                'product': {
                    'test_product': {
                        'title': 'Test Product',
                        'description': 'Test Description'
                    }
                },
                'component': {
                    'test_component': {
                        'common_name': 'Test Component',
                        'scientific_name': 'Testus Componentus'
                    }
                }
            },
            'ru': {
                'product': {
                    'test_product': {
                        'title': 'Тестовый продукт',
                        'description': 'Тестовое описание'
                    }
                },
                'component': {
                    'test_component': {
                        'common_name': 'Тестовый компонент',
                        'scientific_name': 'Тестус Компонентус'
                    }
                }
            }
        }
    
    def test_requested_language_fallback(self):
        """Тест: Fallback на запрошенном языке"""
        result = self.fallback_service.get_translation_with_fallback(
            key='product.test_product.title',
            requested_language='en',
            translation_sources=self.translation_sources
        )
        
        self.assertEqual(result.translation, 'Test Product')
        self.assertEqual(result.level, FallbackLevel.REQUESTED_LANGUAGE)
        self.assertEqual(result.source, 'language_en')
        self.assertEqual(result.confidence, 1.0)
    
    def test_default_language_fallback(self):
        """Тест: Fallback на язык по умолчанию (русский)"""
        result = self.fallback_service.get_translation_with_fallback(
            key='product.test_product.title',
            requested_language='fr',  # Французский не доступен
            translation_sources=self.translation_sources
        )
        
        self.assertEqual(result.translation, 'Тестовый продукт')
        self.assertEqual(result.level, FallbackLevel.DEFAULT_LANGUAGE)
        self.assertEqual(result.source, 'language_ru')
        self.assertEqual(result.confidence, 0.8)
    
    def test_translation_key_fallback(self):
        """Тест: Fallback на ключ перевода"""
        result = self.fallback_service.get_translation_with_fallback(
            key='product.nonexistent_product.title',
            requested_language='fr',
            translation_sources=self.translation_sources
        )
        
        self.assertEqual(result.translation, '[Title]')
        self.assertEqual(result.level, FallbackLevel.TRANSLATION_KEY)
        self.assertEqual(result.source, 'translation_key')
        self.assertEqual(result.confidence, 0.3)
    
    def test_placeholder_fallback(self):
        """Тест: Fallback на placeholder"""
        result = self.fallback_service.get_translation_with_fallback(
            key='product.nonexistent_product.nonexistent_field',
            requested_language='fr',
            translation_sources=self.translation_sources
        )
        
        self.assertEqual(result.translation, '[Nonexistent Field]')
        self.assertEqual(result.level, FallbackLevel.TRANSLATION_KEY)  # Сначала ключ перевода
        self.assertEqual(result.source, 'translation_key')
        self.assertEqual(result.confidence, 0.3)
    
    def test_custom_placeholder_templates(self):
        """Тест: Пользовательские шаблоны placeholder'ов"""
        # Добавляем пользовательский шаблон
        self.fallback_service.add_placeholder_template(
            'product', 'custom_field', 'Пользовательское поле'
        )
        
        result = self.fallback_service.get_translation_with_fallback(
            key='product.test_product.custom_field',
            requested_language='fr',
            translation_sources=self.translation_sources
        )
        
        self.assertEqual(result.translation, '[Custom Field]')  # Сначала ключ перевода
        self.assertEqual(result.level, FallbackLevel.TRANSLATION_KEY)
    
    def test_parameter_formatting(self):
        """Тест: Форматирование с параметрами"""
        result = self.fallback_service.get_translation_with_fallback(
            key='product.test_product.title',
            requested_language='en',
            translation_sources={
                'en': {
                    'product': {
                        'test_product': {
                            'title': 'Hello {name}!'
                        }
                    }
                }
            },
            name='World'
        )
        
        self.assertEqual(result.translation, 'Hello World!')
        self.assertEqual(result.level, FallbackLevel.REQUESTED_LANGUAGE)
    
    def test_fallback_statistics(self):
        """Тест: Статистика fallback операций"""
        # Очищаем статистику
        self.fallback_service.clear_statistics()
        
        # Выполняем различные fallback операции
        self.fallback_service.get_translation_with_fallback(
            'product.test_product.title', 'en', self.translation_sources
        )  # requested_language hit
        
        self.fallback_service.get_translation_with_fallback(
            'product.test_product.title', 'fr', self.translation_sources
        )  # default_language hit
        
        self.fallback_service.get_translation_with_fallback(
            'product.nonexistent.title', 'fr', self.translation_sources
        )  # translation_key hit
        
        self.fallback_service.get_translation_with_fallback(
            'product.nonexistent.nonexistent', 'fr', self.translation_sources
        )  # placeholder hit
        
        # Проверяем статистику
        stats = self.fallback_service.get_fallback_statistics()
        
        self.assertEqual(stats['total_requests'], 4)
        self.assertEqual(stats['fallback_distribution']['requested_language'], 25.0)
        self.assertEqual(stats['fallback_distribution']['default_language'], 25.0)
        self.assertEqual(stats['fallback_distribution']['translation_key'], 50.0)  # 2 запроса
        self.assertEqual(stats['fallback_distribution']['placeholder'], 0.0)  # 0 запросов
        self.assertEqual(stats['success_rate'], 100.0)
        self.assertEqual(stats['error_rate'], 0.0)
    
    def test_confidence_scoring(self):
        """Тест: Оценка уверенности в качестве перевода"""
        # Высококачественный перевод
        high_quality_result = self.fallback_service.get_translation_with_fallback(
            'product.test_product.title', 'en', self.translation_sources
        )
        
        self.assertTrue(self.fallback_service.is_high_quality_translation(high_quality_result))
        self.assertEqual(self.fallback_service.get_confidence_score(high_quality_result), 1.0)
        
        # Низкокачественный перевод
        low_quality_result = self.fallback_service.get_translation_with_fallback(
            'product.nonexistent.nonexistent', 'fr', self.translation_sources
        )
        
        self.assertFalse(self.fallback_service.is_high_quality_translation(low_quality_result))
        self.assertEqual(self.fallback_service.get_confidence_score(low_quality_result), 0.3)
    
    def test_fallback_configuration(self):
        """Тест: Конфигурация fallback стратегий"""
        # Отключаем fallback на ключ перевода
        self.fallback_service.configure_fallback(enable_translation_key_fallback=False)
        
        result = self.fallback_service.get_translation_with_fallback(
            'product.nonexistent.title', 'fr', self.translation_sources
        )
        
        # Должен сразу перейти к placeholder
        self.assertEqual(result.level, FallbackLevel.PLACEHOLDER)
        self.assertEqual(result.translation, '[Название продукта]')  # Из placeholder_templates
        
        # Включаем обратно
        self.fallback_service.configure_fallback(enable_translation_key_fallback=True)
    
    def test_error_handling(self):
        """Тест: Обработка ошибок"""
        # Тестируем с некорректными данными
        result = self.fallback_service.get_translation_with_fallback(
            key='invalid.key.format',
            requested_language='en',
            translation_sources={}
        )
        
        # Должен вернуть fallback на ключ перевода
        self.assertEqual(result.level, FallbackLevel.TRANSLATION_KEY)
        self.assertEqual(result.source, 'translation_key')
        self.assertEqual(result.confidence, 0.3)
        
        # Проверяем статистику ошибок
        stats = self.fallback_service.get_fallback_statistics()
        self.assertEqual(stats['error_rate'], 0.0)  # Нет ошибок, только fallback
    
    def test_different_content_types(self):
        """Тест: Разные типы контента"""
        # Тест продукта
        product_result = self.fallback_service.get_translation_with_fallback(
            'product.test_product.title', 'en', self.translation_sources
        )
        self.assertEqual(product_result.translation, 'Test Product')
        
        # Тест компонента
        component_result = self.fallback_service.get_translation_with_fallback(
            'component.test_component.common_name', 'en', self.translation_sources
        )
        self.assertEqual(component_result.translation, 'Test Component')
        
        # Тест интерфейса (fallback на placeholder)
        interface_result = self.fallback_service.get_translation_with_fallback(
            'interface.button.submit', 'en', self.translation_sources
        )
        self.assertEqual(interface_result.translation, '[Submit]')
    
    def test_cascade_fallback_sequence(self):
        """Тест: Последовательность каскадного fallback"""
        # Создаём источники только с русским языком
        ru_only_sources = {
            'ru': self.translation_sources['ru']
        }
        
        # Запрашиваем английский (недоступен) → должен fallback на русский
        result = self.fallback_service.get_translation_with_fallback(
            'product.test_product.title', 'en', ru_only_sources
        )
        
        self.assertEqual(result.translation, 'Тестовый продукт')
        self.assertEqual(result.level, FallbackLevel.DEFAULT_LANGUAGE)
        self.assertEqual(result.source, 'language_ru')
    
    def test_empty_translation_sources(self):
        """Тест: Пустые источники переводов"""
        result = self.fallback_service.get_translation_with_fallback(
            'product.test_product.title', 'en', {}
        )
        
        # Должен fallback на ключ перевода
        self.assertEqual(result.translation, '[Title]')
        self.assertEqual(result.level, FallbackLevel.TRANSLATION_KEY)
    
    def test_custom_default_value(self):
        """Тест: Пользовательское значение по умолчанию"""
        result = self.fallback_service.get_translation_with_fallback(
            'product.nonexistent.title', 'fr', self.translation_sources,
            default='Пользовательское значение'
        )
        
        # Должен использовать fallback на ключ перевода сначала
        self.assertEqual(result.translation, '[Title]')
        self.assertEqual(result.level, FallbackLevel.TRANSLATION_KEY)
    
    def test_confidence_threshold_configuration(self):
        """Тест: Настройка порога уверенности"""
        # Устанавливаем высокий порог уверенности
        self.fallback_service.configure_fallback(confidence_threshold=0.9)
        
        # Перевод с уверенностью 0.8 не должен считаться высококачественным
        result = self.fallback_service.get_translation_with_fallback(
            'product.test_product.title', 'fr', self.translation_sources
        )
        
        self.assertFalse(self.fallback_service.is_high_quality_translation(result))
        
        # Возвращаем стандартный порог
        self.fallback_service.configure_fallback(confidence_threshold=0.5)

if __name__ == '__main__':
    unittest.main()
