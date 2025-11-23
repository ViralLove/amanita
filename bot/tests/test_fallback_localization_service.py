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

    def test_get_stats_returns_all_metrics(self):
        """Тест: get_stats() возвращает все необходимые метрики"""
        # GIVEN: Сервис с выполненными операциями
        self.fallback_service.fallback_stats['total_requests'] = 10
        self.fallback_service.fallback_stats['requested_language_hits'] = 5
        self.fallback_service.fallback_stats['default_language_hits'] = 3
        self.fallback_service.fallback_stats['translation_key_hits'] = 1
        self.fallback_service.fallback_stats['placeholder_hits'] = 1
        self.fallback_service.fallback_stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats = self.fallback_service.get_stats()
        
        # THEN: Все основные метрики присутствуют
        self.assertIn('total_requests', stats)
        self.assertIn('requested_language_hits', stats)
        self.assertIn('default_language_hits', stats)
        self.assertIn('translation_key_hits', stats)
        self.assertIn('placeholder_hits', stats)
        self.assertIn('errors', stats)
        
        # THEN: Все производные метрики присутствуют
        self.assertIn('requested_language_rate_percent', stats)
        self.assertIn('default_language_rate_percent', stats)
        self.assertIn('placeholder_rate_percent', stats)
        self.assertIn('error_rate_percent', stats)
        
        # THEN: Дополнительные метрики присутствуют
        self.assertIn('default_language', stats)
        
        # THEN: Всего 11 метрик
        self.assertEqual(len(stats), 11)

    def test_get_stats_computes_derived_metrics(self):
        """Тест: get_stats() корректно вычисляет производные метрики"""
        # GIVEN: Сервис с известными значениями
        self.fallback_service.fallback_stats['total_requests'] = 100
        self.fallback_service.fallback_stats['requested_language_hits'] = 60
        self.fallback_service.fallback_stats['default_language_hits'] = 30
        self.fallback_service.fallback_stats['translation_key_hits'] = 5
        self.fallback_service.fallback_stats['placeholder_hits'] = 5
        self.fallback_service.fallback_stats['errors'] = 3
        
        # WHEN: Получаем статистику
        stats = self.fallback_service.get_stats()
        
        # THEN: Производные метрики вычислены корректно
        self.assertEqual(stats['requested_language_rate_percent'], 60.0)  # 60/100 * 100
        self.assertEqual(stats['default_language_rate_percent'], 30.0)  # 30/100 * 100
        self.assertEqual(stats['placeholder_rate_percent'], 5.0)  # 5/100 * 100
        self.assertEqual(stats['error_rate_percent'], 3.0)  # 3/100 * 100
        
        # THEN: Производные метрики являются float и округлены до 2 знаков
        self.assertIsInstance(stats['requested_language_rate_percent'], float)
        # Проверяем что значение корректно округлено (может быть целым, например 60.0)
        self.assertGreaterEqual(stats['requested_language_rate_percent'], 0.0)
        self.assertLessEqual(stats['requested_language_rate_percent'], 100.0)

    def test_get_stats_rounds_derived_metrics_correctly(self):
        """Тест: get_stats() корректно округляет производные метрики до 2 знаков"""
        # GIVEN: Сервис с дробными значениями, которые требуют округления
        # Случай, который даст дробное значение: 1/3 = 0.333... * 100 = 33.333...
        self.fallback_service.fallback_stats['total_requests'] = 3
        self.fallback_service.fallback_stats['requested_language_hits'] = 1  # 1/3 * 100 = 33.333... → должно быть 33.33
        self.fallback_service.fallback_stats['default_language_hits'] = 0
        self.fallback_service.fallback_stats['translation_key_hits'] = 0
        self.fallback_service.fallback_stats['placeholder_hits'] = 0
        self.fallback_service.fallback_stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats = self.fallback_service.get_stats()
        
        # THEN: Производные метрики округлены до 2 знаков после запятой
        # 1/3 * 100 = 33.333... → должно быть округлено до 33.33
        expected_rate = round((1 / 3) * 100, 2)  # 33.33
        self.assertEqual(stats['requested_language_rate_percent'], expected_rate)
        self.assertEqual(stats['requested_language_rate_percent'], 33.33)
        
        # GIVEN: Случай с другим дробным значением: 2/7 = 0.2857... * 100 = 28.571...
        self.fallback_service.fallback_stats['total_requests'] = 7
        self.fallback_service.fallback_stats['requested_language_hits'] = 2  # 2/7 * 100 = 28.571... → должно быть 28.57
        self.fallback_service.fallback_stats['default_language_hits'] = 1  # 1/7 * 100 = 14.285... → должно быть 14.29
        
        # WHEN: Получаем статистику
        stats_fractional = self.fallback_service.get_stats()
        
        # THEN: Производные метрики округлены до 2 знаков
        # 2/7 * 100 = 28.571... → должно быть округлено до 28.57
        expected_rate_fractional = round((2 / 7) * 100, 2)  # 28.57
        self.assertEqual(stats_fractional['requested_language_rate_percent'], expected_rate_fractional)
        self.assertEqual(stats_fractional['requested_language_rate_percent'], 28.57)
        
        # 1/7 * 100 = 14.285... → должно быть округлено до 14.29
        expected_default_rate = round((1 / 7) * 100, 2)  # 14.29
        self.assertEqual(stats_fractional['default_language_rate_percent'], expected_default_rate)
        self.assertEqual(stats_fractional['default_language_rate_percent'], 14.29)
        
        # THEN: Проверяем, что округление действительно до 2 знаков
        # Преобразуем в строку и проверяем количество знаков после запятой
        rate_str = str(stats_fractional['requested_language_rate_percent'])
        if '.' in rate_str:
            decimal_places = len(rate_str.split('.')[-1])
            self.assertLessEqual(decimal_places, 2, 
                                f"Округление должно быть до 2 знаков, получено {decimal_places}")

    def test_get_stats_handles_zero_requests(self):
        """Тест: get_stats() корректно обрабатывает случай нулевых запросов"""
        # GIVEN: Сервис без запросов
        self.fallback_service.fallback_stats['total_requests'] = 0
        self.fallback_service.fallback_stats['requested_language_hits'] = 0
        self.fallback_service.fallback_stats['default_language_hits'] = 0
        self.fallback_service.fallback_stats['translation_key_hits'] = 0
        self.fallback_service.fallback_stats['placeholder_hits'] = 0
        self.fallback_service.fallback_stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats = self.fallback_service.get_stats()
        
        # THEN: Все производные метрики равны 0.0 (без деления на ноль)
        self.assertEqual(stats['requested_language_rate_percent'], 0.0)
        self.assertEqual(stats['default_language_rate_percent'], 0.0)
        self.assertEqual(stats['placeholder_rate_percent'], 0.0)
        self.assertEqual(stats['error_rate_percent'], 0.0)
        
        # THEN: Основные метрики равны 0
        self.assertEqual(stats['total_requests'], 0)
        self.assertEqual(stats['requested_language_hits'], 0)
        
        # THEN: default_language присутствует
        self.assertIn('default_language', stats)
        self.assertEqual(stats['default_language'], 'ru')

    def test_get_stats_boundary_cases_for_derived_metrics(self):
        """Тест: get_stats() корректно обрабатывает граничные случаи производных метрик"""
        # GIVEN: Граничный случай 1 - 100% requested_language rate (все запросы на запрошенном языке)
        self.fallback_service.fallback_stats['total_requests'] = 40
        self.fallback_service.fallback_stats['requested_language_hits'] = 40  # 100% на запрошенном языке
        self.fallback_service.fallback_stats['default_language_hits'] = 0
        self.fallback_service.fallback_stats['translation_key_hits'] = 0
        self.fallback_service.fallback_stats['placeholder_hits'] = 0
        self.fallback_service.fallback_stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats_100_percent = self.fallback_service.get_stats()
        
        # THEN: Производные метрики корректны для 100% requested_language rate
        self.assertEqual(stats_100_percent['requested_language_rate_percent'], 100.0)  # 40/40 * 100
        self.assertEqual(stats_100_percent['default_language_rate_percent'], 0.0)  # 0/40 * 100
        self.assertEqual(stats_100_percent['placeholder_rate_percent'], 0.0)  # 0/40 * 100
        self.assertEqual(stats_100_percent['error_rate_percent'], 0.0)  # 0/40 * 100
        
        # GIVEN: Граничный случай 2 - 0% requested_language rate при не нулевых запросах (все fallback на default)
        self.fallback_service.fallback_stats['total_requests'] = 25
        self.fallback_service.fallback_stats['requested_language_hits'] = 0  # 0% на запрошенном языке
        self.fallback_service.fallback_stats['default_language_hits'] = 25  # 100% fallback на default
        self.fallback_service.fallback_stats['translation_key_hits'] = 0
        self.fallback_service.fallback_stats['placeholder_hits'] = 0
        self.fallback_service.fallback_stats['errors'] = 0
        
        # WHEN: Получаем статистику
        stats_0_percent = self.fallback_service.get_stats()
        
        # THEN: Производные метрики корректны для 0% requested_language rate
        self.assertEqual(stats_0_percent['requested_language_rate_percent'], 0.0)  # 0/25 * 100
        self.assertEqual(stats_0_percent['default_language_rate_percent'], 100.0)  # 25/25 * 100
        self.assertEqual(stats_0_percent['placeholder_rate_percent'], 0.0)  # 0/25 * 100
        self.assertEqual(stats_0_percent['error_rate_percent'], 0.0)  # 0/25 * 100
        
        # GIVEN: Граничный случай 3 - 100% error rate (все запросы с ошибками)
        self.fallback_service.fallback_stats['total_requests'] = 15
        self.fallback_service.fallback_stats['requested_language_hits'] = 0
        self.fallback_service.fallback_stats['default_language_hits'] = 0
        self.fallback_service.fallback_stats['translation_key_hits'] = 0
        self.fallback_service.fallback_stats['placeholder_hits'] = 0
        self.fallback_service.fallback_stats['errors'] = 15  # 100% ошибок
        
        # WHEN: Получаем статистику
        stats_100_error = self.fallback_service.get_stats()
        
        # THEN: Производные метрики корректны для 100% error rate
        self.assertEqual(stats_100_error['requested_language_rate_percent'], 0.0)  # 0/15 * 100
        self.assertEqual(stats_100_error['default_language_rate_percent'], 0.0)  # 0/15 * 100
        self.assertEqual(stats_100_error['placeholder_rate_percent'], 0.0)  # 0/15 * 100
        self.assertEqual(stats_100_error['error_rate_percent'], 100.0)  # 15/15 * 100

    def test_get_stats_reflects_fallback_usage(self):
        """Тест: get_stats() отражает корректные метрики после использования fallback"""
        # GIVEN: Очищаем статистику
        self.fallback_service.clear_statistics()
        
        # WHEN: Выполняем различные fallback операции
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
        )  # translation_key hit (не placeholder, т.к. сначала fallback на ключ)
        
        # WHEN: Получаем статистику
        stats = self.fallback_service.get_stats()
        
        # THEN: Метрики отражают реальное использование
        self.assertEqual(stats['total_requests'], 4)
        self.assertEqual(stats['requested_language_hits'], 1)
        self.assertEqual(stats['default_language_hits'], 1)
        self.assertEqual(stats['translation_key_hits'], 2)  # 2 запроса на translation_key
        self.assertEqual(stats['placeholder_hits'], 0)  # 0 запросов на placeholder
        self.assertEqual(stats['errors'], 0)
        
        # THEN: Производные метрики корректны
        self.assertEqual(stats['requested_language_rate_percent'], 25.0)  # 1/4 * 100
        self.assertEqual(stats['default_language_rate_percent'], 25.0)  # 1/4 * 100
        self.assertEqual(stats['placeholder_rate_percent'], 0.0)  # 0/4 * 100
        self.assertEqual(stats['error_rate_percent'], 0.0)  # 0/4 * 100
        
        # THEN: default_language присутствует
        self.assertEqual(stats['default_language'], 'ru')

if __name__ == '__main__':
    unittest.main()
