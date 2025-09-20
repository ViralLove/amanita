# Конфигурация и переменные окружения для бота AMANITA 
import os
from dotenv import load_dotenv
import logging

# Подробное логирование
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения из .env файла (только если не установлены в системе)
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path, override=False)  # override=False - не перезаписывать системные переменные
logging.info(f"[CONFIG] Загружаем .env из: {env_path}")
logging.info(f"[CONFIG] Файл существует: {os.path.exists(env_path)}")

# Отладка переменных окружения
logging.info(f"[CONFIG] BLOCKCHAIN_PROFILE из env: {os.getenv('BLOCKCHAIN_PROFILE', 'НЕ УСТАНОВЛЕН')}")
logging.info(f"[CONFIG] WEB3_PROVIDER_URI из env: {os.getenv('WEB3_PROVIDER_URI', 'НЕ УСТАНОВЛЕН')}")
logging.info(f"[CONFIG] Все переменные env: {list(os.environ.keys())}")

# Базовые настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logging.error("Не найден TELEGRAM_BOT_TOKEN в .env файле")

# URL для WebApp кошелька
raw_wallet_url = os.getenv("WALLET_APP_URL")
logging.info(f"[CONFIG] Исходное значение WALLET_APP_URL из .env: {raw_wallet_url}")

WALLET_APP_URL = os.getenv("WALLET_APP_URL", "https://localhost:3000/")
logging.info(f"[CONFIG] Финальное значение WALLET_APP_URL: {WALLET_APP_URL}")

# Читаем напрямую из файла для проверки
if os.path.exists(env_path):
    try:
        with open(env_path, 'r') as f:
            env_content = f.read()
            logging.info(f"[CONFIG] Содержимое .env файла (без секретов):")
            for line in env_content.split('\n'):
                if line.strip() and not line.startswith('#'):
                    if "TOKEN" in line or "KEY" in line or "SECRET" in line:
                        key = line.split('=')[0]
                        logging.info(f"[CONFIG]   {key}=********")
                    elif "WALLET_APP_URL" in line:
                        logging.info(f"[CONFIG]   {line}")
                    else:
                        logging.info(f"[CONFIG]   {line}")
    except Exception as e:
        logging.error(f"[CONFIG] Ошибка при чтении .env файла: {e}")

# Настройки для блокчейна
BLOCKCHAIN_PROFILE = os.getenv("BLOCKCHAIN_PROFILE", "localhost")
ACTIVE_PROFILE = BLOCKCHAIN_PROFILE
RPC_URL = os.getenv("WEB3_PROVIDER_URI", "http://localhost:8545")

# Ключ продавца
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")
if not SELLER_PRIVATE_KEY:
    raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
if not SELLER_PRIVATE_KEY.startswith("0x"):
    SELLER_PRIVATE_KEY = f"0x{SELLER_PRIVATE_KEY}"

# API ключи для аутентификации (MVP)
AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "ak_seller_amanita_mvp_2024")
AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "sk_seller_secret_amanita_mvp_2024_secure_key")

# Supabase конфигурация для Edge Functions
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54321")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_ANON_KEY:
    logging.warning("SUPABASE_ANON_KEY не установлен в .env - Edge Functions могут не работать")

# ArWeave конфигурация
ARWEAVE_PRIVATE_KEY = os.getenv("ARWEAVE_PRIVATE_KEY")
if not ARWEAVE_PRIVATE_KEY:
    logging.warning("ARWEAVE_PRIVATE_KEY не установлен в .env - ArWeave операции могут не работать")

# Тип коммуникации с хранилищем (sync|async|hybrid)
STORAGE_COMMUNICATION_TYPE = os.getenv("STORAGE_COMMUNICATION_TYPE", "sync")
if STORAGE_COMMUNICATION_TYPE not in ["sync", "async", "hybrid"]:
    logging.warning(f"STORAGE_COMMUNICATION_TYPE '{STORAGE_COMMUNICATION_TYPE}' не поддерживается, используем 'sync'")
    STORAGE_COMMUNICATION_TYPE = "sync"
logging.info(f"[CONFIG] STORAGE_COMMUNICATION_TYPE: {STORAGE_COMMUNICATION_TYPE}")

# Адрес реестра контрактов
AMANITA_REGISTRY_CONTRACT_ADDRESS = os.getenv("AMANITA_REGISTRY_CONTRACT_ADDRESS")
if not AMANITA_REGISTRY_CONTRACT_ADDRESS:
    raise ValueError("AMANITA_REGISTRY_CONTRACT_ADDRESS не установлен в .env")

# Настройки путей
# Корневая папка приложения (bot для локальной разработки, app для продакшена)
APP_ROOT_DIR = os.getenv("APP_ROOT_DIR", "app")

# Параметризация по среде выполнения
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")  # local | prod

# Параметризация загрузки каталога на старте
LOAD_CATALOG = os.getenv("LOAD_CATALOG", "true").lower() in ["true", "1", "yes", "on"]
logging.info(f"[CONFIG] LOAD_CATALOG: {LOAD_CATALOG}")

if ENVIRONMENT == "local":
    # Для локальной разработки - используем корневую папку artifacts
    # Определяем правильный путь относительно корня проекта
    current_dir = os.path.dirname(os.path.abspath(__file__))  # bot/
    project_root = os.path.dirname(current_dir)  # корень проекта
    ABI_BASE_DIR = os.getenv("ABI_BASE_DIR", os.path.join(project_root, "artifacts", "contracts"))
    logging.info(f"[CONFIG] ENVIRONMENT: local")
    logging.info(f"[CONFIG] current_dir (bot/): {current_dir}")
    logging.info(f"[CONFIG] project_root: {project_root}")
    logging.info(f"[CONFIG] ABI_BASE_DIR: {ABI_BASE_DIR}")
else:
    # Для продакшена - используем папку app/artifacts
    ABI_BASE_DIR = os.getenv("ABI_BASE_DIR", f"{APP_ROOT_DIR}/artifacts/contracts")
    logging.info(f"[CONFIG] ENVIRONMENT: prod")
    logging.info(f"[CONFIG] ABI_BASE_DIR: {ABI_BASE_DIR}") 