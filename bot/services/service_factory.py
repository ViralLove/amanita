from bot.services.core.blockchain import BlockchainService
from bot.services.core.account import AccountService
from bot.services.product.registry import ProductRegistryService
from bot.services.product.storage import ProductStorageService
from bot.services.product.validation import ProductValidationService

class ServiceFactory:
    def __init__(self):
        # Используем синглтон BlockchainService
        self.blockchain = BlockchainService()

    def create_account_service(self):
        return AccountService(self.blockchain)
    
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