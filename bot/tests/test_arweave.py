import pytest
import logging
import json
from bot.services.ar_weave import ArWeaveUploader
import os
from dotenv import load_dotenv

# Настройка логгера
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Константа для тестирования
ZEYA = "88888888"  # 8 символов цифры 8

@pytest.fixture
def arweave_uploader():
    """Фикстура для создания экземпляра ArWeaveUploader"""
    logger.info("=" * 50)
    logger.info("🔧 НАЧАЛО ИНИЦИАЛИЗАЦИИ ФИКСТУРЫ arweave_uploader")
    
    # Проверяем переменные окружения
    key_path = os.getenv("ARWEAVE_PRIVATE_KEY")
    logger.info(f"📝 ARWEAVE_PRIVATE_KEY путь: {key_path}")
    assert key_path is not None, "ARWEAVE_PRIVATE_KEY не установлен в .env"
    assert os.path.isfile(key_path), f"Файл ключа не найден по пути: {key_path}"
    
    uploader = ArWeaveUploader()
    logger.info("✅ ArWeaveUploader создан")
    
    return uploader

def test_upload_and_download_text(arweave_uploader):
    """
    Тест загрузки и скачивания текстовых данных.
    Использует константу ZEYA для проверки.
    """
    logger.info("=" * 50)
    logger.info("🚀 НАЧАЛО ТЕСТА ЗАГРУЗКИ/СКАЧИВАНИЯ ТЕКСТА")
    
    # Подготавливаем тестовые данные
    test_data = {
        "test_id": ZEYA,
        "description": "Test upload and download"
    }
    test_json = json.dumps(test_data)
    
    logger.debug(f"📝 Подготовлены тестовые данные: {test_json}")
    
    try:
        # Загружаем данные
        logger.debug("📤 Начинаем загрузку данных в Arweave")
        arweave_url = arweave_uploader.upload_text(test_json)
        logger.info(f"✅ Данные успешно загружены: {arweave_url}")
        
        # Извлекаем CID из URL
        cid = arweave_url.split('/')[-1]
        logger.debug(f"🔑 Извлечен CID: {cid}")
        
        # Скачиваем данные обратно
        logger.debug("📥 Начинаем скачивание данных")
        downloaded_data = arweave_uploader.download_json(cid)
        logger.debug(f"✅ Данные успешно скачаны: {downloaded_data}")
        
        # Проверяем данные
        assert downloaded_data["test_id"] == ZEYA, \
            f"Ошибка проверки данных: ожидалось {ZEYA}, получено {downloaded_data.get('test_id')}"
        logger.info("✅ Проверка данных успешна")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {str(e)}")
        raise

def test_download_with_ar_prefix(arweave_uploader):
    """
    Тест скачивания данных с префиксом ar://.
    """
    logger.info("=" * 50)
    logger.info("🚀 НАЧАЛО ТЕСТА СКАЧИВАНИЯ С ПРЕФИКСОМ ar://")
    
    try:
        # Загружаем тестовые данные
        test_data = {"test_id": ZEYA}
        test_json = json.dumps(test_data)
        
        # Загружаем данные
        arweave_url = arweave_uploader.upload_text(test_json)
        cid = arweave_url.split('/')[-1]
        
        # Добавляем префикс ar://
        ar_cid = f"ar://{cid}"
        logger.debug(f"🔍 Тестируем CID с префиксом: {ar_cid}")
        
        # Пытаемся скачать с префиксом
        downloaded_data = arweave_uploader.download_json(ar_cid)
        assert downloaded_data["test_id"] == ZEYA, \
            "Данные не совпадают после скачивания с префиксом ar://"
        
        logger.info("✅ Тест успешно завершен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {str(e)}")
        raise

def test_error_handling(arweave_uploader):
    """
    Тест обработки ошибок при неверном CID.
    """
    logger.info("=" * 50)
    logger.info("🚀 НАЧАЛО ТЕСТА ОБРАБОТКИ ОШИБОК")
    
    invalid_cids = [
        "invalid_cid",
        "not_exists_12345",
        ""  # Пустой CID
    ]
    
    for invalid_cid in invalid_cids:
        logger.debug(f"\n🔍 Тестируем неверный CID: {invalid_cid}")
        
        try:
            arweave_uploader.download_json(invalid_cid)
            pytest.fail(f"Ожидалась ошибка для неверного CID: {invalid_cid}")
        except Exception as e:
            logger.debug(f"✅ Получена ожидаемая ошибка: {str(e)}")
            
    logger.info("✅ Тест успешно завершен")
