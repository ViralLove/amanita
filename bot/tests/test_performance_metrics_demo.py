"""
Демонстрация метрик производительности для тестов
"""

import pytest
import time
import logging
from bot.tests.utils.performance_metrics import measure_performance, measure_fixture_performance

logger = logging.getLogger(__name__)

@measure_fixture_performance("demo_fixture")
@pytest.fixture
def demo_fixture():
    """Демонстрационная фикстура с измерением производительности"""
    logger.info("🔧 Инициализация демонстрационной фикстуры")
    time.sleep(0.1)  # Имитация работы
    return {"data": "test_data"}

@pytest.mark.asyncio
@measure_performance("demo_test")
async def test_performance_metrics_demo(demo_fixture):
    """Демонстрационный тест с измерением производительности"""
    logger.info("🧪 Начинаем демонстрационный тест производительности")
    
    # Имитация работы теста
    time.sleep(0.2)
    
    # Проверка фикстуры
    assert demo_fixture["data"] == "test_data"
    
    logger.info("✅ Демонстрационный тест завершен успешно")

@pytest.mark.asyncio
@measure_performance("memory_intensive_test")
async def test_memory_intensive_operation():
    """Тест с интенсивным использованием памяти"""
    logger.info("🧪 Начинаем тест с интенсивным использованием памяти")
    
    # Создаем большой список для имитации использования памяти
    large_list = [i for i in range(100000)]
    
    # Имитация обработки данных
    processed_data = [x * 2 for x in large_list[:1000]]
    
    # Проверка результата
    assert len(processed_data) == 1000
    assert processed_data[0] == 0
    assert processed_data[999] == 1998
    
    logger.info("✅ Тест с интенсивным использованием памяти завершен")

def test_performance_metrics_summary():
    """Финальный тест с выводом сводки метрик"""
    logger.info("📊 ДЕМОНСТРАЦИЯ МЕТРИК ПРОИЗВОДИТЕЛЬНОСТИ")
    
    from tests.utils.performance_metrics import performance_collector
    performance_collector.log_summary()
    
    logger.info("✅ Демонстрация метрик производительности завершена") 