# Конфигурация и переменные окружения для бота AMANITA 
import os
from dotenv import load_dotenv
import logging

# Попытка импорта VaultService (опционально, только если hvac установлен)
try:
    from services.vault_service import VaultService, VaultServiceError
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    VaultService = None
    VaultServiceError = Exception
    logging.warning("[CONFIG] VaultService недоступен (hvac не установлен), используем только .env")

# Уровень логов из окружения (Railway: LOG_LEVEL=DEBUG)
_log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(level=_log_level)
logging.info("[CONFIG] LOG_LEVEL=%s (%s)", _log_level_name, logging.getLevelName(_log_level))

# Даже при DEBUG не выводим низкоуровневые HTTP-заголовки с токенами.
for _noisy in ("httpx", "httpcore", "hpack", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.INFO)


def _mask_rpc_uri(uri: str) -> str:
    """Маскирует чувствительную часть RPC URL в логах."""
    if not uri:
        return "НЕ УСТАНОВЛЕН"
    if "://" not in uri:
        return "***"
    scheme, rest = uri.split("://", 1)
    if "/" not in rest:
        return f"{scheme}://{rest}"
    host, path = rest.split("/", 1)
    if not path:
        return f"{scheme}://{host}"
    # Часто провайдеры добавляют API-key последним сегментом пути.
    parts = [p for p in path.split("/") if p]
    if not parts:
        return f"{scheme}://{host}/"
    if len(parts) == 1:
        return f"{scheme}://{host}/***"
    return f"{scheme}://{host}/{'/'.join(parts[:-1])}/***"

# Загружаем переменные окружения из .env файла (только если не установлены в системе)
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path, override=False)  # override=False - не перезаписывать системные переменные
logging.info(f"[CONFIG] Загружаем .env из: {env_path}")
logging.info(f"[CONFIG] Файл существует: {os.path.exists(env_path)}")

# Отладка переменных окружения
logging.info(f"[CONFIG] BLOCKCHAIN_PROFILE из env: {os.getenv('BLOCKCHAIN_PROFILE', 'НЕ УСТАНОВЛЕН')}")
logging.info(
    "[CONFIG] WEB3_PROVIDER_URI из env (masked): %s",
    _mask_rpc_uri(os.getenv("WEB3_PROVIDER_URI", "")),
)
logging.info("[CONFIG] Переменных окружения загружено: %s", len(os.environ))

# Базовые настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logging.error("Не найден TELEGRAM_BOT_TOKEN в .env файле")

# URL для WebApp кошелька
raw_wallet_url = os.getenv("WALLET_APP_URL")
logging.info(f"[CONFIG] Исходное значение WALLET_APP_URL из .env: {raw_wallet_url}")

WALLET_APP_URL = os.getenv("WALLET_APP_URL", "https://localhost:3000/")
logging.info(f"[CONFIG] Финальное значение WALLET_APP_URL: {WALLET_APP_URL}")

# Настройки для блокчейна
BLOCKCHAIN_PROFILE = os.getenv("BLOCKCHAIN_PROFILE", "localhost")
ACTIVE_PROFILE = BLOCKCHAIN_PROFILE
RPC_URL = os.getenv("WEB3_PROVIDER_URI", "http://localhost:8545")

# EVM chain id (десятичный): SSOT для кошелька, sign-requests, wallet-auth challenge.
# Должен совпадать с eth_chainId узла WEB3_PROVIDER_URI; BlockchainService проверяет при старте
# (отключение только через EVM_CHAIN_ID_SKIP_RPC_CHECK=1 — тесты/отладка).
_chain_id_raw = os.getenv("CHAIN_ID", "137").strip()
if not _chain_id_raw:
    raise ValueError("CHAIN_ID is set but empty; unset or set a decimal chain id (e.g. 137, 31337).")
try:
    CHAIN_ID_INT = int(_chain_id_raw)
except ValueError as e:
    raise ValueError(
        f"CHAIN_ID must be a decimal integer, got {_chain_id_raw!r}"
    ) from e
CHAIN_ID = _chain_id_raw
logging.info(
    "[CONFIG] CHAIN_ID=%s (must match eth_chainId of WEB3_PROVIDER_URI unless EVM_CHAIN_ID_SKIP_RPC_CHECK)",
    CHAIN_ID,
)

# Deployment profile (сеть/окружение деплоя). Источник секретов задаётся отдельно —
# см. SECRETS_PROVIDER (ниже); не смешивать с DEPLOYMENT_PROFILE.
DEPLOYMENT_PROFILE = os.getenv("DEPLOYMENT_PROFILE", "localhost")
logging.info(f"[CONFIG] DEPLOYMENT_PROFILE: {DEPLOYMENT_PROFILE}")

# ============================================================================
# SECRETS MANAGEMENT: SECRETS_PROVIDER (vault | env)
# ============================================================================

_ALLOWED_SECRETS_PROVIDERS = frozenset(("vault", "env"))


def _infer_secrets_provider() -> tuple[str, bool]:
    """
    Если SECRETS_PROVIDER не задан — inferred: polygon → vault (как раньше), иначе env.
    Returns: (provider, inferred)
    """
    if DEPLOYMENT_PROFILE == "polygon":
        return "vault", True
    return "env", True


def _resolve_secrets_provider() -> tuple[str, bool]:
    raw = os.getenv("SECRETS_PROVIDER", "").strip().lower()
    if not raw:
        provider, inferred = _infer_secrets_provider()
        logging.info(
            "[CONFIG] SECRETS_PROVIDER не задан; выбрано по умолчанию %r "
            "(DEPLOYMENT_PROFILE=%r). Задайте SECRETS_PROVIDER явно для фиксации режима.",
            provider,
            DEPLOYMENT_PROFILE,
        )
        return provider, True
    if raw not in _ALLOWED_SECRETS_PROVIDERS:
        raise ValueError(
            f"SECRETS_PROVIDER={raw!r} не поддерживается. Допустимо: vault, env."
        )
    logging.info(
        "[CONFIG] SECRETS_PROVIDER=%s (явно из окружения)", raw
    )
    return raw, False


SECRETS_PROVIDER, _ = _resolve_secrets_provider()


def _load_secrets_from_env():
    """Чтение SELLER_PRIVATE_KEY / ARWEAVE_PRIVATE_KEY из окружения."""
    seller = os.getenv("SELLER_PRIVATE_KEY")
    if not seller:
        raise ValueError(
            "SELLER_PRIVATE_KEY не установлен в окружении для SECRETS_PROVIDER=env"
        )
    arweave = os.getenv("ARWEAVE_PRIVATE_KEY")
    if not arweave:
        logging.warning(
            "ARWEAVE_PRIVATE_KEY не установлен — операции Arweave могут быть недоступны"
        )
    return seller, arweave


def _load_secrets_from_vault():
    """
    Загрузка секретов из HashiCorp Vault при SECRETS_PROVIDER=vault.

    Raises:
        VaultServiceError: Если Vault недоступен или секреты не найдены
    """
    if not VAULT_AVAILABLE:
        raise VaultServiceError(
            "VaultService недоступен (hvac не установлен). "
            "Установите: pip install hvac"
        )

    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    vault_path = os.getenv("VAULT_PATH", "secret/data/amanita")

    if not vault_addr:
        raise VaultServiceError(
            "VAULT_ADDR не установлен для SECRETS_PROVIDER=vault. "
            "Укажите URL Vault или переключитесь на SECRETS_PROVIDER=env."
        )

    if not vault_token:
        raise VaultServiceError(
            "VAULT_TOKEN не установлен для SECRETS_PROVIDER=vault. "
            "Укажите token или переключитесь на SECRETS_PROVIDER=env."
        )
    
    logging.info(f"[CONFIG] 🔐 Инициализация Vault: {vault_addr}")
    logging.info(f"[CONFIG] 🔐 Vault path: {vault_path}")
    
    try:
        vault = VaultService(
            vault_addr=vault_addr,
            vault_token=vault_token,
            vault_path=vault_path
        )
        
        # Загружаем секреты
        seller_key = vault.get_secret("SELLER_PRIVATE_KEY")
        arweave_key = vault.get_secret("ARWEAVE_PRIVATE_KEY")
        
        logging.info("[CONFIG] ✅ Секреты успешно загружены из Vault")
        return seller_key, arweave_key
        
    except VaultServiceError as e:
        logging.error(f"[CONFIG] ❌ Ошибка загрузки секретов из Vault: {e}")
        raise

# Ключи продавца / Arweave — по SECRETS_PROVIDER
if SECRETS_PROVIDER == "vault":
    logging.info("[CONFIG] 🔐 Секреты: Vault (SECRETS_PROVIDER=vault)")
    SELLER_PRIVATE_KEY, ARWEAVE_PRIVATE_KEY = _load_secrets_from_vault()
else:
    logging.info("[CONFIG] 📁 Секреты: переменные окружения (SECRETS_PROVIDER=env)")
    SELLER_PRIVATE_KEY, ARWEAVE_PRIVATE_KEY = _load_secrets_from_env()

# Нормализация SELLER_PRIVATE_KEY (добавляем 0x префикс если отсутствует)
if SELLER_PRIVATE_KEY and not SELLER_PRIVATE_KEY.startswith("0x"):
    SELLER_PRIVATE_KEY = f"0x{SELLER_PRIVATE_KEY}"

# API ключи для аутентификации (MVP)
AMANITA_API_KEY = os.getenv("AMANITA_API_KEY", "ak_seller_amanita_mvp_2024")
AMANITA_API_SECRET = os.getenv("AMANITA_API_SECRET", "sk_seller_secret_amanita_mvp_2024_secure_key")

# Supabase конфигурация для Edge Functions
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54321")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_ANON_KEY:
    logging.warning("SUPABASE_ANON_KEY не установлен в .env - Edge Functions могут не работать")

# Примечание: ARWEAVE_PRIVATE_KEY теперь загружается через profile-based logic выше
# (вместе с SELLER_PRIVATE_KEY)

# Тип коммуникации с хранилищем (sync|async|hybrid)
STORAGE_COMMUNICATION_TYPE = os.getenv("STORAGE_COMMUNICATION_TYPE", "sync")
if STORAGE_COMMUNICATION_TYPE not in ["sync", "async", "hybrid"]:
    logging.warning(f"STORAGE_COMMUNICATION_TYPE '{STORAGE_COMMUNICATION_TYPE}' не поддерживается, используем 'sync'")
    STORAGE_COMMUNICATION_TYPE = "sync"
logging.info(f"[CONFIG] STORAGE_COMMUNICATION_TYPE: {STORAGE_COMMUNICATION_TYPE}")

# Адрес реестра контрактов
MAGIC_REGISTRY_CONTRACT_ADDRESS = os.getenv("MAGIC_REGISTRY_CONTRACT_ADDRESS")
if not MAGIC_REGISTRY_CONTRACT_ADDRESS:
    raise ValueError("MAGIC_REGISTRY_CONTRACT_ADDRESS не установлен в .env")

# Настройки путей
# Корневая папка приложения (bot для локальной разработки, app для продакшена)
APP_ROOT_DIR = os.getenv("APP_ROOT_DIR", "app")

# Параметризация по среде выполнения
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")  # local | prod

# Параметризация загрузки каталога на старте
LOAD_CATALOG = os.getenv("LOAD_CATALOG", "true").lower() in ["true", "1", "yes", "on"]
logging.info(f"[CONFIG] LOAD_CATALOG: {LOAD_CATALOG}")


def _resolve_abi_base_dir(path: str) -> str:
    """
    Абсолютный путь для ABI_BASE_DIR.
    На Railway cwd часто /app; ошибочное значение app/artifacts/contracts давало бы /app/app/artifacts/contracts.
    """
    if not path:
        return path
    if os.path.isabs(path):
        return os.path.normpath(path)
    cwd = os.getcwd()
    rel = path.replace("\\", "/")
    if rel.startswith("app/") and cwd.rstrip(os.sep) == "/app":
        inner = rel[4:].lstrip("/")
        fixed = os.path.normpath(os.path.join(cwd, inner))
        if os.path.isdir(fixed):
            logging.info(
                "[CONFIG] ABI_BASE_DIR: нормализация %r → %r (cwd=%r, убран лишний префикс app/)",
                path,
                fixed,
                cwd,
            )
            return fixed
    return os.path.normpath(os.path.join(cwd, path))


if ENVIRONMENT == "local":
    # Для локальной разработки - используем корневую папку artifacts
    # Определяем правильный путь относительно корня проекта
    current_dir = os.path.dirname(os.path.abspath(__file__))  # bot/
    project_root = os.path.dirname(current_dir)  # корень проекта
    ABI_BASE_DIR = os.getenv("ABI_BASE_DIR", os.path.join(project_root, "artifacts", "contracts"))
    if ABI_BASE_DIR and not os.path.isabs(ABI_BASE_DIR):
        ABI_BASE_DIR = _resolve_abi_base_dir(ABI_BASE_DIR)
    logging.info(f"[CONFIG] ENVIRONMENT: local")
    logging.info(f"[CONFIG] current_dir (bot/): {current_dir}")
    logging.info(f"[CONFIG] project_root: {project_root}")
    logging.info(f"[CONFIG] ABI_BASE_DIR: {ABI_BASE_DIR}")
else:
    # Для продакшена - используем папку app/artifacts
    ABI_BASE_DIR = os.getenv("ABI_BASE_DIR", f"{APP_ROOT_DIR}/artifacts/contracts")
    if ABI_BASE_DIR and not os.path.isabs(ABI_BASE_DIR):
        ABI_BASE_DIR = _resolve_abi_base_dir(ABI_BASE_DIR)
    logging.info(f"[CONFIG] ENVIRONMENT: prod")
    logging.info(f"[CONFIG] ABI_BASE_DIR: {ABI_BASE_DIR}")