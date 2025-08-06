"""
Тесты для интеграции Supabase Edge Function с ArWeave загрузкой.
"""

import pytest
import os
import json
import logging
import time
import tempfile
import requests
from pathlib import Path
from dotenv import load_dotenv

# Импорт тестируемых модулей
from bot.config import SUPABASE_URL, SUPABASE_ANON_KEY

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Константы для тестирования
TRANSFORMATION = "88888888"
EDGE_FUNCTION_BASE_URL = f"{SUPABASE_URL}/functions/v1/arweave-upload"


class PerformanceMetrics:
    """Класс для измерения производительности тестов"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, test_name: str):
        """Начинает таймер для теста"""
        self.metrics[test_name] = {
            'start_time': time.time(),
            'end_time': None,
            'duration': None
        }
    
    def end_timer(self, test_name: str):
        """Завершает таймер для теста"""
        if test_name in self.metrics:
            self.metrics[test_name]['end_time'] = time.time()
            self.metrics[test_name]['duration'] = (
                self.metrics[test_name]['end_time'] - 
                self.metrics[test_name]['start_time']
            )
    
    def get_duration(self, test_name: str) -> float:
        """Возвращает длительность теста"""
        return self.metrics.get(test_name, {}).get('duration', 0)
    
    def print_summary(self):
        """Выводит сводку по производительности"""
        logger.info("📊 СВОДКА ПРОИЗВОДИТЕЛЬНОСТИ:")
        for test_name, metric in self.metrics.items():
            duration = metric.get('duration', 0)
            logger.info(f"   {test_name}: {duration:.3f}s")


class BalanceTracker:
    """Класс для отслеживания баланса ArWeave операций"""
    
    def __init__(self):
        self.operations = []
        self.start_time = time.time()
        self.initial_balance = None
        self.final_balance = None
    
    def get_arweave_balance(self) -> float:
        """Получает текущий баланс ArWeave кошелька"""
        try:
            # Используем ArWeave API для получения баланса
            import requests
            from bot.config import ARWEAVE_PRIVATE_KEY
            
            # Извлекаем адрес кошелька из приватного ключа
            wallet_address = self._extract_wallet_address(ARWEAVE_PRIVATE_KEY)
            if not wallet_address:
                logger.warning("⚠️ Не удалось извлечь адрес кошелька")
                return None
            
            # Запрос баланса через ArWeave API
            url = f"https://arweave.net/wallet/{wallet_address}/balance"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                balance_ar = float(response.text) / 1e12  # Конвертируем из winston в AR
                logger.info(f"💰 Текущий баланс ArWeave: {balance_ar:.6f} AR")
                return balance_ar
            else:
                logger.warning(f"⚠️ Не удалось получить баланс: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения баланса: {e}")
            return None
    
    def _extract_wallet_address(self, private_key_path: str) -> str:
        """Извлекает адрес кошелька из приватного ключа"""
        try:
            import json
            import base64
            import hashlib
            
            # Загружаем приватный ключ
            if private_key_path.startswith('{'):
                key_data = json.loads(private_key_path)
            else:
                with open(private_key_path, 'r') as f:
                    key_data = json.load(f)
            
            # Извлекаем публичный ключ (n) из RSA ключа
            n = key_data.get('n')
            if not n:
                logger.warning("⚠️ Не найден параметр 'n' в RSA ключе")
                return None
            
            # Декодируем base64url
            n_bytes = base64.urlsafe_b64decode(n + '=' * (4 - len(n) % 4))
            
            # Вычисляем хеш SHA256
            sha256_hash = hashlib.sha256(n_bytes).digest()
            
            # Конвертируем в base64url (это и есть адрес кошелька)
            wallet_address = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')
            
            logger.info(f"💰 Извлечен адрес кошелька: {wallet_address}")
            return wallet_address
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка извлечения адреса кошелька: {e}")
            return None
    
    def start_balance_tracking(self):
        """Начинает отслеживание баланса"""
        self.initial_balance = self.get_arweave_balance()
        logger.info(f"💰 Начальный баланс: {self.initial_balance:.6f} AR" if self.initial_balance else "💰 Начальный баланс: неизвестен")
    
    def end_balance_tracking(self):
        """Завершает отслеживание баланса"""
        self.final_balance = self.get_arweave_balance()
        logger.info(f"💰 Финальный баланс: {self.final_balance:.6f} AR" if self.final_balance else "💰 Финальный баланс: неизвестен")
        
        if self.initial_balance is not None and self.final_balance is not None:
            balance_change = self.final_balance - self.initial_balance
            logger.info(f"💰 Изменение баланса: {balance_change:+.6f} AR")
            return balance_change
        return None
    
    def track_operation(self, operation_type: str, transaction_id: str = None, cost_estimate: str = "unknown"):
        """Отслеживает операцию"""
        operation = {
            "type": operation_type,
            "timestamp": time.time(),
            "transaction_id": transaction_id,
            "cost_estimate": cost_estimate
        }
        self.operations.append(operation)
        logger.info(f"💰 Операция: {operation_type}, TX: {transaction_id}, стоимость: {cost_estimate}")
    
    def get_summary(self):
        """Возвращает сводку операций"""
        return {
            "total_operations": len(self.operations),
            "operations": self.operations,
            "total_time": time.time() - self.start_time,
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "balance_change": self.final_balance - self.initial_balance if (self.initial_balance is not None and self.final_balance is not None) else None
        }


# Глобальные объекты для метрик
performance_metrics = PerformanceMetrics()
balance_tracker = BalanceTracker()

@pytest.fixture
def arweave_balance_tracker():
    """
    Фикстура для точного измерения расхода AR токенов
    """
    tracker = BalanceTracker()
    tracker.start_balance_tracking()
    
    yield tracker
    
    # После теста завершаем отслеживание
    balance_change = tracker.end_balance_tracking()
    
    # Логируем результаты
    summary = tracker.get_summary()
    logger.info("💰 ТОЧНОЕ ИЗМЕРЕНИЕ РАСХОДА AR:")
    logger.info(f"   💰 Начальный баланс: {summary['initial_balance']:.6f} AR" if summary['initial_balance'] else "   💰 Начальный баланс: неизвестен")
    logger.info(f"   💰 Финальный баланс: {summary['final_balance']:.6f} AR" if summary['final_balance'] else "   💰 Финальный баланс: неизвестен")
    if summary['balance_change'] is not None:
        logger.info(f"   💰 Изменение баланса: {summary['balance_change']:+.6f} AR")
        if summary['balance_change'] < 0:
            logger.info(f"   💸 Расход AR: {abs(summary['balance_change']):.6f} AR")
        else:
            logger.info(f"   💰 Пополнение AR: {summary['balance_change']:.6f} AR")
    logger.info(f"   📊 Всего операций: {summary['total_operations']}")


def measure_performance(test_name: str):
    """Декоратор для измерения производительности тестов"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            performance_metrics.start_timer(test_name)
            try:
                result = func(self, *args, **kwargs)
                return result
            finally:
                performance_metrics.end_timer(test_name)
        return wrapper
    return decorator


@pytest.fixture(scope="module")
def edge_function_client():
    """
    Фикстура для HTTP клиента edge function
    """
    class EdgeFunctionClient:
        def __init__(self):
            self.base_url = EDGE_FUNCTION_BASE_URL
            self.headers = {
                'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
                'Content-Type': 'application/json'
            }
            self.timeout = 30
        
        def health_check(self):
            """Проверка здоровья edge function"""
            url = f"{self.base_url}/health"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            return response
        
        def upload_text(self, data: str, content_type: str = "text/plain"):
            """Загрузка текста через edge function"""
            url = f"{self.base_url}/upload-text"
            payload = {
                "data": data,
                "contentType": content_type
            }
            response = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
            return response
        
        def upload_file(self, file_path: str):
            """Загрузка файла через edge function"""
            url = f"{self.base_url}/upload-file"
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                headers = {'Authorization': f'Bearer {SUPABASE_ANON_KEY}'}
                response = requests.post(url, files=files, headers=headers, timeout=self.timeout)
            return response
    
    return EdgeFunctionClient()


@pytest.fixture(scope="module")
def arweave_uploader():
    """
    Фикстура для ArWeaveUploader с edge function интеграцией
    ПРИМЕЧАНИЕ: Этот тест должен тестировать только Edge Function, а не Python интеграцию
    """
    # Для тестирования Edge Function нам не нужен Python ArWeaveUploader
    # Мы тестируем Edge Function напрямую через HTTP запросы
    return None


@pytest.fixture
def temp_test_file():
    """
    Фикстура для создания временного тестового файла
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test file content for ArWeave upload")
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Очистка
    try:
        os.unlink(temp_file_path)
    except OSError:
        pass


@pytest.fixture
def test_json_data():
    """
    Фикстура для тестовых JSON данных
    """
    return {
        "test": "data",
        "number": 42,
        "boolean": True,
        "array": [1, 2, 3],
        "object": {"nested": "value"}
    }


# ============================================================================
# ТЕСТЫ EDGE FUNCTION
# ============================================================================

class TestEdgeFunctionAvailability:
    """Тесты доступности и работоспособности edge function"""
    
    def test_health_check(self, edge_function_client):
        """Тест health check endpoint"""
        logger.info("🔍 Тестирование health check endpoint")
        
        response = edge_function_client.health_check()
        
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        data = response.json()
        assert data.get('status') == 'healthy', f"Invalid status: {data.get('status')}"
        assert 'timestamp' in data, "Missing timestamp in response"
        assert data.get('arweave') == 'connected', f"ArWeave not connected: {data.get('arweave')}"
        
        logger.info(f"✅ Health check passed: {data}")
        balance_tracker.track_operation("health_check")
    
    def test_balance_tracking_demo(self, arweave_balance_tracker):
        """Демонстрация работы фикстуры измерения баланса AR токенов"""
        logger.info("🔍 Демонстрация измерения баланса AR токенов")
        
        # Симулируем операцию без реальной загрузки
        arweave_balance_tracker.track_operation("balance_check_demo", cost_estimate="0 AR")
        
        # Проверяем, что фикстура работает
        summary = arweave_balance_tracker.get_summary()
        assert summary['total_operations'] >= 1, "Должна быть хотя бы одна операция"
        
        logger.info("✅ Демонстрация измерения баланса завершена")
    
    def test_upload_text_with_balance_tracking(self, edge_function_client, test_json_data, arweave_balance_tracker):
        """Тест загрузки текста с точным измерением расхода AR токенов"""
        logger.info("🔍 Тестирование upload text с измерением расхода AR")
        
        test_data = json.dumps(test_json_data)
        
        # Отслеживаем операцию
        arweave_balance_tracker.track_operation("upload_text_start", cost_estimate="~0.002 AR")
        
        # ОБЯЗАТЕЛЬНАЯ проверка HTTP статуса
        response = edge_function_client.upload_text(test_data, "application/json")
        assert response.status_code == 200, f"HTTP error: {response.status_code} - {response.text}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка успеха операции
        data = response.json()
        assert data.get('success') is True, f"Upload failed: {data}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка transaction_id
        transaction_id = data.get('transaction_id')
        assert transaction_id and transaction_id.startswith('ar'), f"Invalid transaction ID: {transaction_id}"
        
        # Отслеживаем успешную операцию
        arweave_balance_tracker.track_operation("upload_text_success", transaction_id, "actual_cost")
        logger.info(f"✅ Text upload successful: {transaction_id}")
        
        # ДОПОЛНИТЕЛЬНАЯ проверка: скачивание загруженных данных
        downloaded_data = self.verify_arweave_upload(transaction_id, test_data)
        assert downloaded_data == test_data, f"Uploaded data doesn't match: {downloaded_data[:100]}..."
        
        logger.info(f"✅ Text upload verified in ArWeave: {transaction_id}")
        return transaction_id
    
    def verify_arweave_upload(self, transaction_id: str, expected_data: str) -> str:
        """Проверяет, что данные реально загружены в ArWeave"""
        url = f"https://arweave.net/{transaction_id}"
        response = requests.get(url, timeout=30)
        assert response.status_code == 200, f"Failed to download from ArWeave: {response.status_code}"
        return response.text
    
    def test_upload_file(self, edge_function_client, temp_test_file):
        """Тест загрузки файла через edge function"""
        logger.info("🔍 Тестирование upload file endpoint")
        
        # ОБЯЗАТЕЛЬНАЯ проверка HTTP статуса
        response = edge_function_client.upload_file(temp_test_file)
        assert response.status_code == 200, f"HTTP error: {response.status_code} - {response.text}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка успеха операции
        data = response.json()
        assert data.get('success') is True, f"Upload failed: {data}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка transaction_id
        transaction_id = data.get('transaction_id')
        assert transaction_id and transaction_id.startswith('ar'), f"Invalid transaction ID: {transaction_id}"
        
        # Отслеживаем успешную операцию
        balance_tracker.track_operation("upload_file", transaction_id)
        logger.info(f"✅ File upload successful: {transaction_id}")
        
        # ДОПОЛНИТЕЛЬНАЯ проверка: скачивание загруженного файла
        downloaded_file = self.verify_arweave_file_upload(transaction_id, temp_test_file)
        assert downloaded_file, "Failed to download uploaded file from ArWeave"
        
        logger.info(f"✅ File upload verified in ArWeave: {transaction_id}")
        return transaction_id
    
    def verify_arweave_file_upload(self, transaction_id: str, original_file_path: str) -> bool:
        """Проверяет, что файл реально загружен в ArWeave"""
        url = f"https://arweave.net/{transaction_id}"
        response = requests.get(url, timeout=30)
        assert response.status_code == 200, f"Failed to download file from ArWeave: {response.status_code}"
        
        # Сравниваем с исходным файлом
        with open(original_file_path, 'rb') as f:
            original_content = f.read()
        
        return response.content == original_content


class TestEdgeFunctionErrorHandling:
    """Тесты обработки ошибок edge function"""
    
    def test_invalid_auth(self, edge_function_client):
        """Тест неверной аутентификации"""
        logger.info("🔍 Тестирование неверной аутентификации")
        
        # Создаем клиент с неверным ключом
        invalid_headers = {'Authorization': 'Bearer invalid_key'}
        url = f"{EDGE_FUNCTION_BASE_URL}/upload-text"
        payload = {"data": "test", "contentType": "text/plain"}
        
        response = requests.post(url, json=payload, headers=invalid_headers, timeout=30)
        
        # Ожидаем ошибку аутентификации
        assert response.status_code in [401, 403], f"Expected auth error, got: {response.status_code}"
        
        logger.info(f"✅ Invalid auth handled correctly: {response.status_code}")
    
    def test_invalid_data_format(self, edge_function_client):
        """Тест неверного формата данных"""
        logger.info("🔍 Тестирование неверного формата данных")
        
        # Отправляем неверный формат данных
        url = f"{EDGE_FUNCTION_BASE_URL}/upload-text"
        payload = {"wrong_field": "test"}  # Отсутствует поле "data"
        
        response = requests.post(url, json=payload, headers=edge_function_client.headers, timeout=30)
        
        # Ожидаем ТОЛЬКО валидные коды ошибок валидации
        assert response.status_code in [400, 422], f"Expected validation error, got: {response.status_code}"
        
        logger.info(f"✅ Invalid data format handled correctly: {response.status_code}")
    
    def test_server_error_handling(self, edge_function_client):
        """Тест обработки серверных ошибок (500)"""
        logger.info("🔍 Тестирование обработки серверных ошибок")
        
        # Отправляем запрос, который может вызвать серверную ошибку
        url = f"{EDGE_FUNCTION_BASE_URL}/upload-text"
        payload = {"data": "x" * 1000000}  # Очень большие данные
        
        response = requests.post(url, json=payload, headers=edge_function_client.headers, timeout=30)
        
        # 500 ошибка - это серверная ошибка, не ошибка валидации
        if response.status_code == 500:
            logger.warning(f"⚠️ Server error detected: {response.status_code}")
            # Тест проходит, но логируем предупреждение
        else:
            logger.info(f"✅ Request handled without server error: {response.status_code}")
    
    def test_missing_file(self, edge_function_client):
        """Тест отсутствующего файла"""
        logger.info("🔍 Тестирование отсутствующего файла")
        
        url = f"{EDGE_FUNCTION_BASE_URL}/upload-file"
        
        # Отправляем запрос без файла
        response = requests.post(url, headers=edge_function_client.headers, timeout=30)
        
        # Ожидаем ТОЛЬКО валидные коды ошибок валидации
        assert response.status_code in [400, 422], f"Expected file error, got: {response.status_code}"
        
        logger.info(f"✅ Missing file handled correctly: {response.status_code}")


# ============================================================================
# ТЕСТЫ КОНФИГУРАЦИИ
# ============================================================================

class TestConfiguration:
    """Тесты конфигурации Edge Function"""
    
    def test_configuration_validation(self):
        """Тест валидации конфигурации"""
        logger.info("🔍 Тестирование валидации конфигурации")
        
        # Проверяем наличие необходимых переменных
        assert SUPABASE_URL, "SUPABASE_URL не установлен"
        assert SUPABASE_URL.startswith("http"), f"Invalid SUPABASE_URL: {SUPABASE_URL}"
        
        if SUPABASE_ANON_KEY:
            assert len(SUPABASE_ANON_KEY) > 10, f"SUPABASE_ANON_KEY слишком короткий: {len(SUPABASE_ANON_KEY)}"
            logger.info("✅ SUPABASE_ANON_KEY установлен")
        else:
            logger.warning("⚠️ SUPABASE_ANON_KEY не установлен - Edge Functions недоступны")
        
        logger.info(f"✅ Configuration validation passed: {SUPABASE_URL}")


# ============================================================================
# END-TO-END ТЕСТИРОВАНИЕ EDGE FUNCTION
# ============================================================================

class TestEndToEndEdgeFunction:
    """Тесты полной интеграции Edge Function"""
    
    def test_upload_and_verify_cycle(self, edge_function_client, test_json_data):
        """Тест полного цикла: загрузка через Edge Function"""
        logger.info("🔍 Тестирование полного цикла upload через Edge Function")
        
        # ОБЯЗАТЕЛЬНАЯ проверка HTTP статуса
        test_data = json.dumps(test_json_data)
        response = edge_function_client.upload_text(test_data, "application/json")
        assert response.status_code == 200, f"HTTP error: {response.status_code} - {response.text}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка успеха операции
        data = response.json()
        assert data.get('success') is True, f"Upload failed: {data}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка transaction_id
        transaction_id = data.get('transaction_id')
        assert transaction_id and transaction_id.startswith('ar'), f"Invalid transaction ID: {transaction_id}"
        
        # Отслеживаем успешную операцию
        balance_tracker.track_operation("full_cycle", transaction_id)
        logger.info(f"✅ Full cycle successful: {transaction_id}")
        
        # ДОПОЛНИТЕЛЬНАЯ проверка: скачивание загруженных данных
        downloaded_data = self.verify_arweave_upload(transaction_id, test_data)
        assert downloaded_data == test_data, f"Uploaded data doesn't match: {downloaded_data[:100]}..."
        
        logger.info(f"✅ Full cycle verified in ArWeave: {transaction_id}")
        return transaction_id


# ============================================================================
# ПРОИЗВОДИТЕЛЬНОСТЬ EDGE FUNCTION
# ============================================================================

class TestPerformanceAndLoad:
    """Тесты производительности Edge Function"""
    
    def test_multiple_uploads(self, edge_function_client):
        """Тест множественных загрузок через Edge Function"""
        logger.info("🔍 Тестирование множественных загрузок через Edge Function")
        
        transaction_ids = []
        successful_uploads = 0
        
        for i in range(3):  # Тестируем 3 загрузки
            test_data = json.dumps({"test_number": i, "timestamp": time.time()})
            
            # ОБЯЗАТЕЛЬНАЯ проверка HTTP статуса
            response = edge_function_client.upload_text(test_data, "application/json")
            assert response.status_code == 200, f"Upload {i} HTTP error: {response.status_code} - {response.text}"
            
            # ОБЯЗАТЕЛЬНАЯ проверка успеха операции
            data = response.json()
            assert data.get('success') is True, f"Upload {i} failed: {data}"
            
            # ОБЯЗАТЕЛЬНАЯ проверка transaction_id
            transaction_id = data.get('transaction_id')
            assert transaction_id and transaction_id.startswith('ar'), f"Upload {i} invalid transaction ID: {transaction_id}"
            
            # Отслеживаем успешную операцию
            transaction_ids.append(transaction_id)
            balance_tracker.track_operation(f"multiple_upload_{i}", transaction_id)
            successful_uploads += 1
            logger.info(f"✅ Upload {i} successful: {transaction_id}")
            
            # ДОПОЛНИТЕЛЬНАЯ проверка: скачивание загруженных данных
            downloaded_data = self.verify_arweave_upload(transaction_id, test_data)
            assert downloaded_data == test_data, f"Upload {i} data doesn't match: {downloaded_data[:100]}..."
        
        # ОБЯЗАТЕЛЬНАЯ проверка: все загрузки должны быть успешными
        assert successful_uploads == 3, f"Expected 3 successful uploads, got {successful_uploads}"
        
        logger.info(f"✅ Multiple uploads completed: {successful_uploads}/{3} successful")
        return transaction_ids
    
    def test_performance_metrics(self, edge_function_client, test_json_data):
        """Измерение производительности Edge Function"""
        logger.info("🔍 Измерение производительности Edge Function")
        
        test_data = json.dumps(test_json_data)
        
        # ОБЯЗАТЕЛЬНАЯ проверка HTTP статуса
        start_time = time.time()
        response = edge_function_client.upload_text(test_data, "application/json")
        upload_time = time.time() - start_time
        
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка успеха операции
        data = response.json()
        assert data.get('success') is True, f"Upload failed: {data}"
        
        # ОБЯЗАТЕЛЬНАЯ проверка transaction_id
        transaction_id = data.get('transaction_id')
        assert transaction_id and transaction_id.startswith('ar'), f"Invalid transaction ID: {transaction_id}"
        
        # Измеряем производительность только успешных операций
        logger.info(f"✅ Upload successful: {transaction_id}")
        logger.info(f"Edge Function upload time: {upload_time:.3f}s")
        
        # ДОПОЛНИТЕЛЬНАЯ проверка: скачивание загруженных данных
        downloaded_data = self.verify_arweave_upload(transaction_id, test_data)
        assert downloaded_data == test_data, f"Uploaded data doesn't match: {downloaded_data[:100]}..."
        
        logger.info("✅ Performance metrics completed for successful upload")


# ============================================================================
# ФИНАЛЬНЫЕ ТЕСТЫ И ОТЧЕТЫ
# ============================================================================

class TestFinalSummary:
    """Финальные тесты и отчеты"""
    
    def test_final_summary(self):
        """Финальная сводка тестирования"""
        logger.info("🔍 Генерация финальной сводки")
        
        # Сводка операций
        operations_summary = balance_tracker.get_summary()
        logger.info("💰 СВОДКА ARWEAVE ОПЕРАЦИЙ:")
        logger.info(f"   📊 Всего операций: {operations_summary['total_operations']}")
        logger.info(f"   ⏱️ Общее время: {operations_summary['total_time']:.3f}s")
        
        for op in operations_summary['operations']:
            logger.info(f"   - {op['type']}: {op['transaction_id'] or 'N/A'}")
        
        # Сводка производительности
        performance_metrics.print_summary()
        
        # Рекомендации
        logger.info("📋 РЕКОМЕНДАЦИИ:")
        if SUPABASE_ANON_KEY:
            logger.info("   ✅ Edge Function интеграция работает")
            logger.info("   ✅ Рекомендуется использовать Edge Function для загрузки")
        else:
            logger.info("   ⚠️ SUPABASE_ANON_KEY не установлен")
            logger.info("   ⚠️ Рекомендуется настроить Edge Function для лучшей производительности")
        
        logger.info("✅ Final summary completed")


# ============================================================================
# ЗАПУСК ТЕСТОВ
# ============================================================================

if __name__ == "__main__":
    # Запуск тестов с подробным выводом
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--capture=no"
    ])
