"""
Тесты для TranslationCacheService

Проверяет многоуровневое кэширование переводов:
- Memory Cache
- File Cache  
- IPFS Cache (заглушка)
- TTL и истечение кэша
- Статистика и производительность
"""

import unittest
import tempfile
import shutil
import time
import json
import sys
import os
from pathlib import Path

# Добавляем путь к модулям проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
bot_dir = os.path.join(current_dir, '..')
sys.path.insert(0, os.path.abspath(bot_dir))

from services.common.translation_cache_service import TranslationCacheService, CacheEntry

class TestTranslationCacheService(unittest.TestCase):
    """Тесты для TranslationCacheService"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_service = TranslationCacheService(
            cache_dir=self.temp_dir,
            default_ttl=1  # 1 секунда для быстрого тестирования
        )
    
    def tearDown(self):
        """Очистка тестового окружения"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_memory_cache_basic_operations(self):
        """Тест: Базовые операции с memory cache"""
        # Сохранение и получение
        self.cache_service.set("test_key", "test_value", "interface")
        result = self.cache_service.get("test_key", "interface")
        self.assertEqual(result, "test_value")
        
        # Проверка статистики
        stats = self.cache_service.get_stats()
        self.assertEqual(stats['memory_hits'], 1)
        self.assertEqual(stats['total_requests'], 1)
        self.assertEqual(stats['hit_rate_percent'], 100.0)
    
    def test_file_cache_persistence(self):
        """Тест: Персистентность file cache"""
        # Сохраняем данные
        self.cache_service.set("persistent_key", {"data": "persistent_value"}, "product")
        
        # Создаём новый экземпляр сервиса (имитируем перезапуск)
        new_cache_service = TranslationCacheService(
            cache_dir=self.temp_dir,
            default_ttl=1
        )
        
        # Проверяем, что данные сохранились
        result = new_cache_service.get("persistent_key", "product")
        self.assertEqual(result, {"data": "persistent_value"})
        
        # Проверяем, что данные попали в memory cache
        stats = new_cache_service.get_stats()
        self.assertEqual(stats['file_hits'], 1)
    
    def test_ttl_expiration(self):
        """Тест: Истечение TTL кэша"""
        # Сохраняем с коротким TTL
        self.cache_service.set("expire_key", "expire_value", "interface", ttl=1)
        
        # Проверяем, что данные доступны
        result = self.cache_service.get("expire_key", "interface")
        self.assertEqual(result, "expire_value")
        
        # Ждём истечения TTL
        time.sleep(1.1)
        
        # Проверяем, что данные истекли
        result = self.cache_service.get("expire_key", "interface")
        self.assertIsNone(result)
        
        # Проверяем статистику
        stats = self.cache_service.get_stats()
        self.assertEqual(stats['misses'], 1)
    
    def test_cache_invalidation(self):
        """Тест: Инвалидация кэша"""
        # Сохраняем данные
        self.cache_service.set("invalidate_key", "invalidate_value", "component")
        
        # Проверяем, что данные доступны
        result = self.cache_service.get("invalidate_key", "component")
        self.assertEqual(result, "invalidate_value")
        
        # Инвалидируем кэш
        self.cache_service.invalidate("invalidate_key", "component")
        
        # Проверяем, что данные удалены
        result = self.cache_service.get("invalidate_key", "component")
        self.assertIsNone(result)
    
    def test_cache_clear(self):
        """Тест: Очистка кэша"""
        # Сохраняем данные разных типов
        self.cache_service.set("key1", "value1", "interface")
        self.cache_service.set("key2", "value2", "product")
        self.cache_service.set("key3", "value3", "component")
        
        # Проверяем, что данные доступны
        self.assertEqual(self.cache_service.get("key1", "interface"), "value1")
        self.assertEqual(self.cache_service.get("key2", "product"), "value2")
        self.assertEqual(self.cache_service.get("key3", "component"), "value3")
        
        # Очищаем кэш типа "product"
        self.cache_service.clear_cache("product")
        
        # Проверяем, что данные product удалены, а остальные остались
        self.assertEqual(self.cache_service.get("key1", "interface"), "value1")
        self.assertIsNone(self.cache_service.get("key2", "product"))
        self.assertEqual(self.cache_service.get("key3", "component"), "value3")
        
        # Очищаем весь кэш
        self.cache_service.clear_cache()
        
        # Проверяем, что все данные удалены
        self.assertIsNone(self.cache_service.get("key1", "interface"))
        self.assertIsNone(self.cache_service.get("key3", "component"))
    
    def test_cache_hierarchy(self):
        """Тест: Иерархия кэширования (memory -> file -> ipfs)"""
        # Сохраняем данные
        self.cache_service.set("hierarchy_key", "hierarchy_value", "product")
        
        # Первый запрос - должен попасть в memory cache
        result1 = self.cache_service.get("hierarchy_key", "product")
        self.assertEqual(result1, "hierarchy_value")
        
        # Создаём новый экземпляр (очищаем memory cache)
        new_cache_service = TranslationCacheService(
            cache_dir=self.temp_dir,
            default_ttl=1
        )
        
        # Второй запрос - должен попасть в file cache
        result2 = new_cache_service.get("hierarchy_key", "product")
        self.assertEqual(result2, "hierarchy_value")
        
        # Проверяем статистику
        stats = new_cache_service.get_stats()
        self.assertEqual(stats['file_hits'], 1)
        self.assertEqual(stats['memory_hits'], 0)  # Memory cache пуст
    
    def test_different_cache_types(self):
        """Тест: Разные типы кэша с разными TTL"""
        # Сохраняем данные разных типов
        self.cache_service.set("interface_key", "interface_value", "interface")
        self.cache_service.set("product_key", "product_value", "product")
        self.cache_service.set("component_key", "component_value", "component")
        self.cache_service.set("fallback_key", "fallback_value", "fallback")
        
        # Проверяем, что все данные доступны
        self.assertEqual(self.cache_service.get("interface_key", "interface"), "interface_value")
        self.assertEqual(self.cache_service.get("product_key", "product"), "product_value")
        self.assertEqual(self.cache_service.get("component_key", "component"), "component_value")
        self.assertEqual(self.cache_service.get("fallback_key", "fallback"), "fallback_value")
        
        # Проверяем статистику
        stats = self.cache_service.get_stats()
        self.assertEqual(stats['total_requests'], 4)
        self.assertEqual(stats['memory_hits'], 4)
    
    def test_cache_entry_creation(self):
        """Тест: Создание записей кэша"""
        # Создаём запись кэша
        entry = CacheEntry(
            data="test_data",
            timestamp=time.time(),
            ttl=3600,
            source="memory"
        )
        
        # Проверяем свойства
        self.assertEqual(entry.data, "test_data")
        self.assertFalse(entry.is_expired())
        
        # Проверяем истечение
        expired_entry = CacheEntry(
            data="expired_data",
            timestamp=time.time() - 3601,  # 1 час назад
            ttl=3600,  # TTL 1 час
            source="memory"
        )
        self.assertTrue(expired_entry.is_expired())
    
    def test_performance_requirements(self):
        """Тест: Требования к производительности"""
        # Тестируем производительность memory cache
        start_time = time.time()
        
        # Сохраняем 100 записей
        for i in range(100):
            self.cache_service.set(f"perf_key_{i}", f"perf_value_{i}", "interface")
        
        # Читаем 100 записей
        for i in range(100):
            result = self.cache_service.get(f"perf_key_{i}", "interface")
            self.assertEqual(result, f"perf_value_{i}")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Проверяем, что выполнение заняло менее 1 секунды
        self.assertLess(execution_time, 1.0)
        
        # Проверяем статистику
        stats = self.cache_service.get_stats()
        self.assertEqual(stats['total_requests'], 100)
        self.assertEqual(stats['memory_hits'], 100)
        self.assertEqual(stats['hit_rate_percent'], 100.0)
    
    def test_error_handling(self):
        """Тест: Обработка ошибок"""
        # Тестируем с некорректными параметрами
        result = self.cache_service.get("", "interface")
        self.assertIsNone(result)
        
        result = self.cache_service.get("key", "")
        self.assertIsNone(result)
        
        # Тестируем инвалидацию несуществующего ключа
        success = self.cache_service.invalidate("nonexistent_key", "interface")
        self.assertTrue(success)  # Должно работать без ошибок
        
        # Тестируем очистку несуществующего типа
        success = self.cache_service.clear_cache("nonexistent_type")
        self.assertTrue(success)  # Должно работать без ошибок
    
    def test_file_cache_corruption_handling(self):
        """Тест: Обработка повреждённого файлового кэша"""
        # Создаём повреждённый JSON файл
        corrupted_file = Path(self.temp_dir) / "translations.json"
        with open(corrupted_file, 'w') as f:
            f.write("invalid json content")
        
        # Создаём новый сервис - должен обработать ошибку корректно
        new_cache_service = TranslationCacheService(
            cache_dir=self.temp_dir,
            default_ttl=1
        )
        
        # Проверяем, что сервис работает
        result = new_cache_service.get("test_key", "interface")
        self.assertIsNone(result)  # Должно вернуть None без ошибки
    
    def test_cache_stats_accuracy(self):
        """Тест: Точность статистики кэша"""
        # Очищаем статистику
        self.cache_service.clear_cache()
        
        # Выполняем операции
        self.cache_service.set("key1", "value1", "interface")
        self.cache_service.set("key2", "value2", "product")
        
        # Memory hits
        self.cache_service.get("key1", "interface")
        self.cache_service.get("key2", "product")
        
        # Misses
        self.cache_service.get("nonexistent", "interface")
        self.cache_service.get("nonexistent2", "product")
        
        # Проверяем статистику
        stats = self.cache_service.get_stats()
        self.assertEqual(stats['memory_hits'], 2)
        self.assertEqual(stats['misses'], 2)
        self.assertEqual(stats['total_requests'], 4)
        self.assertEqual(stats['hit_rate_percent'], 50.0)
        self.assertEqual(stats['memory_cache_size'], 2)

if __name__ == '__main__':
    unittest.main()
