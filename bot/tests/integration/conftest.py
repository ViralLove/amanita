import pytest

from tests.integration.ipfs_stub import IPFSFactoryStub
from tests.integration.blockchain_stub import BlockchainServiceStub, AmanitaInternationalContractStub
from services.common.translation_cache_service import TranslationCacheService
from services.common.multilingual_ipfs_service import MultilingualIPFSService
from services.common.localization_service import LocalizationService


@pytest.fixture()
def ipfs_factory():
    """
    Изолированный ipfs_factory для интеграционных тестов.
    На каждый тест поднимается отдельное in-memory хранилище.
    """
    return IPFSFactoryStub(storage={})

@pytest.fixture()
def blockchain_service():
    """
    Stub BlockchainService с развёрнутым контрактом AmanitaInternational.
    """
    return BlockchainServiceStub()

@pytest.fixture()
def translation_cache_service(tmp_path):
    """
    Реальный TranslationCacheService с отдельной temp-директорией.
    Persist ipfs.json между вызовами в рамках одного теста.
    """
    cache_dir = tmp_path / "cache" / "translations"
    return TranslationCacheService(cache_dir=str(cache_dir))

@pytest.fixture()
def fallback_service():
    """
    Простой fallback-стаб: метод get_translation_with_fallback возвращает None (не используется в happy-path).
    """
    class _Fallback:
        def get_translation_with_fallback(self, *args, **kwargs):
            return None
    return _Fallback()

@pytest.fixture()
def multilingual_ipfs_service(ipfs_factory, translation_cache_service, fallback_service, blockchain_service):
    """
    Собранный MultilingualIPFSService с blockchain_service, ipfs_factory и реальным TranslationCacheService.
    """
    return MultilingualIPFSService(
        ipfs_factory=ipfs_factory,
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        blockchain_service=blockchain_service,
    )

@pytest.fixture()
def localization_service(multilingual_ipfs_service, translation_cache_service, fallback_service):
    """
    Готовый LocalizationService с DI-зависимостями для интеграционных тестов.
    """
    return LocalizationService(
        lang='en',
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        ipfs_service=multilingual_ipfs_service,
    )


