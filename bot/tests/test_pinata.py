import pytest
import logging
import json
import os
from dotenv import load_dotenv
import time
from pathlib import Path
import tempfile
import shutil

from bot.services.pinata import SecurePinataUploader

# Настройка логгера
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

TEST_ID = "88888888"

@pytest.fixture
def pinata_uploader():
    """Фикстура: создаёт экземпляр SecurePinataUploader"""
    logger.info("=" * 50)
    logger.info("🔧 НАЧАЛО ИНИЦИАЛИЗАЦИИ ФИКСТУРЫ pinata_uploader")

    # Проверяем наличие ключей
    assert os.getenv("PINATA_API_KEY"), "PINATA_API_KEY не установлен"
    assert os.getenv("PINATA_API_SECRET"), "PINATA_API_SECRET не установлен"

    uploader = SecurePinataUploader()
    logger.info("✅ SecurePinataUploader создан")

    return uploader

@pytest.fixture
def temp_test_files():
    """Фикстура: создает временные тестовые файлы"""
    temp_dir = tempfile.mkdtemp()
    files = []
    
    try:
        # Создаем текстовый файл
        text_file = Path(temp_dir) / "test.txt"
        with open(text_file, "w") as f:
            f.write(f"Test content {TEST_ID}")
        files.append(text_file)
        
        # Создаем JSON файл
        json_file = Path(temp_dir) / "test.json"
        with open(json_file, "w") as f:
            json.dump({"test_id": TEST_ID}, f)
        files.append(json_file)
        
        yield files
    finally:
        shutil.rmtree(temp_dir)

def test_upload_and_download_text(pinata_uploader):
    """Проверка загрузки и скачивания JSON-данных"""
    logger.info("=" * 50)
    logger.info("🚀 Тест: загрузка и скачивание текста")

    test_data = {
        "test_id": TEST_ID,
        "description": "Test via Pinata"
    }

    try:
        # Загрузка с именем файла
        cid = pinata_uploader.upload_text(test_data, "test_data.json")
        assert cid, "CID не получен"
        logger.info(f"✅ Загружено, CID: {cid}")

        time.sleep(5)  # Увеличиваем время ожидания индексации

        # Скачивание
        downloaded = pinata_uploader.download_json(cid)
        assert downloaded is not None, "Не удалось скачать данные"
        assert downloaded["test_id"] == TEST_ID, "Данные не совпадают"
        
        # Проверка кэша
        cached_info = pinata_uploader.find_file_by_name("test_data.json")
        assert cached_info, "Файл не найден в кэше"
        assert cached_info[0] == cid, "CID в кэше не совпадает"

        logger.info("✅ Проверка пройдена")

    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise

def test_download_with_ipfs_prefix(pinata_uploader):
    """Проверка скачивания с префиксом ipfs://"""
    logger.info("=" * 50)
    logger.info("🚀 Тест: скачивание с префиксом ipfs://")

    test_data = {"test_id": TEST_ID}

    try:
        cid = pinata_uploader.upload_text(test_data)
        assert cid, "CID не получен"
        prefixed_cid = f"ipfs://{cid}"

        time.sleep(5)  # Увеличиваем время ожидания индексации

        result = pinata_uploader.download_json(prefixed_cid)
        assert result is not None, "Не удалось скачать данные"
        assert result["test_id"] == TEST_ID, "Скачивание с префиксом неудачно"

        # Проверка URL
        gateway_url = pinata_uploader.get_gateway_url(prefixed_cid)
        assert gateway_url.startswith("https://"), "Неверный формат gateway URL"
        assert cid in gateway_url, "CID отсутствует в gateway URL"

        logger.info("✅ Тест пройден")

    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise

def test_invalid_cid_handling(pinata_uploader):
    """Проверка обработки ошибок при неправильных CID"""
    logger.info("=" * 50)
    logger.info("🚀 Тест: обработка неверных CID")

    invalid_cids = ["badcid", "notexists123", ""]

    for cid in invalid_cids:
        logger.debug(f"🧪 Тест CID: {cid}")
        result = pinata_uploader.download_json(cid)
        assert result is None, f"Ожидался None для неверного CID: {cid}"
        logger.debug("✅ Правильная обработка ошибки")

    logger.info("✅ Тест завершён")

def test_file_validation(pinata_uploader, temp_test_files):
    """Проверка валидации файлов"""
    logger.info("=" * 50)
    logger.info("🚀 Тест: валидация файлов")
    
    # Проверка существующего файла
    text_file = temp_test_files[0]
    try:
        pinata_uploader.validate_file(str(text_file))
        logger.info("✅ Валидация существующего файла прошла успешно")
    except Exception as e:
        pytest.fail(f"Неожиданная ошибка при валидации: {e}")
    
    # Проверка несуществующего файла
    with pytest.raises(ValueError):
        pinata_uploader.validate_file("nonexistent.file")
        logger.info("✅ Правильная обработка несуществующего файла")

def test_batch_upload(pinata_uploader, temp_test_files):
    """Проверка многопоточной загрузки файлов"""
    logger.info("=" * 50)
    logger.info("🚀 Тест: многопоточная загрузка")
    
    # Подготовка списка файлов
    files = [
        (str(file), f"test_file_{i}.{file.suffix}")
        for i, file in enumerate(temp_test_files)
    ]
    
    try:
        # Загрузка файлов
        results = pinata_uploader.upload_files_batch(files)
        assert len(results) == len(files), "Количество результатов не совпадает"
        
        # Проверка результатов
        for file_name, cid in results.items():
            assert cid is not None, f"Ошибка загрузки {file_name}"
            logger.info(f"✅ Файл {file_name} успешно загружен: {cid}")
            
            # Проверка кэша
            cached_info = pinata_uploader.find_file_by_name(file_name)
            assert cached_info, f"Файл {file_name} не найден в кэше"
            assert cached_info[0] == cid, f"CID в кэше не совпадает для {file_name}"
        
        logger.info("✅ Тест пройден")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise

def test_metrics(pinata_uploader, temp_test_files):
    """Проверка системы метрик"""
    logger.info("=" * 50)
    logger.info("🚀 Тест: система метрик")
    
    # Загружаем файл для генерации метрик
    file_path = temp_test_files[0]
    cid = pinata_uploader.upload_file(str(file_path), "test_metrics.txt")
    assert cid, "Ошибка загрузки тестового файла"
    
    # Проверяем метрики
    metrics = pinata_uploader.metrics
    
    assert len(metrics.upload_times) > 0, "Не записано время загрузки"
    assert metrics.get_average_upload_time() > 0, "Среднее время загрузки не вычислено"
    
    # Проверяем кэш-метрики
    pinata_uploader.find_file_by_name("test_metrics.txt")  # Должен быть hit
    pinata_uploader.find_file_by_name("nonexistent.file")  # Должен быть miss
    
    assert metrics.cache_hits > 0, "Не записаны попадания в кэш"
    assert metrics.cache_misses > 0, "Не записаны промахи кэша"
    
    logger.info("✅ Тест пройден")
