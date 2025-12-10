"""
Фабрика для создания тестовых сервисов с правильно замокированными зависимостями.

Обеспечивает:
- Единый источник создания тестовых сервисов
- Правильную изоляцию зависимостей (нет реальных подключений к Web3, IPFS и т.д.)
- Легкое переопределение зависимостей для конкретных тестов
- Отсутствие утечек зависимостей между тестами
"""

from typing import Optional, Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock
import logging

logger = logging.getLogger(__name__)


class TestServiceFactory:
    """
    Фабрика тестовых сервисов для unit тестов.
    
    Обеспечивает создание сервисов с правильно замокированными зависимостями,
    предотвращая реальные подключения к внешним сервисам (Web3, IPFS и т.д.).
    """
    
    @staticmethod
    def create_mock_blockchain_service() -> Mock:
        """
        Создает мок BlockchainService.
        
        Returns:
            Mock: Мок BlockchainService с базовой функциональностью для тестов.
        """
        mock_blockchain = Mock()
        
        # Базовые методы для работы с продуктами
        mock_blockchain.get_all_products = AsyncMock(return_value=[])
        mock_blockchain.get_product = AsyncMock(return_value=None)
        mock_blockchain.create_product = AsyncMock(return_value=1)
        mock_blockchain.update_product_status = AsyncMock(return_value=True)
        
        # Методы для работы с компонентами
        mock_blockchain.get_all_components = AsyncMock(return_value=[])
        mock_blockchain.get_component = AsyncMock(return_value=None)
        
        # Методы для работы с контрактами
        mock_blockchain.get_complex_field_cid = Mock(return_value=None)
        mock_blockchain.get_simple_field_cid = Mock(return_value=None)
        
        logger.debug("✅ Создан mock_blockchain_service")
        return mock_blockchain
    
    @staticmethod
    def create_mock_storage_service() -> Mock:
        """
        Создает мок ProductStorageService (IPFS/Arweave storage).
        
        Returns:
            Mock: Мок ProductStorageService с базовой функциональностью для тестов.
        """
        mock_storage = Mock()
        
        # Базовые методы для работы с хранилищем
        mock_storage.download_json = Mock(return_value={})
        mock_storage.upload_json = AsyncMock(return_value="QmTestCID123456789")
        mock_storage.download_file = Mock(return_value=b"")
        mock_storage.upload_file = AsyncMock(return_value="QmTestCID123456789")
        
        logger.debug("✅ Создан mock_storage_service")
        return mock_storage
    
    @staticmethod
    def create_mock_validation_service() -> Mock:
        """
        Создает мок ProductValidationService.
        
        Returns:
            Mock: Мок ProductValidationService с базовой функциональностью для тестов.
        """
        mock_validation = Mock()
        
        # Базовые методы для валидации
        mock_validation.validate_product_data = AsyncMock(return_value=Mock(is_valid=True))
        mock_validation.validate_product = Mock(return_value=Mock(is_valid=True))
        
        logger.debug("✅ Создан mock_validation_service")
        return mock_validation
    
    @staticmethod
    def create_mock_account_service(blockchain_service: Optional[Mock] = None) -> Mock:
        """
        Создает мок AccountService.
        
        Args:
            blockchain_service: Опциональный мок BlockchainService для AccountService.
        
        Returns:
            Mock: Мок AccountService с базовой функциональностью для тестов.
        """
        mock_account = Mock()
        
        # Базовые методы для работы с аккаунтами
        mock_account.get_account = Mock(return_value=None)
        mock_account.get_seller_account = Mock(return_value=None)
        
        logger.debug("✅ Создан mock_account_service")
        return mock_account
    
    @staticmethod
    def create_mock_component_service() -> Mock:
        """
        Создает мок ComponentService.
        
        Returns:
            Mock: Мок ComponentService с базовой функциональностью для тестов.
        """
        mock_component = Mock()
        
        # Базовые методы для работы с компонентами
        mock_component.get_component_description = Mock(return_value=None)
        mock_component.get_all_components = AsyncMock(return_value=[])
        mock_component.get_component = AsyncMock(return_value=None)
        
        logger.debug("✅ Создан mock_component_service")
        return mock_component
    
    @staticmethod
    def create_mock_assembler(component_service: Optional[Mock] = None) -> Mock:
        """
        Создает мок ProductAssembler.
        
        Args:
            component_service: Опциональный мок ComponentService для ProductAssembler.
                              Если не передан, создается новый мок.
        
        Returns:
            Mock: Мок ProductAssembler с базовой функциональностью для тестов.
        """
        if component_service is None:
            component_service = TestServiceFactory.create_mock_component_service()
        
        mock_assembler = Mock()
        mock_assembler.component_service = component_service
        
        # Базовые методы для сборки продуктов
        mock_assembler.assemble_product = AsyncMock(return_value=None)
        mock_assembler._extract_blockchain_data = Mock(return_value=None)
        mock_assembler._validate_component_ids_match = Mock(return_value=True)
        
        logger.debug("✅ Создан mock_assembler")
        return mock_assembler
    
    @staticmethod
    def create_product_registry_service(
        blockchain_service: Optional[Mock] = None,
        storage_service: Optional[Mock] = None,
        validation_service: Optional[Mock] = None,
        account_service: Optional[Mock] = None,
        assembler: Optional[Mock] = None,
        component_service: Optional[Mock] = None,
        **kwargs
    ):
        """
        Создает ProductRegistryService с правильно замокированными зависимостями.
        
        Все зависимости создаются как моки, предотвращая реальные подключения
        к внешним сервисам (Web3, IPFS и т.д.).
        
        Args:
            blockchain_service: Опциональный мок BlockchainService.
                               Если не передан, создается новый мок.
            storage_service: Опциональный мок ProductStorageService.
                           Если не передан, создается новый мок.
            validation_service: Опциональный мок ProductValidationService.
                              Если не передан, создается новый мок.
            account_service: Опциональный мок AccountService.
                           Если не передан, создается новый мок.
            assembler: Опциональный мок ProductAssembler.
                      Если не передан, создается новый мок с mock_component_service.
            component_service: Опциональный мок ComponentService.
                              Если не передан и assembler не передан, создается новый мок.
            **kwargs: Дополнительные параметры для ProductRegistryService (если нужны).
        
        Returns:
            ProductRegistryService: Экземпляр ProductRegistryService со всеми замокированными зависимостями.
        
        Example:
            >>> # Создание с дефолтными моками
            >>> registry = TestServiceFactory.create_product_registry_service()
            >>> 
            >>> # Создание с переопределенным blockchain_service
            >>> custom_blockchain = Mock()
            >>> custom_blockchain.get_all_products = AsyncMock(return_value=[...])
            >>> registry = TestServiceFactory.create_product_registry_service(
            ...     blockchain_service=custom_blockchain
            ... )
        """
        from bot.services.product.registry import ProductRegistryService
        
        # Создаем моки для всех зависимостей, если не переданы
        if blockchain_service is None:
            blockchain_service = TestServiceFactory.create_mock_blockchain_service()
        
        if storage_service is None:
            storage_service = TestServiceFactory.create_mock_storage_service()
        
        if validation_service is None:
            validation_service = TestServiceFactory.create_mock_validation_service()
        
        if account_service is None:
            account_service = TestServiceFactory.create_mock_account_service(blockchain_service)
        
        if assembler is None:
            # Создаем mock_component_service для assembler
            # Если component_service не передан, создаем новый мок
            if component_service is None:
                component_service = TestServiceFactory.create_mock_component_service()
            assembler = TestServiceFactory.create_mock_assembler(component_service)
        
        # Создаем ProductRegistryService с замокированными зависимостями
        # Важно: передаем все зависимости явно, чтобы избежать создания реальных сервисов
        registry_service = ProductRegistryService(
            blockchain_service=blockchain_service,
            storage_service=storage_service,
            validation_service=validation_service,
            account_service=account_service,
            assembler=assembler,
            **kwargs
        )
        
        logger.debug("✅ Создан ProductRegistryService с замокированными зависимостями")
        return registry_service
    
    @staticmethod
    def create_mock_localization_service() -> Mock:
        """
        Создает мок LocalizationService.
        
        Returns:
            Mock: Мок LocalizationService с базовой функциональностью для тестов.
        """
        from bot.services.common.localization_service import LocalizationService
        
        mock_localization = Mock(spec=LocalizationService)
        
        # Базовые методы для локализации
        mock_localization.get_translation = Mock(return_value="Mock Translation")
        mock_localization.get = Mock(return_value="Mock Value")
        mock_localization.t = Mock(return_value="Mock Translation")
        mock_localization.get_localized_text = Mock(return_value="Mock Localized Text")
        
        # Методы для работы с языками
        mock_localization.lang = "ru"
        mock_localization.get_language = Mock(return_value="ru")
        mock_localization.set_language = Mock()
        mock_localization.switch_language = Mock()
        
        # Атрибуты для дочерних сервисов (используются в LocalizationService)
        mock_localization.product_localization = Mock()
        mock_localization.component_localization = Mock()
        
        logger.debug("✅ Создан mock_localization_service")
        return mock_localization
    
    @staticmethod
    def create_mock_service_factory(blockchain_service: Optional[Mock] = None) -> Mock:
        """
        Создает мок ServiceFactory с использованием моков.
        
        Args:
            blockchain_service: Опциональный мок BlockchainService.
                               Если не передан, создается через create_mock_blockchain_service().
        
        Returns:
            Mock: Мок ServiceFactory с моками для всех зависимостей.
        """
        if blockchain_service is None:
            blockchain_service = TestServiceFactory.create_mock_blockchain_service()
        
        mock_factory = Mock()
        mock_factory.blockchain = blockchain_service
        
        # Мокируем create_localization_service для возврата мока
        mock_factory.create_localization_service = Mock(
            return_value=TestServiceFactory.create_mock_localization_service()
        )
        
        logger.debug("✅ Создан mock_service_factory")
        return mock_factory

