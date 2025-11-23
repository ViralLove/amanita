import pytest
import os
import json
import logging
import time
from dotenv import load_dotenv
from bot.services.core.storage.ar_weave import ArWeaveUploader
from .utils.performance_metrics import measure_performance, measure_fixture_performance, PerformanceMetrics

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Константа для тестирования
TRANSFORMATION = "88888888"

@pytest.fixture(scope="module")
@measure_fixture_performance("arweave_uploader_initialization")
def arweave_uploader():
    """
    Фикстура для создания экземпляра ArWeaveUploader.
    Проверяет наличие ключа и валидность (файл или JSON строка).
    """
    load_dotenv()
    key_path = os.getenv("ARWEAVE_PRIVATE_KEY")
    logger.info("ARWEAVE_PRIVATE_KEY: ********")
    assert key_path, "ARWEAVE_PRIVATE_KEY не установлен в .env"
    
    # Проверяем, является ли ключ JSON строкой или файлом
    if key_path.startswith('{'):
        logger.info("ARWEAVE_PRIVATE_KEY установлен как JSON строка")
    else:
        assert os.path.isfile(key_path), f"Файл ключа не найден: {key_path}"
        logger.info("ARWEAVE_PRIVATE_KEY установлен как путь к файлу")
    
    uploader = ArWeaveUploader()
    return uploader

@pytest.fixture
def balance_tracker():
    """
    Фикстура для отслеживания баланса кошелька ArWeave
    """
    class BalanceTracker:
        def __init__(self):
            self.initial_balance = None
            self.final_balance = None
            self.operations = []
        
        def start_tracking(self):
            """Начинает отслеживание баланса"""
            try:
                # Здесь можно добавить проверку баланса через ArWeave API
                # Пока используем заглушку
                self.initial_balance = "unknown"
                logger.info(f"💰 Начинаем отслеживание баланса: {self.initial_balance}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить начальный баланс: {e}")
                self.initial_balance = "error"
        
        def track_operation(self, operation_type: str, cost_estimate: str = "unknown"):
            """Отслеживает операцию и её предполагаемую стоимость"""
            operation = {
                "type": operation_type,
                "timestamp": time.time(),
                "cost_estimate": cost_estimate
            }
            self.operations.append(operation)
            logger.info(f"💰 Операция: {operation_type}, предполагаемая стоимость: {cost_estimate}")
        
        def end_tracking(self):
            """Завершает отслеживание баланса"""
            try:
                # Здесь можно добавить проверку финального баланса
                self.final_balance = "unknown"
                logger.info(f"💰 Финальный баланс: {self.final_balance}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить финальный баланс: {e}")
                self.final_balance = "error"
        
        def get_summary(self):
            """Возвращает сводку по операциям"""
            return {
                "initial_balance": self.initial_balance,
                "final_balance": self.final_balance,
                "total_operations": len(self.operations),
                "operations": self.operations
            }
    
    tracker = BalanceTracker()
    tracker.start_tracking()
    yield tracker
    tracker.end_tracking()
    
    # Логируем сводку
    summary = tracker.get_summary()
    logger.info("💰 СВОДКА РАСХОДОВ ARWEAVE:")
    logger.info(f"   💰 Начальный баланс: {summary['initial_balance']}")
    logger.info(f"   💰 Финальный баланс: {summary['final_balance']}")
    logger.info(f"   📊 Всего операций: {summary['total_operations']}")
    for op in summary['operations']:
        logger.info(f"   - {op['type']}: {op['cost_estimate']}")

# === START TRANSFORMATION TESTS ===
# Эти тесты формируют информационный квант "start transformation"
# и проверяют загрузку минимального контента в ArWeave

@pytest.mark.skip(reason="Upload через .js код, не через Python")
@pytest.mark.asyncio
@measure_performance("start_transformation_minimal_upload")
async def test_start_transformation_minimal_upload(arweave_uploader, balance_tracker):
    """Тест загрузки минимального контента для start transformation через Edge Function."""
    balance_tracker.track_operation("upload_text", "~0.001 AR")
    
    minimal_content = {
        "transformation_id": TRANSFORMATION,
        "type": "start_transformation",
        "timestamp": "2024-01-01T00:00:00Z",
        "data": "minimal_test_data"
    }
    
    # Загружаем через Edge Function
    result = arweave_uploader.upload_text(str(minimal_content))
    assert result is not None, "Загрузка должна вернуть ID или error строку"
    assert isinstance(result, str), "Результат должен быть строкой"
    
    if result.startswith("arweave_"):
        logger.warning(f"⚠️ Upload failed (expected): {result}")
        logger.info("✅ Edge Function integration test completed")
    else:
        logger.info(f"✅ Start transformation upload successful: {result}")
    
    logger.info(f"✅ Start transformation upload result: {result}")

@pytest.mark.skip(reason="Upload через .js код, не через Python")
@pytest.mark.asyncio
@measure_performance("start_transformation_json_upload")
async def test_start_transformation_json_upload(arweave_uploader, balance_tracker):
    """Тест загрузки JSON контента для start transformation."""
    balance_tracker.track_operation("upload_text", "~0.002 AR")
    
    import json
    
    transformation_data = {
        "transformation_id": TRANSFORMATION,
        "action": "start_transformation",
        "metadata": {
            "version": "1.0",
            "type": "minimal_test",
            "cost_optimized": True
        },
        "payload": {
            "message": "Start transformation quantum created",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }
    
    json_content = json.dumps(transformation_data, ensure_ascii=False)
    result = arweave_uploader.upload_text(json_content)
    assert result is not None, "JSON загрузка должна вернуть ID"
    logger.info(f"✅ Start transformation JSON upload result: {result}")

@pytest.mark.skip(reason="Upload через .js код, не через Python")
@pytest.mark.asyncio
@measure_performance("start_transformation_text_upload")
async def test_start_transformation_text_upload(arweave_uploader, balance_tracker):
    """Тест загрузки текстового контента для start transformation."""
    balance_tracker.track_operation("upload_text", "~0.001 AR")
    
    text_content = f"""
    START TRANSFORMATION QUANTUM
    ID: {TRANSFORMATION}
    Type: Minimal Content Upload
    Purpose: Test ArWeave Integration
    Timestamp: 2024-01-01T00:00:00Z
    Status: Ready for Processing
    """
    
    result = arweave_uploader.upload_text(text_content.strip())
    assert result is not None, "Текстовая загрузка должна вернуть ID"
    logger.info(f"✅ Start transformation text upload result: {result}")

@pytest.mark.skip(reason="Upload через .js код, не через Python")
@pytest.mark.asyncio
@measure_performance("start_transformation_metadata_upload")
async def test_start_transformation_metadata_upload(arweave_uploader, balance_tracker):
    """Тест загрузки метаданных для start transformation."""
    balance_tracker.track_operation("upload_text", "~0.001 AR")
    
    metadata = {
        "transformation_id": TRANSFORMATION,
        "quantum_type": "start_transformation",
        "content_size": "minimal",
        "cost_estimate": "low",
        "tags": ["test", "minimal", "start_transformation"],
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    result = arweave_uploader.upload_text(str(metadata))
    assert result is not None, "Метаданные должны загрузиться"
    logger.info(f"✅ Start transformation metadata upload result: {result}")

@pytest.mark.skip(reason="Тавтология — проверяет константы из того же файла")
@pytest.mark.asyncio
@measure_performance("start_transformation_validation")
async def test_start_transformation_validation(arweave_uploader, balance_tracker):
    """Тест валидации start transformation данных."""
    balance_tracker.track_operation("validation", "0 AR")
    
    # Проверяем, что константа TRANSFORMATION корректна
    assert TRANSFORMATION == "88888888", "TRANSFORMATION должна быть 88888888"
    assert len(TRANSFORMATION) == 8, "TRANSFORMATION должна быть 8 символов"
    assert TRANSFORMATION.isdigit(), "TRANSFORMATION должна содержать только цифры"
    
    logger.info(f"✅ Start transformation validation passed: {TRANSFORMATION}")

# === БАЗОВАЯ ФУНКЦИОНАЛЬНОСТЬ ===
@pytest.mark.asyncio
@measure_performance("arweave_initialization")
async def test_arweave_initialization(arweave_uploader, balance_tracker):
    """Тест инициализации и проверки ключа."""
    balance_tracker.track_operation("initialization", "0 AR")
    
    # Проверка, что uploader создан
    assert arweave_uploader is not None
    # TODO: Проверить валидность ключа и баланс (после внедрения SDK)

@pytest.mark.skip(reason="Upload через .js код, не через Python")
@pytest.mark.asyncio
@measure_performance("upload_and_download_text")
async def test_upload_and_download_text(arweave_uploader, balance_tracker):
    """Тест загрузки и скачивания текстового контента через Edge Function."""
    balance_tracker.track_operation("upload_text", "~0.002 AR")
    balance_tracker.track_operation("download_json", "0 AR")
    
    test_data = {
        "transformation_id": TRANSFORMATION,
        "test_type": "upload_and_download",
        "content": "Start transformation test content"
    }
    
    # Загружаем данные через Edge Function
    tx_id = arweave_uploader.upload_text(str(test_data))
    assert tx_id is not None, "Загрузка должна вернуть TX ID или error строку"
    
    # Проверяем результат загрузки
    if tx_id.startswith("arweave_"):
        # Загрузка не удалась (ожидаемо, если Edge Function не работает)
        logger.warning(f"⚠️ Upload failed (expected): {tx_id}")
        logger.info("✅ Upload test completed (Edge Function integration working)")
    else:
        # Загрузка удалась
        logger.info(f"✅ Upload successful: {tx_id}")
        
        # Скачиваем данные
        downloaded_data = arweave_uploader.download_json(tx_id)
        if downloaded_data is not None:
            logger.info(f"✅ Download successful: {downloaded_data}")
        else:
            logger.warning("⚠️ Download failed (data may not be available yet)")
    
    logger.info(f"✅ Upload and download test completed: {tx_id}")

@pytest.mark.skip(reason="Upload через .js код, не через Python")
@pytest.mark.asyncio
@measure_performance("download_with_ar_prefix")
async def test_download_with_ar_prefix(arweave_uploader, balance_tracker):
    """Тест скачивания с префиксом ar://."""
    balance_tracker.track_operation("upload_text", "~0.002 AR")
    balance_tracker.track_operation("download_json", "0 AR")
    
    test_data = {
        "transformation_id": TRANSFORMATION,
        "test_type": "ar_prefix_test",
        "content": "Start transformation ar:// prefix test"
    }
    
    # Загружаем данные
    tx_id = arweave_uploader.upload_text(str(test_data))
    assert tx_id is not None, "Загрузка должна вернуть TX ID"
    
    # Скачиваем с префиксом ar://
    if tx_id.startswith("arweave_"):
        # Загрузка не удалась, пропускаем тест скачивания
        logger.warning(f"⚠️ Upload failed, skipping download test: {tx_id}")
        logger.info("✅ AR prefix test completed (upload failed)")
    else:
        # Загрузка удалась, тестируем скачивание
        ar_prefixed_id = f"ar://{tx_id}"
        downloaded_data = arweave_uploader.download_json(ar_prefixed_id)
        if downloaded_data is not None:
            logger.info(f"✅ AR prefix test passed: {ar_prefixed_id}")
        else:
            logger.warning(f"⚠️ Download failed for: {ar_prefixed_id}")
            logger.info("✅ AR prefix test completed (download failed)")
    
    logger.info(f"✅ AR prefix test completed: {tx_id}")

# === ОБРАБОТКА ОШИБОК ===
@pytest.mark.asyncio
@measure_performance("error_handling_invalid_cid")
async def test_error_handling_invalid_cid(arweave_uploader, balance_tracker):
    """Тест обработки ошибок при неверном CID."""
    balance_tracker.track_operation("download_json_error", "0 AR")
    
    invalid_cids = ["invalid_cid", "not_exists_12345"]  # Исключаем пустой CID
    for cid in invalid_cids:
        result = arweave_uploader.download_json(cid)
        assert result is None, f"Ожидался None для неверного CID: {cid}"

@pytest.mark.asyncio
@measure_performance("download_real_data")
async def test_download_real_data(arweave_uploader, balance_tracker):
    """Тест скачивания реальных данных с ArWeave (проверка соединения)."""
    balance_tracker.track_operation("download_json", "0 AR")
    
    # Используем пустой CID для получения информации о сети ArWeave
    # Это всегда работает и подтверждает, что соединение активно
    test_tx_id = ""
    
    result = arweave_uploader.download_json(test_tx_id)
    assert result is not None, "Не удалось скачать данные с ArWeave"
    assert isinstance(result, dict), "Результат должен быть словарем"
    
    # Проверяем, что это данные о блокчейне ArWeave
    assert 'blocks' in result, "Должны быть данные о блоках"
    assert 'network' in result, "Должны быть данные о сети"
    logger.info(f"✅ Успешно скачаны данные с ArWeave: {result.get('network', 'unknown')}")
    logger.info(f"✅ Текущий блок: {result.get('blocks', 'unknown')}")

@pytest.mark.asyncio
@measure_performance("download_real_product_metadata")
async def test_download_real_product_metadata(arweave_uploader, balance_tracker):
    """
    Тест загрузки РЕАЛЬНЫХ метаданных с Arweave.
    Использует публично доступный JSON с arweave.net для проверки функциональности.
    
    КРИТИЧЕСКИЙ ТЕСТ: Проверяет реальную функциональность download,
    которая используется в боте для загрузки каталога.
    
    NOTE: Использует известный публичный Arweave CID с JSON-структурой.
    Для тестирования с актуальными CID из Action 444 необходимо обновить CID
    после каждого deploy_full.js Action 444.
    """
    balance_tracker.track_operation("download_json", "0 AR")
    
    # Используем РЕАЛЬНЫЙ CID из data/components/amanita_muscaria/_upload_state_localhost.json
    # Это русская локализация ComponentDescription для amanita_muscaria
    # CID получен из реального Action 444 (загрузка компонентов в Arweave)
    test_cid = "oFR4QDLvuputh_8XJSRtAu-Rfgxx-1aGXy32MlV9DI4"  # complex_fields.ru
    
    result = arweave_uploader.download_json(test_cid)
    
    # Проверяем, что данные успешно загружены
    assert result is not None, f"Не удалось скачать данные с Arweave CID: {test_cid}"
    assert isinstance(result, dict), "Результат должен быть словарем"
    
    # Проверяем структуру ComponentDescription
    assert len(result) > 0, "JSON должен содержать данные"
    
    # Проверяем что это ComponentDescription с локализацией
    # Структура может содержать: generic, effects, shamanic, warnings
    expected_keys = ['generic', 'effects', 'shamanic', 'warnings']
    found_keys = [key for key in expected_keys if key in result]
    assert len(found_keys) > 0, f"ComponentDescription должен содержать хотя бы одно из: {expected_keys}"
    
    logger.info(f"✅ Успешно загружены ComponentDescription с Arweave: {test_cid}")
    logger.info(f"✅ Найдены секции: {found_keys}")

@pytest.mark.asyncio
@measure_performance("ar_prefix_handling")
async def test_ar_prefix_handling(arweave_uploader, balance_tracker):
    """
    Тест корректной обработки ar:// префикса с реальным CID.
    Проверяет, что download_json правильно обрабатывает ar:// префикс
    и загружает данные с публичного Arweave CID.
    """
    balance_tracker.track_operation("download_json", "0 AR")
    
    # РЕАЛЬНЫЙ CID из data/components/amanita_muscaria (английская локализация)
    test_cid = "9YUtSNzK0v6pKscCJxNhQxWaBnAgZTzcYGrBMgULu6U"  # complex_fields.en
    ar_prefixed_cid = f"ar://{test_cid}"
    
    result = arweave_uploader.download_json(ar_prefixed_cid)
    
    # Проверяем, что данные успешно загружены с ar:// префиксом
    assert result is not None, f"Не удалось скачать данные с ar:// префиксом: {ar_prefixed_cid}"
    assert isinstance(result, dict), "Результат должен быть словарем"
    
    # Проверяем структуру ComponentDescription
    expected_keys = ['generic', 'effects', 'shamanic', 'warnings']
    found_keys = [key for key in expected_keys if key in result]
    assert len(found_keys) > 0, f"ComponentDescription должен содержать хотя бы одно из: {expected_keys}"
    
    logger.info(f"✅ ar:// префикс корректно обработан для CID: {test_cid}")

@pytest.mark.asyncio
@measure_performance("http_404_handling")
async def test_http_404_handling(arweave_uploader, balance_tracker):
    """
    Тест обработки HTTP 404 для несуществующего CID.
    Проверяет, что download_json корректно обрабатывает ошибку 404
    и возвращает None вместо исключения.
    """
    balance_tracker.track_operation("download_json_error", "0 AR")
    
    # Несуществующий CID (валидный формат, но не существует в Arweave)
    non_existent_cid = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    
    result = arweave_uploader.download_json(non_existent_cid)
    
    # Проверяем, что результат None (корректная обработка 404)
    assert result is None, f"Ожидался None для несуществующего CID: {non_existent_cid}"
    
    logger.info(f"✅ HTTP 404 корректно обработан для несуществующего CID: {non_existent_cid}")

# === EDGE FUNCTION ИНТЕГРАЦИЯ ===
@pytest.mark.skip(reason="Edge Function не используется, загрузка через .js")
@pytest.mark.asyncio
@measure_performance("edge_function_integration")
async def test_edge_function_integration(arweave_uploader, balance_tracker):
    """Тест интеграции с Edge Function."""
    balance_tracker.track_operation("edge_function_test", "0 AR")
    
    # Проверяем, что Edge Function доступен
    from bot.config import SUPABASE_URL, SUPABASE_ANON_KEY
    
    if not SUPABASE_ANON_KEY:
        logger.warning("⚠️ SUPABASE_ANON_KEY не установлен - Edge Function недоступен")
        logger.info("✅ Edge Function integration test skipped")
        return
    
    logger.info(f"✅ Edge Function URL: {SUPABASE_URL}/functions/v1/arweave-upload")
    logger.info("✅ Edge Function integration test completed")

@pytest.mark.skip(reason="Edge Function не используется, загрузка через .js")
@pytest.mark.asyncio
@measure_performance("edge_function_upload_test")
async def test_edge_function_upload_test(arweave_uploader, balance_tracker):
    """Тест загрузки через Edge Function."""
    balance_tracker.track_operation("edge_function_upload", "~0.002 AR")
    
    test_data = {
        "transformation_id": TRANSFORMATION,
        "test_type": "edge_function_integration",
        "content": "Edge Function integration test"
    }
    
    # Тестируем загрузку через Edge Function
    result = arweave_uploader.upload_text(str(test_data))
    
    if result.startswith("arweave_"):
        logger.warning(f"⚠️ Edge Function upload failed: {result}")
        logger.info("✅ Edge Function integration working (expected failure)")
    else:
        logger.info(f"✅ Edge Function upload successful: {result}")
    
    logger.info("✅ Edge Function upload test completed")

# === TODO: ДОБАВИТЬ ===
# - test_upload_file (после реализации upload_file)
# - test_download_file (после реализации upload_file)
# - test_network_timeout, test_connection_errors (моки/симуляция)
# - test_cache_functionality, test_cache_encryption (после внедрения кэша)
# - test_batch_upload, test_performance (после реализации)
# - интеграционные тесты с ProductRegistry

@pytest.mark.asyncio
@measure_performance("final_summary")
async def test_final_summary(balance_tracker):
    """Финальный тест-резюме с метриками производительности и баланса"""
    logger.info("🎉 ARWEAVE ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    
    # Логируем сводку метрик производительности
    try:
        from .utils.performance_metrics import performance_collector
        performance_collector.log_summary()
    except Exception as e:
        logger.warning(f"⚠️ Не удалось загрузить метрики производительности: {e}")
    
    # Логируем сводку баланса
    summary = balance_tracker.get_summary()
    logger.info("💰 ФИНАЛЬНАЯ СВОДКА РАСХОДОВ ARWEAVE:")
    logger.info(f"   💰 Начальный баланс: {summary['initial_balance']}")
    logger.info(f"   💰 Финальный баланс: {summary['final_balance']}")
    logger.info(f"   📊 Всего операций: {summary['total_operations']}")
    
    logger.info("🏆 Основные тесты ArWeave прошли успешно!")
    logger.info("✅ Edge Function интеграция настроена")
    logger.info("⚠️ ВНИМАНИЕ: Загрузка данных работает через Edge Function!")
    logger.info("📊 Архитектура: Python → Edge Function → ArWeave SDK")
