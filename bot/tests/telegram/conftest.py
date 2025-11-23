import pytest
from typing import Dict, Any

from tests.integration.ipfs_stub import IPFSFactoryStub
from tests.integration.blockchain_stub import BlockchainServiceStub
from services.common.translation_cache_service import TranslationCacheService
from services.common.multilingual_ipfs_service import MultilingualIPFSService
from services.common.localization_service import LocalizationService

class DummyTelegramBot:
    """
    Простой заглушечный Telegram-бот, который накапливает отправленные сообщения/медиа.
    """
    def __init__(self):
        self.sent_messages = []
        self.sent_media_groups = []

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent_messages.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return True

    def send_media_group(self, chat_id, media, reply_markup=None):
        self.sent_media_groups.append({"chat_id": chat_id, "media": media, "reply_markup": reply_markup})
        return True


class CatalogFormatterStub:
    """
    Упрощённый форматтер каталога:
    - Собирает карточки на основе списка items и localization_service
    - Возвращает структуру для отправки (без реального Telegram API)
    """
    def __init__(self, localization_service):
        self.localization_service = localization_service

    def build_carousel(self, items):
        """
        items: список словарей вида {"type": "product"|"component", "id": "<business_id|component_id>"}
        """
        slides = []
        for item in items:
            if item["type"] == "product":
                title = self.localization_service.t(f"product.{item['id']}.title")  # str
                desc = self.localization_service.t(f"product.{item['id']}.description", default="")
            else:
                title = self.localization_service.t(f"component.{item['id']}.title")
                desc = self.localization_service.t(f"component.{item['id']}.description", default="")
            slides.append({"title": title, "description": desc, "id": item["id"], "type": item["type"]})
        return slides


@pytest.fixture()
def telegram_bot():
    """
    Заглушка Telegram-бота для unit/integration тестов Telegram-слоя.
    """
    return DummyTelegramBot()


@pytest.fixture()
def catalog_formatter(localization_service):
    """
    Заглушка форматтера каталога, использующего LocalizationService.
    """
    return CatalogFormatterStub(localization_service)

@pytest.fixture()
def ipfs_factory():
    return IPFSFactoryStub(storage={})

@pytest.fixture()
def blockchain_service():
    return BlockchainServiceStub()

@pytest.fixture()
def translation_cache_service(tmp_path):
    cache_dir = tmp_path / "cache" / "translations"
    return TranslationCacheService(cache_dir=str(cache_dir))

@pytest.fixture()
def fallback_service():
    class _Fallback:
        def get_translation_with_fallback(self, *args, **kwargs):
            return None
    return _Fallback()

@pytest.fixture()
def multilingual_ipfs_service(ipfs_factory, translation_cache_service, fallback_service, blockchain_service):
    return MultilingualIPFSService(
        ipfs_factory=ipfs_factory,
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        blockchain_service=blockchain_service,
    )

@pytest.fixture()
def localization_service(ipfs_factory, translation_cache_service, fallback_service, blockchain_service):
    """
    LocalizationService с DI-зависимостями (совместим с форматтером).
    """
    ml = MultilingualIPFSService(
        ipfs_factory=ipfs_factory,
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        blockchain_service=blockchain_service,
    )
    return LocalizationService(
        lang='en',
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        ipfs_service=ml,
    )

@pytest.fixture()
def localization_service_primed(localization_service, ipfs_factory, blockchain_service):
    """
    Предзаполняет IPFS-json и CID’ы в контракте для продукта/компонента,
    чтобы форматтер каталога получил локализованные заголовки.
    """
    ipfs = ipfs_factory.get_service()
    # Product payload (плоская форма, ожидаемая ProductLocalizationService)
    p_id = "prod-tg-001"
    p_payload = {"title": "TG Product", "description": "Product for Telegram carousel"}
    p_cid = ipfs.upload_json(p_payload)
    # Component payload
    c_id = "comp-tg-001"
    c_payload = {"title": "TG Component", "description": "Component for Telegram carousel"}
    c_cid = ipfs.upload_json(c_payload)
    # Записываем CID’ы в контракт
    contract = blockchain_service.get_contract("AmanitaInternational")
    contract.functions.setSimpleFieldCID("product", p_id, "*", "en", p_cid).transact()
    contract.functions.setSimpleFieldCID("component", c_id, "*", "en", c_cid).transact()
    return localization_service, {"product_id": p_id, "component_id": c_id}


