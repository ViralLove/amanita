"""
API-специфичный модуль зависимостей для FastAPI.
Использует общий модуль bot/dependencies.py и добавляет FastAPI Depends.
"""

from fastapi import Depends
from bot.dependencies import (
    get_product_storage_service as _get_product_storage_service,
    get_blockchain_service as _get_blockchain_service,
    get_api_key_service as _get_api_key_service,
    get_account_service as _get_account_service,
    get_product_registry_service as _get_product_registry_service,
    get_product_validation_service as _get_product_validation_service,
    get_ipfs_storage as _get_ipfs_storage,
)
from bot.services.product.storage import ProductStorageService
from bot.services.core.blockchain import BlockchainService
from bot.services.core.api_key import ApiKeyService
from bot.services.core.account import AccountService
from bot.services.product.registry import ProductRegistryService
from bot.services.product.validation import ProductValidationService


def get_ipfs_storage():
    """FastAPI dependency provider для IPFS storage"""
    return _get_ipfs_storage()


def get_product_storage_service(
    storage_provider=None,
) -> ProductStorageService:
    """FastAPI dependency provider для ProductStorageService"""
    return _get_product_storage_service(storage_provider=storage_provider)


def get_blockchain_service() -> BlockchainService:
    """FastAPI dependency provider для BlockchainService"""
    return _get_blockchain_service()


def get_product_validation_service() -> ProductValidationService:
    """FastAPI dependency provider для ProductValidationService"""
    return _get_product_validation_service()


def get_account_service(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
) -> AccountService:
    """FastAPI dependency provider для AccountService"""
    return _get_account_service(blockchain_service)


def get_api_key_service(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
) -> ApiKeyService:
    """FastAPI dependency provider для ApiKeyService"""
    return _get_api_key_service(blockchain_service)


def get_product_registry_service(
    blockchain_service: BlockchainService = Depends(get_blockchain_service),
    storage_service: ProductStorageService = Depends(get_product_storage_service),
    validation_service: ProductValidationService = Depends(get_product_validation_service),
) -> ProductRegistryService:
    """FastAPI dependency provider для ProductRegistryService"""
    # 🔧 ИСПРАВЛЕНО: Используем тот же синглтон, что и бот
    from bot.services.product.registry_singleton import product_registry_service
    return product_registry_service 