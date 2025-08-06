"""
Общий модуль зависимостей для всего приложения AMANITA.
Содержит dependency providers для всех внешних сервисов.
"""

from bot.services.product.storage import ProductStorageService
from bot.services.core.blockchain import BlockchainService
from bot.services.core.api_key import ApiKeyService
from bot.services.core.account import AccountService
from bot.services.product.registry import ProductRegistryService
from bot.services.product.validation import ProductValidationService
from bot.services.core.ipfs_factory import IPFSFactory


def get_ipfs_storage():
    """Dependency provider для IPFS storage (результат IPFSFactory().get_storage())"""
    return IPFSFactory().get_storage()


def get_product_storage_service(storage_provider=None) -> ProductStorageService:
    """
    Dependency provider для ProductStorageService
    
    Args:
        storage_provider: Провайдер хранилища. Если None, создается через IPFSFactory.
    """
    return ProductStorageService(storage_provider=storage_provider)


def get_blockchain_service() -> BlockchainService:
    """Dependency provider для BlockchainService (синглтон)"""
    return BlockchainService()


def get_product_validation_service() -> ProductValidationService:
    """Dependency provider для ProductValidationService"""
    return ProductValidationService()


def get_ipfs_factory() -> IPFSFactory:
    """Dependency provider для IPFSFactory"""
    return IPFSFactory()


def get_account_service(
    blockchain_service: BlockchainService = None,
) -> AccountService:
    """Dependency provider для AccountService"""
    if blockchain_service is None:
        blockchain_service = get_blockchain_service()
    return AccountService(blockchain_service)


def get_api_key_service(
    blockchain_service: BlockchainService = None,
) -> ApiKeyService:
    """Dependency provider для ApiKeyService"""
    if blockchain_service is None:
        blockchain_service = get_blockchain_service()
    return ApiKeyService(blockchain_service)


def get_product_registry_service(
    blockchain_service: BlockchainService = None,
    storage_service: ProductStorageService = None,
    validation_service: ProductValidationService = None,
    account_service: AccountService = None,
) -> ProductRegistryService:
    """Dependency provider для ProductRegistryService"""
    if blockchain_service is None:
        blockchain_service = get_blockchain_service()
    if storage_service is None:
        storage_service = get_product_storage_service()
    if validation_service is None:
        validation_service = get_product_validation_service()
    if account_service is None:
        account_service = get_account_service(blockchain_service)
    
    return ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    ) 