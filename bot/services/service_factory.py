from services.core.blockchain import BlockchainService
from services.core.account import AccountService
from services.core.api_key import ApiKeyService
from services.product.registry import ProductRegistryService
from services.product.storage import ProductStorageService
from services.product.validation import ProductValidationService

class ServiceFactory:
    def __init__(self):
        # Используем синглтон BlockchainService
        self.blockchain = BlockchainService()

    def create_account_service(self):
        return AccountService(self.blockchain)
    
    def create_api_key_service(self):
        return ApiKeyService(self.blockchain)
    
    def create_product_registry_service(self):
        # Создаем зависимости для ProductRegistryService
        storage_service = ProductStorageService()
        validation_service = ProductValidationService()
        account_service = AccountService(self.blockchain)
        
        # Создаем ProductRegistryService с синглтоном BlockchainService и AccountService
        return ProductRegistryService(
            blockchain_service=self.blockchain,
            storage_service=storage_service,
            validation_service=validation_service,
            account_service=account_service
        )
    

    
    @classmethod
    def reset(cls):
        """Сброс синглтонов для тестирования"""
        BlockchainService.reset()