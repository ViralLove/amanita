"""
HashiCorp Vault Service для безопасного получения секретов в production окружении.

Используется для Polygon profile для загрузки приватных ключей из Vault вместо
прямого хранения в environment variables.

Для localhost profile ключи по-прежнему загружаются из .env файла через python-dotenv.

Usage:
    from services.vault_service import VaultService
    
    vault = VaultService(
        vault_addr="https://vault.example.com:8200",
        vault_token="s.xxxxxxxxxxxxxxxxxxxxxx"
    )
    
    seller_key = vault.get_secret("SELLER_PRIVATE_KEY")
    arweave_key = vault.get_secret("ARWEAVE_PRIVATE_KEY")

Author: eslinko
Date: 2025-10-10
Related: ADR-001-hashicorp-vault-integration.md
"""

import logging
from typing import Optional, Dict, Any

try:
    import hvac
    from hvac.exceptions import VaultError, InvalidPath, Unauthorized
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False
    hvac = None
    VaultError = Exception
    InvalidPath = Exception
    Unauthorized = Exception

logger = logging.getLogger(__name__)


class VaultServiceError(Exception):
    """Базовый класс для ошибок VaultService."""
    pass


class VaultConnectionError(VaultServiceError):
    """Ошибка подключения к Vault."""
    pass


class VaultAuthenticationError(VaultServiceError):
    """Ошибка аутентификации в Vault."""
    pass


class VaultSecretNotFoundError(VaultServiceError):
    """Секрет не найден в Vault."""
    pass


class VaultService:
    """
    Сервис для работы с HashiCorp Vault.
    
    Attributes:
        vault_addr (str): URL адрес Vault сервера
        vault_token (str): Token для аутентификации
        vault_path (str): Путь к секретам в Vault (default: "secret/data/amanita")
        client (hvac.Client): HVAC клиент для работы с Vault
    """
    
    def __init__(
        self, 
        vault_addr: str, 
        vault_token: str,
        vault_path: str = "secret/data/amanita",
        verify_ssl: bool = True
    ):
        """
        Инициализация VaultService.
        
        Args:
            vault_addr: URL адрес Vault сервера (например: https://vault.example.com:8200)
            vault_token: Token для аутентификации в Vault
            vault_path: Путь к секретам в Vault KV v2 (default: secret/data/amanita)
            verify_ssl: Проверять SSL сертификат (default: True, для production)
            
        Raises:
            VaultServiceError: Если hvac не установлен
            VaultConnectionError: Если не удалось подключиться к Vault
            VaultAuthenticationError: Если токен невалидный
        """
        if not HVAC_AVAILABLE:
            raise VaultServiceError(
                "hvac library не установлена. Выполните: pip install hvac"
            )
        
        if not vault_addr:
            raise VaultServiceError("vault_addr обязателен")
        
        if not vault_token:
            raise VaultServiceError("vault_token обязателен")
        
        self.vault_addr = vault_addr
        self.vault_token = vault_token
        self.vault_path = vault_path
        self.verify_ssl = verify_ssl
        
        logger.info(f"Инициализация VaultService: {vault_addr} (path: {vault_path})")
        
        try:
            self.client = hvac.Client(
                url=vault_addr,
                token=vault_token,
                verify=verify_ssl
            )
            
            # Проверяем подключение и аутентификацию
            if not self.client.is_authenticated():
                raise VaultAuthenticationError(
                    f"Не удалось аутентифицироваться в Vault. "
                    f"Проверьте VAULT_TOKEN. "
                    f"Vault addr: {vault_addr}"
                )
            
            logger.info("✅ VaultService успешно инициализирован и аутентифицирован")
            
        except Unauthorized as e:
            raise VaultAuthenticationError(
                f"Vault authentication failed: {str(e)}"
            ) from e
        except Exception as e:
            raise VaultConnectionError(
                f"Не удалось подключиться к Vault: {str(e)}"
            ) from e
    
    def get_secret(
        self, 
        secret_key: str,
        vault_path: Optional[str] = None,
        default: Optional[str] = None
    ) -> str:
        """
        Получить секрет из Vault.
        
        Args:
            secret_key: Ключ секрета (например: "SELLER_PRIVATE_KEY")
            vault_path: Опциональный путь к секретам (по умолчанию self.vault_path)
            default: Значение по умолчанию, если секрет не найден
            
        Returns:
            str: Значение секрета
            
        Raises:
            VaultSecretNotFoundError: Если секрет не найден и default=None
            VaultConnectionError: Если не удалось получить секрет
        """
        path = vault_path or self.vault_path
        
        logger.debug(f"Получение секрета '{secret_key}' из Vault path: {path}")
        
        try:
            # Для KV v2 используем secrets.kv.v2.read_secret_version
            # Путь должен быть в формате "secret/data/amanita" для KV v2
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path.replace("secret/data/", "")  # KV v2 API автоматически добавляет /data
            )
            
            if not response or 'data' not in response:
                raise VaultSecretNotFoundError(
                    f"Vault response не содержит 'data'. Path: {path}"
                )
            
            data = response['data']['data']
            
            if secret_key not in data:
                if default is not None:
                    logger.warning(
                        f"Секрет '{secret_key}' не найден в Vault path '{path}', "
                        f"используется default значение"
                    )
                    return default
                
                available_keys = list(data.keys())
                raise VaultSecretNotFoundError(
                    f"Секрет '{secret_key}' не найден в Vault path '{path}'. "
                    f"Доступные ключи: {available_keys}"
                )
            
            logger.debug(f"✅ Секрет '{secret_key}' успешно получен из Vault")
            return data[secret_key]
            
        except InvalidPath as e:
            raise VaultSecretNotFoundError(
                f"Vault path не найден: {path}. Error: {str(e)}"
            ) from e
        except VaultError as e:
            raise VaultConnectionError(
                f"Ошибка при получении секрета из Vault: {str(e)}"
            ) from e
        except Exception as e:
            raise VaultConnectionError(
                f"Неожиданная ошибка при получении секрета: {str(e)}"
            ) from e
    
    def get_all_secrets(self, vault_path: Optional[str] = None) -> Dict[str, str]:
        """
        Получить все секреты из указанного path.
        
        Args:
            vault_path: Опциональный путь к секретам (по умолчанию self.vault_path)
            
        Returns:
            Dict[str, str]: Словарь всех секретов
            
        Raises:
            VaultConnectionError: Если не удалось получить секреты
        """
        path = vault_path or self.vault_path
        
        logger.debug(f"Получение всех секретов из Vault path: {path}")
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path.replace("secret/data/", "")
            )
            
            if not response or 'data' not in response:
                raise VaultConnectionError(
                    f"Vault response не содержит 'data'. Path: {path}"
                )
            
            data = response['data']['data']
            logger.debug(f"✅ Получено {len(data)} секретов из Vault")
            return data
            
        except VaultError as e:
            raise VaultConnectionError(
                f"Ошибка при получении секретов из Vault: {str(e)}"
            ) from e
    
    def healthcheck(self) -> Dict[str, Any]:
        """
        Проверка состояния Vault и подключения.
        
        Returns:
            Dict с информацией о состоянии:
            {
                "connected": bool,
                "authenticated": bool,
                "vault_addr": str,
                "vault_path": str,
                "error": Optional[str]
            }
        """
        result = {
            "connected": False,
            "authenticated": False,
            "vault_addr": self.vault_addr,
            "vault_path": self.vault_path,
            "error": None
        }
        
        try:
            # Проверяем аутентификацию
            result["authenticated"] = self.client.is_authenticated()
            
            # Проверяем подключение (пытаемся прочитать секреты)
            self.get_all_secrets()
            result["connected"] = True
            
            logger.info("✅ Vault healthcheck passed")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Vault healthcheck failed: {str(e)}")
        
        return result
    
    def __repr__(self) -> str:
        """Строковое представление VaultService."""
        return (
            f"VaultService(vault_addr='{self.vault_addr}', "
            f"vault_path='{self.vault_path}', "
            f"authenticated={self.client.is_authenticated() if self.client else False})"
        )


# Convenience function для быстрого создания VaultService из environment variables
def create_vault_service_from_env() -> VaultService:
    """
    Создать VaultService используя environment variables.
    
    Ожидаемые переменные:
        VAULT_ADDR: URL адрес Vault сервера
        VAULT_TOKEN: Token для аутентификации
        VAULT_PATH: (optional) Путь к секретам (default: "secret/data/amanita")
        VAULT_VERIFY_SSL: (optional) Проверять SSL (default: "true")
    
    Returns:
        VaultService: Инициализированный сервис
        
    Raises:
        VaultServiceError: Если необходимые переменные не заданы
    """
    import os
    
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    vault_path = os.getenv("VAULT_PATH", "secret/data/amanita")
    verify_ssl = os.getenv("VAULT_VERIFY_SSL", "true").lower() == "true"
    
    if not vault_addr:
        raise VaultServiceError(
            "VAULT_ADDR environment variable не задана. "
            "Укажите URL адрес Vault сервера."
        )
    
    if not vault_token:
        raise VaultServiceError(
            "VAULT_TOKEN environment variable не задана. "
            "Укажите token для аутентификации в Vault."
        )
    
    return VaultService(
        vault_addr=vault_addr,
        vault_token=vault_token,
        vault_path=vault_path,
        verify_ssl=verify_ssl
    )


if __name__ == "__main__":
    # Простой тест для проверки работы VaultService
    import sys
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        vault = create_vault_service_from_env()
        print(f"\n{vault}\n")
        
        # Healthcheck
        health = vault.healthcheck()
        print(f"Healthcheck: {health}\n")
        
        if health["connected"] and health["authenticated"]:
            # Пробуем получить тестовый секрет
            print("Пробуем получить SELLER_PRIVATE_KEY...")
            seller_key = vault.get_secret("SELLER_PRIVATE_KEY")
            print(f"✅ SELLER_PRIVATE_KEY получен (длина: {len(seller_key)} символов)\n")
        else:
            print(f"❌ Vault не доступен: {health.get('error')}")
            sys.exit(1)
            
    except VaultServiceError as e:
        print(f"❌ VaultService Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)

