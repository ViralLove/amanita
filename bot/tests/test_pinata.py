import pytest
import logging
import json
import os
from dotenv import load_dotenv
import time
from pathlib import Path
import tempfile
import shutil

# Загружаем .env файл
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from bot.services.core.storage.pinata import SecurePinataUploader

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

def test_pinata_connection_minimal():
    """Минимальный тест для проверки соединения с Pinata API"""
    logger.info("=" * 50)
    logger.info("🚀 МИНИМАЛЬНЫЙ ТЕСТ: проверка соединения с Pinata")
    
    # Проверяем наличие ключей
    api_key = os.getenv("PINATA_API_KEY")
    api_secret = os.getenv("PINATA_API_SECRET")
    
    logger.info(f"🔑 API Key: {api_key[:10]}..." if api_key else "❌ API Key отсутствует")
    logger.info(f"🔑 API Secret: {api_secret[:10]}..." if api_secret else "❌ API Secret отсутствует")
    
    assert api_key, "PINATA_API_KEY не установлен"
    assert api_secret, "PINATA_API_SECRET не установлен"
    
    try:
        # Создаем минимальный экземпляр
        uploader = SecurePinataUploader()
        logger.info("✅ SecurePinataUploader создан успешно")
        
        # Простой тест - загружаем минимальные данные
        test_data = {"test": "connection", "timestamp": time.time()}
        
        logger.info("📤 Попытка загрузки тестовых данных...")
        cid = uploader.upload_text(test_data, "connection_test.json")
        
        assert cid, "CID не получен"
        logger.info(f"✅ Данные загружены успешно, CID: {cid}")
        
        # Проверяем, что данные можно скачать
        logger.info("📥 Попытка скачивания данных...")
        downloaded = uploader.download_json(cid)
        
        assert downloaded is not None, "Не удалось скачать данные"
        assert downloaded["test"] == "connection", "Данные не совпадают"
        logger.info("✅ Данные скачаны и проверены успешно")
        
        logger.info("🎉 МИНИМАЛЬНЫЙ ТЕСТ ПРОЙДЕН - СОЕДИНЕНИЕ РАБОТАЕТ")
        return True
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА СОЕДИНЕНИЯ: {str(e)}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        raise

def test_pinata_jwt_connection():
    """Тест соединения с Pinata API через JWT токен"""
    logger.info("=" * 50)
    logger.info("🚀 ТЕСТ JWT: проверка соединения с Pinata через JWT")
    
    # Проверяем наличие JWT токена
    jwt_token = os.getenv("PINATA_JWT")
    
    logger.info(f"🔑 JWT Token: {jwt_token[:20]}..." if jwt_token else "❌ JWT Token отсутствует")
    
    assert jwt_token, "PINATA_JWT не установлен"
    
    try:
        # Простой тест с JWT аутентификацией
        import requests
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        # Тестовые данные
        test_data = {
            "pinataContent": {
                "test": "jwt_connection",
                "timestamp": time.time()
            },
            "pinataMetadata": {
                "name": "jwt_test.json"
            }
        }
        
        logger.info("📤 Попытка загрузки через JWT...")
        
        response = requests.post(
            "https://api.pinata.cloud/pinning/pinJSONToIPFS",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        logger.info(f"📊 Статус ответа: {response.status_code}")
        logger.info(f"📊 Заголовки ответа: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            cid = result.get("IpfsHash")
            logger.info(f"✅ JWT загрузка успешна, CID: {cid}")
            
            # Проверяем скачивание
            gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"
            logger.info(f"📥 Попытка скачивания: {gateway_url}")
            
            download_response = requests.get(gateway_url, timeout=30)
            if download_response.status_code == 200:
                downloaded_data = download_response.json()
                logger.info(f"✅ Скачивание успешно: {downloaded_data}")
                return True
            else:
                logger.error(f"❌ Ошибка скачивания: {download_response.status_code}")
                return False
        else:
            logger.error(f"❌ Ошибка JWT загрузки: {response.status_code}")
            logger.error(f"❌ Ответ: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ОШИБКА JWT ТЕСТА: {str(e)}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        return False

def test_pinata_direct_api():
    """Тест прямого обращения к Pinata API с API ключами"""
    logger.info("=" * 50)
    logger.info("🚀 ТЕСТ ПРЯМОГО API: проверка с API ключами")
    
    # Проверяем наличие ключей
    api_key = os.getenv("PINATA_API_KEY")
    api_secret = os.getenv("PINATA_API_SECRET")
    
    logger.info(f"🔑 API Key: {api_key[:10]}..." if api_key else "❌ API Key отсутствует")
    logger.info(f"🔑 API Secret: {api_secret[:10]}..." if api_secret else "❌ API Secret отсутствует")
    
    assert api_key, "PINATA_API_KEY не установлен"
    assert api_secret, "PINATA_API_SECRET не установлен"
    
    try:
        import requests
        
        # Заголовки как в curl
        headers = {
            "pinata_api_key": api_key,
            "pinata_secret_api_key": api_secret,
            "Content-Type": "application/json"
        }
        
        # Сначала тестируем аутентификацию
        logger.info("🔐 Тест аутентификации...")
        auth_response = requests.get(
            "https://api.pinata.cloud/data/testAuthentication",
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 Статус аутентификации: {auth_response.status_code}")
        if auth_response.status_code == 200:
            logger.info(f"✅ Аутентификация успешна: {auth_response.json()}")
        else:
            logger.error(f"❌ Ошибка аутентификации: {auth_response.text}")
            return False
        
        # Теперь тестируем загрузку JSON
        test_data = {
            "pinataContent": {
                "test": "direct_api",
                "timestamp": time.time()
            },
            "pinataMetadata": {
                "name": "direct_api_test.json"
            }
        }
        
        logger.info("📤 Попытка загрузки JSON...")
        upload_response = requests.post(
            "https://api.pinata.cloud/pinning/pinJSONToIPFS",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        logger.info(f"📊 Статус загрузки: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            result = upload_response.json()
            cid = result.get("IpfsHash")
            logger.info(f"✅ Загрузка успешна, CID: {cid}")
            
            # Проверяем скачивание
            gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"
            logger.info(f"📥 Попытка скачивания: {gateway_url}")
            
            download_response = requests.get(gateway_url, timeout=30)
            if download_response.status_code == 200:
                downloaded_data = download_response.json()
                logger.info(f"✅ Скачивание успешно: {downloaded_data}")
                return True
            else:
                logger.error(f"❌ Ошибка скачивания: {download_response.status_code}")
                return False
        else:
            logger.error(f"❌ Ошибка загрузки: {upload_response.status_code}")
            logger.error(f"❌ Ответ: {upload_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ОШИБКА ПРЯМОГО API ТЕСТА: {str(e)}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        return False

def test_pinata_diagnostic():
    """Диагностический тест состояния Pinata API"""
    logger.info("=" * 50)
    logger.info("🔍 ДИАГНОСТИКА: полная проверка состояния Pinata API")
    
    # Проверяем все типы ключей
    api_key = os.getenv("PINATA_API_KEY")
    api_secret = os.getenv("PINATA_API_SECRET")
    jwt_token = os.getenv("PINATA_JWT")
    
    logger.info("📋 ПРОВЕРКА КЛЮЧЕЙ:")
    logger.info(f"  🔑 API Key: {'✅ Установлен' if api_key else '❌ Отсутствует'}")
    logger.info(f"  🔑 API Secret: {'✅ Установлен' if api_secret else '❌ Отсутствует'}")
    logger.info(f"  🔑 JWT Token: {'✅ Установлен' if jwt_token else '❌ Отсутствует'}")
    
    try:
        import requests
        
        # Тест 1: API ключи - аутентификация
        logger.info("\n🔐 ТЕСТ 1: Аутентификация API ключей")
        if api_key and api_secret:
            headers = {
                "pinata_api_key": api_key,
                "pinata_secret_api_key": api_secret
            }
            
            auth_response = requests.get(
                "https://api.pinata.cloud/data/testAuthentication",
                headers=headers,
                timeout=10
            )
            
            if auth_response.status_code == 200:
                logger.info("  ✅ Аутентификация API ключей: УСПЕШНО")
            else:
                logger.error(f"  ❌ Аутентификация API ключей: ОШИБКА {auth_response.status_code}")
        else:
            logger.warning("  ⚠️ API ключи не установлены")
        
        # Тест 2: API ключи - загрузка
        logger.info("\n📤 ТЕСТ 2: Загрузка через API ключи")
        if api_key and api_secret:
            headers = {
                "pinata_api_key": api_key,
                "pinata_secret_api_key": api_secret,
                "Content-Type": "application/json"
            }
            
            test_data = {
                "pinataContent": {"test": "diagnostic"},
                "pinataMetadata": {"name": "diagnostic_test.json"}
            }
            
            upload_response = requests.post(
                "https://api.pinata.cloud/pinning/pinJSONToIPFS",
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            if upload_response.status_code == 200:
                logger.info("  ✅ Загрузка API ключей: УСПЕШНО")
            elif upload_response.status_code == 403:
                logger.error("  ❌ Загрузка API ключей: НЕТ РАЗРЕШЕНИЙ (403)")
                logger.error(f"     Детали: {upload_response.json()}")
            else:
                logger.error(f"  ❌ Загрузка API ключей: ОШИБКА {upload_response.status_code}")
        else:
            logger.warning("  ⚠️ API ключи не установлены")
        
        # Тест 3: JWT токен
        logger.info("\n🔑 ТЕСТ 3: JWT токен")
        if jwt_token:
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
            
            test_data = {
                "pinataContent": {"test": "jwt_diagnostic"},
                "pinataMetadata": {"name": "jwt_diagnostic_test.json"}
            }
            
            jwt_response = requests.post(
                "https://api.pinata.cloud/pinning/pinJSONToIPFS",
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            if jwt_response.status_code == 200:
                logger.info("  ✅ JWT загрузка: УСПЕШНО")
            elif jwt_response.status_code == 403:
                logger.error("  ❌ JWT загрузка: НЕТ РАЗРЕШЕНИЙ (403)")
                logger.error(f"     Детали: {jwt_response.json()}")
            else:
                logger.error(f"  ❌ JWT загрузка: ОШИБКА {jwt_response.status_code}")
        else:
            logger.warning("  ⚠️ JWT токен не установлен")
        
        # Резюме
        logger.info("\n📊 РЕЗЮМЕ ДИАГНОСТИКИ:")
        logger.info("  🔍 Проблема: API ключи не имеют разрешений для загрузки файлов")
        logger.info("  🔍 Решение: Обновить разрешения в Pinata Dashboard или создать новые ключи")
        logger.info("  🔍 Статус: Требуется вмешательство администратора")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА ДИАГНОСТИКИ: {str(e)}")
        return False

def test_pinata_amanita_key_detailed():
    """Детальный тест ключа Amanita с полным логированием"""
    logger.info("=" * 50)
    logger.info("🔍 ДЕТАЛЬНЫЙ ТЕСТ: проверка ключа Amanita")
    
    # Проверяем ключи
    api_key = os.getenv("PINATA_API_KEY")
    api_secret = os.getenv("PINATA_API_SECRET")
    
    logger.info(f"🔑 API Key: {api_key}")
    logger.info(f"🔑 API Secret: {api_secret[:20]}...")
    
    assert api_key, "PINATA_API_KEY не установлен"
    assert api_secret, "PINATA_API_SECRET не установлен"
    
    try:
        import requests
        
        # Заголовки для запроса
        headers = {
            "pinata_api_key": api_key,
            "pinata_secret_api_key": api_secret,
            "Content-Type": "application/json"
        }
        
        logger.info("📋 ЗАГОЛОВКИ ЗАПРОСА:")
        for key, value in headers.items():
            if "secret" in key.lower():
                logger.info(f"  {key}: {value[:20]}...")
            else:
                logger.info(f"  {key}: {value}")
        
        # Тестовые данные
        test_data = {
            "pinataContent": {
                "test": "amanita_key_test",
                "timestamp": time.time(),
                "key_name": "Amanita"
            },
            "pinataMetadata": {
                "name": "amanita_test.json"
            }
        }
        
        logger.info("📤 ОТПРАВКА ЗАПРОСА:")
        logger.info(f"  URL: https://api.pinata.cloud/pinning/pinJSONToIPFS")
        logger.info(f"  Method: POST")
        logger.info(f"  Data: {json.dumps(test_data, indent=2)}")
        
        # Отправляем запрос
        response = requests.post(
            "https://api.pinata.cloud/pinning/pinJSONToIPFS",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        logger.info("📊 ОТВЕТ ОТ СЕРВЕРА:")
        logger.info(f"  Status Code: {response.status_code}")
        logger.info(f"  Headers: {dict(response.headers)}")
        logger.info(f"  Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            cid = result.get("IpfsHash")
            logger.info(f"✅ УСПЕХ! CID: {cid}")
            return True
        elif response.status_code == 403:
            error_data = response.json()
            logger.error(f"❌ 403 FORBIDDEN:")
            logger.error(f"  Error: {error_data}")
            
            # Проверяем, может ли быть проблема с форматом данных
            logger.info("🔍 ПОПЫТКА АЛЬТЕРНАТИВНОГО ФОРМАТА...")
            
            # Альтернативный формат данных
            alt_data = {
                "pinataContent": "test_content",
                "pinataMetadata": {
                    "name": "test.txt"
                }
            }
            
            alt_response = requests.post(
                "https://api.pinata.cloud/pinning/pinJSONToIPFS",
                headers=headers,
                json=alt_data,
                timeout=30
            )
            
            logger.info(f"📊 АЛЬТЕРНАТИВНЫЙ ОТВЕТ: {alt_response.status_code}")
            logger.info(f"📊 АЛЬТЕРНАТИВНЫЙ ТЕКСТ: {alt_response.text}")
            
            if alt_response.status_code == 200:
                logger.info("✅ АЛЬТЕРНАТИВНЫЙ ФОРМАТ РАБОТАЕТ!")
                return True
            else:
                logger.error("❌ АЛЬТЕРНАТИВНЫЙ ФОРМАТ ТОЖЕ НЕ РАБОТАЕТ")
                return False
        else:
            logger.error(f"❌ НЕОЖИДАННАЯ ОШИБКА: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ОШИБКА ТЕСТА: {str(e)}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        return False

def test_pinata_alternative_endpoints():
    """Тест альтернативных endpoints Pinata API"""
    logger.info("=" * 50)
    logger.info("🔍 ТЕСТ АЛЬТЕРНАТИВНЫХ ENDPOINTS")
    
    api_key = os.getenv("PINATA_API_KEY")
    api_secret = os.getenv("PINATA_API_SECRET")
    
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": api_secret,
        "Content-Type": "application/json"
    }
    
    try:
        import requests
        
        # Тест 1: Проверка аутентификации
        logger.info("🔐 ТЕСТ 1: Аутентификация")
        auth_response = requests.get(
            "https://api.pinata.cloud/data/testAuthentication",
            headers=headers,
            timeout=10
        )
        logger.info(f"  Статус: {auth_response.status_code}")
        logger.info(f"  Ответ: {auth_response.text}")
        
        # Тест 2: Проверка списка файлов
        logger.info("📋 ТЕСТ 2: Список файлов")
        list_response = requests.get(
            "https://api.pinata.cloud/data/pinList",
            headers=headers,
            timeout=10
        )
        logger.info(f"  Статус: {list_response.status_code}")
        if list_response.status_code == 200:
            data = list_response.json()
            logger.info(f"  Количество файлов: {len(data.get('rows', []))}")
        else:
            logger.info(f"  Ответ: {list_response.text}")
        
        # Тест 3: Попытка загрузки через другой endpoint
        logger.info("📤 ТЕСТ 3: Альтернативный endpoint загрузки")
        
        # Создаем временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "alternative_endpoint"}, f)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {'file': f}
                alt_response = requests.post(
                    "https://api.pinata.cloud/pinning/pinFileToIPFS",
                    headers={
                        "pinata_api_key": api_key,
                        "pinata_secret_api_key": api_secret
                    },
                    files=files,
                    timeout=30
                )
            
            logger.info(f"  Статус: {alt_response.status_code}")
            logger.info(f"  Ответ: {alt_response.text}")
            
            if alt_response.status_code == 200:
                result = alt_response.json()
                cid = result.get("IpfsHash")
                logger.info(f"  ✅ УСПЕХ! CID: {cid}")
                return True
            else:
                logger.error(f"  ❌ ОШИБКА: {alt_response.status_code}")
                return False
                
        finally:
            # Удаляем временный файл
            os.unlink(temp_file_path)
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА: {str(e)}")
        return False

def test_pinata_new_key():
    """Тест для нового API ключа (если будет создан)"""
    logger.info("=" * 50)
    logger.info("🆕 ТЕСТ НОВОГО API КЛЮЧА")
    
    # Проверяем, есть ли новый ключ в переменных окружения
    new_api_key = os.getenv("PINATA_NEW_API_KEY")
    new_api_secret = os.getenv("PINATA_NEW_API_SECRET")
    
    if not new_api_key or not new_api_secret:
        logger.info("⚠️ Новый API ключ не найден в переменных окружения")
        logger.info("💡 Для тестирования нового ключа добавьте в .env:")
        logger.info("   PINATA_NEW_API_KEY=your_new_key")
        logger.info("   PINATA_NEW_API_SECRET=your_new_secret")
        return True  # Не падаем, если ключ не установлен
    
    logger.info(f"🔑 Новый API Key: {new_api_key}")
    logger.info(f"🔑 Новый API Secret: {new_api_secret[:20]}...")
    
    try:
        import requests
        
        headers = {
            "pinata_api_key": new_api_key,
            "pinata_secret_api_key": new_api_secret,
            "Content-Type": "application/json"
        }
        
        # Тест аутентификации
        logger.info("🔐 Тест аутентификации нового ключа...")
        auth_response = requests.get(
            "https://api.pinata.cloud/data/testAuthentication",
            headers=headers,
            timeout=10
        )
        
        if auth_response.status_code != 200:
            logger.error(f"❌ Ошибка аутентификации: {auth_response.status_code}")
            return False
        
        logger.info("✅ Аутентификация нового ключа успешна")
        
        # Тест загрузки
        test_data = {
            "pinataContent": {"test": "new_key_test"},
            "pinataMetadata": {"name": "new_key_test.json"}
        }
        
        logger.info("📤 Тест загрузки с новым ключом...")
        upload_response = requests.post(
            "https://api.pinata.cloud/pinning/pinJSONToIPFS",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        if upload_response.status_code == 200:
            result = upload_response.json()
            cid = result.get("IpfsHash")
            logger.info(f"✅ НОВЫЙ КЛЮЧ РАБОТАЕТ! CID: {cid}")
            return True
        else:
            logger.error(f"❌ Новый ключ тоже не работает: {upload_response.status_code}")
            logger.error(f"   Ответ: {upload_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования нового ключа: {str(e)}")
        return False
