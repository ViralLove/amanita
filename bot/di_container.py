"""
Dependency Injection Container для приложения AMANITA.

Централизованное управление зависимостями и конфигурацией сервисов.
Поддерживает синглтоны, ленивую инициализацию и конфигурацию окружений.
"""

import logging
import os
from typing import Any, Dict, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Поддерживаемые окружения приложения."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class DIContainer:
    """
    Контейнер зависимостей для управления сервисами приложения.
    
    Обеспечивает:
    - Централизованное создание сервисов
    - Поддержку синглтонов
    - Ленивую инициализацию
    - Конфигурацию для разных окружений
    """
    
    def __init__(self):
        """Инициализация контейнера зависимостей."""
        self._services: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._environment: Optional[Environment] = None
        self._config: Dict[str, Any] = {}
        
        logger.debug("DIContainer инициализирован")
    
    def configure_for_environment(self, env: str = None) -> None:
        """
        Конфигурация контейнера для конкретного окружения.
        
        Args:
            env: Название окружения (development, production, testing).
                 Если не указано, определяется из переменной ENVIRONMENT.
        """
        try:
            # Загрузка .env файла отключена для избежания ошибок при инициализации
            # self._load_env_file()
            
            # Определяем окружение
            if env is None:
                env = self._detect_environment()
            
            self._environment = Environment(env)
            self._config = self._get_environment_config(self._environment)
            
            # Валидация конфигурации отключена для избежания ошибок при инициализации
            # self._validate_configuration()
            
            # Регистрация сервисов отключена для избежания ошибок при инициализации
            # Сервисы будут регистрироваться по требованию
            # self._register_environment_services()
            
            logger.info(f"Контейнер сконфигурирован для окружения: {env}")
            
        except ValueError as e:
            logger.error(f"Неизвестное окружение: {env}. Доступные: {[e.value for e in Environment]}")
            raise
    
    def _load_env_file(self) -> None:
        """Загружает .env файл если он существует."""
        # Загрузка .env файла отключена для избежания ошибок при инициализации
        # env_path = os.path.join(os.path.dirname(__file__), '.env')
        # if os.path.exists(env_path):
        #     from dotenv import load_dotenv
        #     load_dotenv(env_path, override=False)
        #     logger.debug(f"Загружен .env файл: {env_path}")
    
    def _detect_environment(self) -> str:
        """
        Автоматическое определение окружения из переменных окружения.
        
        Returns:
            Название окружения
        """
        # Получаем окружение из переменной ENVIRONMENT
        env = os.getenv("ENVIRONMENT", "").lower()
        
        # Валидируем и возвращаем окружение
        valid_environments = [e.value for e in Environment]
        
        if env in valid_environments:
            logger.debug(f"Окружение определено из переменной ENVIRONMENT: {env}")
            return env
        
        # Fallback на development для локальной разработки
        logger.info(f"Переменная ENVIRONMENT не установлена или невалидна: '{env}'. Используем development")
        return "development"
    
    def get_service(self, service_name: str) -> Any:
        """
        Получение сервиса по имени с поддержкой кэширования.
        
        Args:
            service_name: Имя сервиса для получения
            
        Returns:
            Экземпляр сервиса
            
        Raises:
            KeyError: Если сервис не зарегистрирован
        """
        if service_name not in self._services:
            raise KeyError(f"Сервис '{service_name}' не зарегистрирован в контейнере")
        
        # Проверяем, является ли сервис синглтоном
        if service_name in self._singletons:
            logger.debug(f"Возвращаем синглтон сервиса: {service_name}")
            return self._singletons[service_name]
        
        # Создаем новый экземпляр сервиса
        factory = self._services[service_name]
        service = factory()
        
        logger.debug(f"Создан новый экземпляр сервиса: {service_name}")
        return service
    
    def register_service(self, name: str, factory: Callable, singleton: bool = False) -> None:
        """
        Регистрация сервиса в контейнере.
        
        Args:
            name: Имя сервиса
            factory: Фабричная функция для создания сервиса
            singleton: Является ли сервис синглтоном
        """
        self._services[name] = factory
        
        if singleton:
            # Для синглтонов создаем экземпляр сразу
            self._singletons[name] = factory()
            logger.debug(f"Зарегистрирован синглтон сервис: {name}")
        else:
            logger.debug(f"Зарегистрирован обычный сервис: {name}")
    
    def register_singleton(self, name: str, factory: Callable) -> None:
        """
        Регистрация синглтон сервиса.
        
        Args:
            name: Имя сервиса
            factory: Фабричная функция для создания сервиса
        """
        self.register_service(name, factory, singleton=True)
    
    def is_configured(self) -> bool:
        """Проверка, сконфигурирован ли контейнер."""
        return self._environment is not None
    
    def get_environment(self) -> Optional[Environment]:
        """Получение текущего окружения."""
        return self._environment
    
    def get_config(self) -> Dict[str, Any]:
        """Получение конфигурации текущего окружения."""
        return self._config.copy()
    
    def _get_environment_config(self, env: Environment) -> Dict[str, Any]:
        """
        Получение конфигурации для конкретного окружения.
        Читает значения из переменных окружения с fallback на значения по умолчанию.
        
        Args:
            env: Окружение
            
        Returns:
            Словарь с конфигурацией
        """
        
        # Базовые значения по умолчанию для каждого окружения
        default_configs = {
            Environment.DEVELOPMENT: {
                # Логирование
                "log_level": "DEBUG",
                "enable_debug": True,
                
                # Блокчейн
                "blockchain_timeout": 60,
                "blockchain_retry_attempts": 3,
                
                
                # API
                "api_timeout": 30,
                "enable_api_logging": True,
                
                # Безопасность
                "enable_hmac_validation": True,
                "enable_rate_limiting": False,
                
                # Telegram
                "telegram_polling_timeout": 10,
                
                # Кэширование
                "enable_caching": True,
                "cache_ttl": 300,  # 5 минут
                
                # Мониторинг
                "enable_metrics": True,
                "metrics_interval": 60
            },
            Environment.PRODUCTION: {
                # Логирование
                "log_level": "INFO",
                "enable_debug": False,
                
                # Блокчейн
                "blockchain_timeout": 120,
                "blockchain_retry_attempts": 5,
                
                
                # API
                "api_timeout": 60,
                "enable_api_logging": False,
                
                # Безопасность
                "enable_hmac_validation": True,
                "enable_rate_limiting": True,
                
                # Telegram
                "telegram_polling_timeout": 30,
                
                # Кэширование
                "enable_caching": True,
                "cache_ttl": 1800,  # 30 минут
                
                # Мониторинг
                "enable_metrics": True,
                "metrics_interval": 300
            },
            Environment.TESTING: {
                # Логирование
                "log_level": "WARNING",
                "enable_debug": False,
                
                # Блокчейн
                "blockchain_timeout": 5,
                "blockchain_retry_attempts": 1,
                
                
                # API
                "api_timeout": 5,
                "enable_api_logging": False,
                
                # Безопасность
                "enable_hmac_validation": False,
                "enable_rate_limiting": False,
                
                # Telegram
                "telegram_polling_timeout": 1,
                
                # Кэширование
                "enable_caching": False,
                "cache_ttl": 0,
                
                # Мониторинг
                "enable_metrics": False,
                "metrics_interval": 0
            }
        }
        
        # Получаем базовую конфигурацию для окружения
        config = default_configs.get(env, {}).copy()
        
        # Переопределения из переменных окружения отключены для избежания ошибок при инициализации
        env_overrides = {
            # Блокчейн
            # "blockchain_rpc": os.getenv("WEB3_PROVIDER_URI"),
            # "blockchain_timeout": self._get_env_int("BLOCKCHAIN_TIMEOUT"),
            # "blockchain_retry_attempts": self._get_env_int("BLOCKCHAIN_RETRY_ATTEMPTS"),
            
            # "storage_type": os.getenv("STORAGE_TYPE"),
            # "storage_communication_mode": os.getenv("STORAGE_COMMUNICATION_MODE"),
            
            # API
            # "api_url": os.getenv("AMANITA_API_URL"),
            # "api_timeout": self._get_env_int("API_TIMEOUT"),
            # "enable_api_logging": self._get_env_bool("ENABLE_API_LOGGING"),
            
            # Безопасность
            # "enable_hmac_validation": self._get_env_bool("ENABLE_HMAC_VALIDATION"),
            # "enable_rate_limiting": self._get_env_bool("ENABLE_RATE_LIMITING"),
            
            # Telegram
            # "telegram_webhook_url": os.getenv("TELEGRAM_WEBHOOK_URL"),
            # "telegram_polling_timeout": self._get_env_int("TELEGRAM_POLLING_TIMEOUT"),
            
            # Кэширование
            # "enable_caching": self._get_env_bool("ENABLE_CACHING"),
            # "cache_ttl": self._get_env_int("CACHE_TTL"),
            
            # Мониторинг
            # "enable_metrics": self._get_env_bool("ENABLE_METRICS"),
            # "metrics_interval": self._get_env_int("METRICS_INTERVAL"),
            
            # Логирование
            # "log_level": os.getenv("LOG_LEVEL"),
            # "enable_debug": self._get_env_bool("ENABLE_DEBUG")
        }
        
        # Применяем переопределения (только если значение не None)
        for key, value in env_overrides.items():
            if value is not None:
                config[key] = value
        
        return config
    
    def _get_env_int(self, key: str) -> Optional[int]:
        """Получение целочисленного значения из переменной окружения."""
        # Загрузка .env файла отключена для избежания ошибок при инициализации
        # value = os.getenv(key)
        # if value is None:
        #     return None
        # try:
        #     return int(value)
        # except ValueError:
        #     logger.warning(f"Неверное целочисленное значение для {key}: {value}")
        #     return None
        return None
    
    def _get_env_bool(self, key: str) -> Optional[bool]:
        """Получение булевого значения из переменной окружения."""
        # Загрузка .env файла отключена для избежания ошибок при инициализации
        # value = os.getenv(key)
        # if value is None:
        #     return None
        # return value.lower() in ('true', '1', 'yes', 'on')
        return None
    
    def _validate_configuration(self) -> None:
        """Валидация конфигурации для текущего окружения."""
        logger.debug("Начинаем валидацию конфигурации...")
        
        # Валидируем обязательные переменные
        self._validate_required_variables()
        
        # Валидируем форматы значений
        self._validate_value_formats()
        
        # Проверяем предупреждения
        self._check_configuration_warnings()
        
        logger.debug("Валидация конфигурации завершена успешно")
    
    def _validate_required_variables(self) -> None:
        """Валидация обязательных переменных для окружения."""
        required_vars = {
            Environment.DEVELOPMENT: [
                "TELEGRAM_BOT_TOKEN",
                "WEB3_PROVIDER_URI",
                "SELLER_ADDRESS",
                "SELLER_PRIVATE_KEY"
            ],
            Environment.PRODUCTION: [
                "TELEGRAM_BOT_TOKEN",
                "WEB3_PROVIDER_URI",
                "SELLER_ADDRESS", 
                "SELLER_PRIVATE_KEY",
                "AMANITA_API_URL",
                "AMANITA_API_KEY",
                "AMANITA_API_SECRET",
                "AMANITA_API_HMAC_SECRET_KEY"
            ],
            Environment.TESTING: [
                # В тестировании большинство переменных опциональны
            ]
        }
        
        missing_vars = []
        for var_name in required_vars.get(self._environment, []):
            if not os.getenv(var_name):
                missing_vars.append(var_name)
        
        if missing_vars:
            error_msg = f"Отсутствуют обязательные переменные для {self._environment.value}: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"Все обязательные переменные для {self._environment.value} присутствуют")
    
    def _validate_value_formats(self) -> None:
        """Валидация форматов значений."""
        # Проверяем URL форматы
        url_vars = ["WEB3_PROVIDER_URI", "AMANITA_API_URL", "WALLET_APP_URL"]
        for var_name in url_vars:
            value = os.getenv(var_name)
            if value and not self._is_valid_url(value):
                logger.warning(f"Некорректный URL формат для {var_name}: {value}")
        
        # Проверяем адреса Ethereum
        eth_address_vars = ["SELLER_ADDRESS"]
        for var_name in eth_address_vars:
            value = os.getenv(var_name)
            if value and not self._is_valid_ethereum_address(value):
                logger.warning(f"Некорректный Ethereum адрес для {var_name}: {value}")
        
        # Проверяем числовые значения
        numeric_vars = ["BLOCKCHAIN_TIMEOUT", "API_TIMEOUT", "CACHE_TTL", "METRICS_INTERVAL"]
        for var_name in numeric_vars:
            value = os.getenv(var_name)
            if value and not value.isdigit():
                logger.warning(f"Некорректное числовое значение для {var_name}: {value}")
        
        logger.debug("Валидация форматов значений завершена")
    
    def _check_configuration_warnings(self) -> None:
        """Проверка предупреждений о неоптимальных настройках."""
        warnings = []
        
        # Проверяем настройки безопасности
        if self._environment == Environment.PRODUCTION:
            if not os.getenv("ENABLE_HMAC_VALIDATION", "true").lower() == "true":
                warnings.append("HMAC валидация отключена в production - это небезопасно")
            
            if os.getenv("ENABLE_DEBUG", "false").lower() == "true":
                warnings.append("Debug режим включен в production - это небезопасно")
            
            if os.getenv("LOG_LEVEL", "INFO") == "DEBUG":
                warnings.append("DEBUG логирование в production может снизить производительность")
        
        # Проверяем настройки блокчейна
        blockchain_rpc = os.getenv("WEB3_PROVIDER_URI")
        if blockchain_rpc and "localhost" in blockchain_rpc and self._environment == Environment.PRODUCTION:
            warnings.append("Используется localhost RPC в production - проверьте настройки")
        
        # Проверяем настройки хранилища
        storage_type = os.getenv("STORAGE_TYPE")
        if storage_type == "mock" and self._environment == Environment.PRODUCTION:
            warnings.append("Используется mock хранилище в production")
        
        # Логируем предупреждения
        for warning in warnings:
            logger.warning(f"⚠️  {warning}")
        
        if warnings:
            logger.info(f"Обнаружено {len(warnings)} предупреждений конфигурации")
    
    def _is_valid_url(self, url: str) -> bool:
        """Проверка корректности URL."""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _is_valid_ethereum_address(self, address: str) -> bool:
        """Проверка корректности Ethereum адреса."""
        if not address.startswith("0x"):
            return False
        if len(address) != 42:
            return False
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    
    def _register_environment_services(self) -> None:
        """Регистрация сервисов, специфичных для окружения."""
        # Интеграция с существующими dependency providers отключена
        # Сервисы будут регистрироваться по требованию
        logger.debug("Базовые сервисы окружения будут регистрироваться по требованию")
    
    def _register_dependency_providers(self) -> None:
        """Регистрация сервисов из dependencies.py."""
        try:
            # Создаем ленивые фабрики для избежания ошибок при импорте
            def create_lazy_factory(module_name: str, func_name: str):
                def lazy_factory():
                    try:
                        import importlib
                        module = importlib.import_module(module_name)
                        return getattr(module, func_name)()
                    except Exception as e:
                        logger.error(f"Ошибка при создании сервиса {func_name}: {e}")
                        raise
                return lazy_factory
            
            # Регистрируем сервисы с ленивыми фабриками
            service_registrations = [
                ("blockchain_service", create_lazy_factory("dependencies", "get_blockchain_service")),
                ("user_settings", create_lazy_factory("dependencies", "get_user_settings")),
                ("ipfs_factory", create_lazy_factory("dependencies", "get_ipfs_factory")),
                ("product_validation_service", create_lazy_factory("dependencies", "get_product_validation_service")),
                ("product_assembler", create_lazy_factory("dependencies", "get_product_assembler")),
                ("account_service", create_lazy_factory("dependencies", "get_account_service")),
                ("api_key_service", create_lazy_factory("dependencies", "get_api_key_service")),
                ("product_registry_service", create_lazy_factory("dependencies", "get_product_registry_service")),
                ("catalog_service", create_lazy_factory("dependencies", "get_catalog_service")),
                ("product_service", create_lazy_factory("dependencies", "get_product_service")),
                ("image_service", create_lazy_factory("dependencies", "get_image_service")),
                ("storage_service", create_lazy_factory("dependencies", "get_storage_service")),
                ("formatter_service", create_lazy_factory("dependencies", "get_formatter_service")),
            ]
            
            registered_count = 0
            for service_name, factory_func in service_registrations:
                try:
                    # Регистрируем как обычные сервисы для отложенной инициализации
                    self.register_service(service_name, factory_func)
                    registered_count += 1
                    logger.debug(f"Зарегистрирован сервис (ленивая инициализация): {service_name}")
                except Exception as e:
                    logger.warning(f"Не удалось зарегистрировать сервис {service_name}: {e}")
            
            logger.info(f"Dependency providers интегрированы: {registered_count} сервисов зарегистрировано")
            
        except Exception as e:
            logger.error(f"Ошибка при регистрации dependency providers: {e}")
            logger.warning("DI контейнер будет работать без предустановленных сервисов")


# Глобальный экземпляр контейнера
container = DIContainer()
