"""
Тесты для CacheManager

Проверяет централизованное управление кэшами:
- Регистрация кэш-сервисов
- Унифицированный API для всех типов кэшей
- Централизованная статистика и мониторинг
- Управление жизненным циклом кэшей
- Конфигурация и настройки
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Добавляем путь к модулям проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
bot_dir = os.path.join(current_dir, '..')
sys.path.insert(0, os.path.abspath(bot_dir))

from services.common.cache_manager import (
    CacheManager, 
    CacheType, 
    CacheStats, 
    CacheConfig
)

class TestCacheManager(unittest.TestCase):
    """Тесты для CacheManager"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.cache_manager = CacheManager()
        
        # Создаём моки кэш-сервисов
        self.mock_translation_service = Mock()
        self.mock_product_service = Mock()
        self.mock_catalog_service = Mock()
        
        # Настраиваем моки
        self.mock_translation_service.get.return_value = "translation_data"
        self.mock_translation_service.set.return_value = True
        self.mock_translation_service.invalidate.return_value = True
        self.mock_translation_service.clear_cache.return_value = True
        self.mock_translation_service.get_stats.return_value = {
            'total_requests': 10,
            'memory_hits': 5,
            'file_hits': 3,
            'ipfs_hits': 1,
            'misses': 1,
            'hit_rate_percent': 90.0,
            'memory_cache_size': 5
        }
        
        # Настраиваем product service с нужными методами
        self.mock_product_service.get_cached_item.return_value = "product_data"
        self.mock_product_service.set_cached_item.return_value = True
        self.mock_product_service.remove_cached_item.return_value = True
        self.mock_product_service.clear_all_cache.return_value = True
        
        # Удаляем стандартные методы, чтобы использовались специфичные
        del self.mock_product_service.get
        del self.mock_product_service.set
        del self.mock_product_service.invalidate
        del self.mock_product_service.clear_cache
        
        self.mock_catalog_service.get.return_value = "catalog_data"
        self.mock_catalog_service.set.return_value = True
        self.mock_catalog_service.invalidate.return_value = True
        self.mock_catalog_service.clear_cache.return_value = True
    
    def test_cache_service_registration(self):
        """Тест: Регистрация кэш-сервисов"""
        # Регистрируем сервисы
        result1 = self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        result2 = self.cache_manager.register_cache_service(CacheType.PRODUCT, self.mock_product_service)
        result3 = self.cache_manager.register_cache_service(CacheType.CATALOG, self.mock_catalog_service)
        
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertTrue(result3)
        
        # Проверяем, что сервисы зарегистрированы
        self.assertIn(CacheType.TRANSLATION, self.cache_manager.cache_services)
        self.assertIn(CacheType.PRODUCT, self.cache_manager.cache_services)
        self.assertIn(CacheType.CATALOG, self.cache_manager.cache_services)
        
        # Проверяем глобальную статистику
        global_stats = self.cache_manager.get_global_stats()
        self.assertEqual(global_stats['cache_services_count'], 3)
    
    def test_get_from_cache(self):
        """Тест: Получение данных из кэша"""
        # Регистрируем сервисы
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        self.cache_manager.register_cache_service(CacheType.PRODUCT, self.mock_product_service)
        
        # Тестируем получение из translation cache
        result1 = self.cache_manager.get("test_key", CacheType.TRANSLATION)
        self.assertEqual(result1, "translation_data")
        self.mock_translation_service.get.assert_called_once_with("test_key")
        
        # Тестируем получение из product cache
        result2 = self.cache_manager.get("product_key", CacheType.PRODUCT)
        self.assertEqual(result2, "product_data")
        self.mock_product_service.get_cached_item.assert_called_once_with("product_key", "product")
    
    def test_set_to_cache(self):
        """Тест: Сохранение данных в кэш"""
        # Регистрируем сервисы
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        self.cache_manager.register_cache_service(CacheType.PRODUCT, self.mock_product_service)
        
        # Тестируем сохранение в translation cache
        result1 = self.cache_manager.set("test_key", "test_data", CacheType.TRANSLATION)
        self.assertTrue(result1)
        self.mock_translation_service.set.assert_called_once_with("test_key", "test_data")
        
        # Тестируем сохранение в product cache
        result2 = self.cache_manager.set("product_key", "product_data", CacheType.PRODUCT)
        self.assertTrue(result2)
        self.mock_product_service.set_cached_item.assert_called_once_with("product_key", "product_data", "product")
    
    def test_invalidate_cache(self):
        """Тест: Инвалидация кэша"""
        # Регистрируем сервисы
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        self.cache_manager.register_cache_service(CacheType.PRODUCT, self.mock_product_service)
        
        # Тестируем инвалидацию translation cache
        result1 = self.cache_manager.invalidate("test_key", CacheType.TRANSLATION)
        self.assertTrue(result1)
        self.mock_translation_service.invalidate.assert_called_once_with("test_key")
        
        # Тестируем инвалидацию product cache
        result2 = self.cache_manager.invalidate("product_key", CacheType.PRODUCT)
        self.assertTrue(result2)
        self.mock_product_service.remove_cached_item.assert_called_once_with("product_key", "product")
    
    def test_clear_cache(self):
        """Тест: Очистка кэша"""
        # Регистрируем сервисы
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        self.cache_manager.register_cache_service(CacheType.PRODUCT, self.mock_product_service)
        
        # Тестируем очистку конкретного кэша
        result1 = self.cache_manager.clear_cache(CacheType.TRANSLATION)
        self.assertTrue(result1)
        self.mock_translation_service.clear_cache.assert_called_once()
        
        # Тестируем очистку всех кэшей
        result2 = self.cache_manager.clear_cache()
        self.assertTrue(result2)
        self.mock_translation_service.clear_cache.assert_called()
        self.mock_product_service.clear_all_cache.assert_called()
    
    def test_cache_statistics(self):
        """Тест: Статистика кэшей"""
        # Регистрируем сервисы
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        self.cache_manager.register_cache_service(CacheType.PRODUCT, self.mock_product_service)
        
        # Выполняем операции для генерации статистики
        self.cache_manager.get("key1", CacheType.TRANSLATION)
        self.cache_manager.get("key2", CacheType.PRODUCT)
        self.cache_manager.get("key3", CacheType.TRANSLATION)
        
        # Получаем статистику одного кэша
        translation_stats = self.cache_manager.get_cache_stats(CacheType.TRANSLATION)
        self.assertIsInstance(translation_stats, CacheStats)
        self.assertEqual(translation_stats.cache_type, CacheType.TRANSLATION)
        self.assertEqual(translation_stats.total_requests, 10)  # Из мока
        self.assertEqual(translation_stats.hits, 9)  # memory_hits + file_hits + ipfs_hits
        self.assertEqual(translation_stats.hit_rate, 90.0)
        
        # Получаем статистику всех кэшей
        all_stats = self.cache_manager.get_cache_stats()
        self.assertIsInstance(all_stats, dict)
        self.assertIn(CacheType.TRANSLATION, all_stats)
        self.assertIn(CacheType.PRODUCT, all_stats)
    
    def test_global_statistics(self):
        """Тест: Глобальная статистика"""
        # Регистрируем сервисы
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        self.cache_manager.register_cache_service(CacheType.PRODUCT, self.mock_product_service)
        
        # Выполняем операции
        self.cache_manager.get("key1", CacheType.TRANSLATION)  # hit
        self.cache_manager.get("key2", CacheType.PRODUCT)      # hit
        # Не добавляем CATALOG, так как он не зарегистрирован
        
        # Получаем глобальную статистику
        global_stats = self.cache_manager.get_global_stats()
        
        self.assertEqual(global_stats['total_requests'], 2)
        self.assertEqual(global_stats['total_hits'], 2)
        self.assertEqual(global_stats['total_misses'], 0)
        self.assertEqual(global_stats['hit_rate_percent'], 100.0)
        self.assertEqual(global_stats['cache_services_count'], 2)
        self.assertIn('translation', global_stats['enabled_caches'])
        self.assertIn('product', global_stats['enabled_caches'])
    
    def test_cache_configuration(self):
        """Тест: Конфигурация кэшей"""
        # Тестируем настройку конфигурации
        result = self.cache_manager.configure_cache(
            CacheType.TRANSLATION,
            ttl=7200,
            max_size=2000,
            enabled=False
        )
        self.assertTrue(result)
        
        # Проверяем, что конфигурация обновилась
        config = self.cache_manager.cache_configs[CacheType.TRANSLATION]
        self.assertEqual(config.ttl, 7200)
        self.assertEqual(config.max_size, 2000)
        self.assertFalse(config.enabled)
    
    def test_enable_disable_cache(self):
        """Тест: Включение/отключение кэшей"""
        # Отключаем кэш
        result1 = self.cache_manager.disable_cache(CacheType.TRANSLATION)
        self.assertTrue(result1)
        
        config = self.cache_manager.cache_configs[CacheType.TRANSLATION]
        self.assertFalse(config.enabled)
        
        # Включаем кэш
        result2 = self.cache_manager.enable_cache(CacheType.TRANSLATION)
        self.assertTrue(result2)
        
        config = self.cache_manager.cache_configs[CacheType.TRANSLATION]
        self.assertTrue(config.enabled)
    
    def test_disabled_cache_operations(self):
        """Тест: Операции с отключённым кэшем"""
        # Отключаем кэш
        self.cache_manager.disable_cache(CacheType.TRANSLATION)
        
        # Регистрируем сервис
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, self.mock_translation_service)
        
        # Пытаемся получить данные из отключённого кэша
        result = self.cache_manager.get("test_key", CacheType.TRANSLATION)
        self.assertIsNone(result)
        
        # Пытаемся сохранить данные в отключённый кэш
        result = self.cache_manager.set("test_key", "test_data", CacheType.TRANSLATION)
        self.assertFalse(result)
    
    def test_cleanup_expired(self):
        """Тест: Очистка истёкших записей"""
        # Создаём мок с методом cleanup_expired
        mock_service = Mock()
        mock_service.cleanup_expired.return_value = 5
        
        # Регистрируем сервис
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, mock_service)
        
        # Очищаем истёкшие записи
        cleaned_count = self.cache_manager.cleanup_expired(CacheType.TRANSLATION)
        self.assertEqual(cleaned_count, 5)
        mock_service.cleanup_expired.assert_called_once()
    
    def test_cleanup_all_expired(self):
        """Тест: Очистка истёкших записей во всех кэшах"""
        # Создаём моки с методами очистки
        mock_service1 = Mock()
        mock_service1.cleanup_expired.return_value = 3
        
        mock_service2 = Mock()
        mock_service2.cleanup_expired.return_value = 2  # Используем только cleanup_expired
        
        # Регистрируем сервисы
        self.cache_manager.register_cache_service(CacheType.TRANSLATION, mock_service1)
        self.cache_manager.register_cache_service(CacheType.PRODUCT, mock_service2)
        
        # Очищаем все кэши
        cleaned_count = self.cache_manager.cleanup_expired()
        self.assertEqual(cleaned_count, 5)  # 3 + 2
        
        mock_service1.cleanup_expired.assert_called_once()
        mock_service2.cleanup_expired.assert_called_once()
    
    def test_error_handling(self):
        """Тест: Обработка ошибок"""
        # Тестируем получение из несуществующего кэша
        result = self.cache_manager.get("key", CacheType.IPFS)
        self.assertIsNone(result)
        
        # Тестируем сохранение в несуществующий кэш
        result = self.cache_manager.set("key", "data", CacheType.IPFS)
        self.assertFalse(result)
        
        # Тестируем инвалидацию несуществующего кэша
        result = self.cache_manager.invalidate("key", CacheType.IPFS)
        self.assertFalse(result)
    
    def test_cache_config_defaults(self):
        """Тест: Конфигурации по умолчанию"""
        # Проверяем, что все типы кэшей имеют конфигурации по умолчанию
        for cache_type in CacheType:
            self.assertIn(cache_type, self.cache_manager.cache_configs)
            
            config = self.cache_manager.cache_configs[cache_type]
            self.assertIsInstance(config, CacheConfig)
            self.assertEqual(config.cache_type, cache_type)
            self.assertTrue(config.enabled)
            self.assertGreater(config.ttl, 0)
            self.assertGreater(config.max_size, 0)
            self.assertGreater(config.cleanup_interval, 0)
            self.assertTrue(config.auto_cleanup)
    
    def test_cache_type_enum(self):
        """Тест: Перечисление типов кэшей"""
        # Проверяем все типы кэшей
        expected_types = [
            'translation', 'product', 'catalog', 
            'ipfs', 'image', 'navigation'
        ]
        
        for cache_type in CacheType:
            self.assertIn(cache_type.value, expected_types)
    
    def test_cache_stats_dataclass(self):
        """Тест: Структура данных CacheStats"""
        stats = CacheStats(
            cache_type=CacheType.TRANSLATION,
            total_requests=100,
            hits=90,
            misses=10,
            hit_rate=90.0,
            size=50,
            memory_usage=1024,
            last_cleanup=datetime.now()
        )
        
        self.assertEqual(stats.cache_type, CacheType.TRANSLATION)
        self.assertEqual(stats.total_requests, 100)
        self.assertEqual(stats.hits, 90)
        self.assertEqual(stats.misses, 10)
        self.assertEqual(stats.hit_rate, 90.0)
        self.assertEqual(stats.size, 50)
        self.assertEqual(stats.memory_usage, 1024)
        self.assertIsInstance(stats.last_cleanup, datetime)
    
    def test_cache_config_dataclass(self):
        """Тест: Структура данных CacheConfig"""
        config = CacheConfig(
            cache_type=CacheType.PRODUCT,
            enabled=True,
            ttl=1800,
            max_size=500,
            cleanup_interval=900,
            auto_cleanup=True
        )
        
        self.assertEqual(config.cache_type, CacheType.PRODUCT)
        self.assertTrue(config.enabled)
        self.assertEqual(config.ttl, 1800)
        self.assertEqual(config.max_size, 500)
        self.assertEqual(config.cleanup_interval, 900)
        self.assertTrue(config.auto_cleanup)

if __name__ == '__main__':
    unittest.main()
