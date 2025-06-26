# Конфигурация и переменные окружения для бота AMANITA 
import os
from dotenv import load_dotenv
import logging

# Подробное логирование
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения из .env файла
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
logging.info(f"[CONFIG] Загружаем .env из: {env_path}")
logging.info(f"[CONFIG] Файл существует: {os.path.exists(env_path)}")

# Базовые настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logging.error("Не найден TELEGRAM_BOT_TOKEN в .env файле")

# URL для WebApp кошелька
raw_wallet_url = os.getenv("WALLET_APP_URL")
logging.info(f"[CONFIG] Исходное значение WALLET_APP_URL из .env: {raw_wallet_url}")

WALLET_APP_URL = os.getenv("WALLET_APP_URL", "https://localhost:8080/")
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

# Адрес реестра контрактов
AMANITA_REGISTRY_CONTRACT_ADDRESS = os.getenv("AMANITA_REGISTRY_CONTRACT_ADDRESS")
if not AMANITA_REGISTRY_CONTRACT_ADDRESS:
    raise ValueError("AMANITA_REGISTRY_CONTRACT_ADDRESS не установлен в .env")

# Настройки путей
ABI_BASE_DIR = os.getenv("ABI_BASE_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts", "contracts")) 