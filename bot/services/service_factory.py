from services.core.blockchain import BlockchainService
from services.core.account import AccountService
from services.core.api_key import ApiKeyService
from services.product.registry import ProductRegistryService
from services.product.storage import ProductStorageService
from services.product.validation import ProductValidationService
from services.common.translation_cache_service import TranslationCacheService
from services.common.fallback_localization_service import FallbackLocalizationService
from services.common.multilingual_ipfs_service import MultilingualIPFSService
from services.common.localization_service import LocalizationService
from services.core.ipfs_factory import IPFSFactory

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

    def create_activity_registry_service(self):
        """
        ActivityRegistryService — тот же граф, что собирает api.dependencies (мок Activities API).
        Не использует синглтоны FastAPI: свежие ActivityStorage / StubPushSender / PayloadCache и
        локальный PrepareResolveService — для скриптов и изоляции; HTTP-путь — get_activity_registry_service.
        """
        from api.services import ActivityStorage
        from services.core.storage.ar_weave import ArWeaveUploader
        from services.core.supabase import SupabaseService
        from services.upload.upload_service import UploadService
        from services.upload.storage import PrepareResolveService
        from services.wallet_push import PayloadCache, StubPushSender
        from services.application.activity.factory import build_activity_registry_service

        storage = ActivityStorage()
        upload_svc = UploadService(SupabaseService())
        prepare = PrepareResolveService(upload_svc, ArWeaveUploader())
        push = StubPushSender()
        cache = PayloadCache()
        return build_activity_registry_service(
            storage=storage,
            prepare_resolve=prepare,
            push_sender=push,
            payload_cache=cache,
        )
    
    def create_localization_service(self, lang: str = 'ru') -> LocalizationService:
        """
        Создает LocalizationService с полной DI цепочкой зависимостей.
        
        Все зависимости (cache_service, fallback_service, blockchain_service) 
        передаются только в MultilingualIPFSService, который уже инкапсулирует 
        всю логику работы с IPFS, кэшированием и fallback.
        
        Args:
            lang: Язык локализации (по умолчанию 'ru')
            
        Returns:
            LocalizationService: Сервис локализации с IPFS/Blockchain/Cache/Fallback
        """
        # 1. Создаем TranslationCacheService (можно кэшировать, но для простоты создаём каждый раз)
        cache_service = TranslationCacheService(cache_dir="cache/translations", default_ttl=3600)
        
        # 2. Создаем FallbackLocalizationService (singleton по логике, но можно создавать каждый раз)
        fallback_service = FallbackLocalizationService(default_language='ru')
        
        # 3. Создаем IPFSFactory (можно кэшировать в ServiceFactory, но пока создаём каждый раз)
        ipfs_factory = IPFSFactory()
        # 3.1 SSOT: один ProductStorageService для download_json(cid)
        storage_service = ProductStorageService(storage_provider=ipfs_factory.get_storage())
        
        # 4. Создаем MultilingualIPFSService с полной DI цепочкой
        # Он уже содержит cache_service, fallback_service, blockchain_service
        ipfs_service = MultilingualIPFSService(
            storage_service=storage_service,
            cache_service=cache_service,
            fallback_service=fallback_service,
            blockchain_service=self.blockchain
        )
        
        # 6. Создаем LocalizationService
        # Все зависимости (cache_service, fallback_service, blockchain_service) уже инкапсулированы в ipfs_service.
        # cache_service и fallback_service передаём для ProductLocalizationService/ComponentLocalizationService,
        # которые используют их напрямую (кэш полей отдельно, fallback стратегии).
        # TODO: В будущем можно рефакторить ProductLocalizationService/ComponentLocalizationService 
        # чтобы использовать только ipfs_service и убрать дублирование зависимостей.
        localization_service = LocalizationService(
            lang=lang,
            cache_service=cache_service,  # Используется напрямую в ProductLocalizationService (кэш полей)
            fallback_service=fallback_service,  # Используется напрямую в ProductLocalizationService (fallback)
            ipfs_service=ipfs_service  # Основной сервис (содержит cache_service, fallback_service, blockchain_service)
        )
        
        return localization_service

    
    @classmethod
    def reset(cls):
        """Сброс синглтонов для тестирования"""
        BlockchainService.reset()