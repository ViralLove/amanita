import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.unit
class TestProductServiceDetails:
    @pytest.mark.asyncio
    async def test_get_product_by_id_matches_by_id_and_passes_language(self):
        from services.application.catalog.product_service import ProductService
        from services.product import registry_singleton

        p1 = SimpleNamespace(id="p1", business_id="biz1", title="P1")
        p2 = SimpleNamespace(id="p2", business_id="biz2", title="P2")

        registry_singleton.product_registry_service.get_all_products = AsyncMock(return_value=[p1, p2])

        service = ProductService(image_service=MagicMock(), formatter_service=MagicMock())
        found = await service.get_product_by_id("p2", language="en")

        assert found == p2
        registry_singleton.product_registry_service.get_all_products.assert_awaited_once_with("en")

    @pytest.mark.asyncio
    async def test_get_product_by_id_matches_by_business_id(self):
        from services.application.catalog.product_service import ProductService
        from services.product import registry_singleton

        p1 = SimpleNamespace(id="p1", business_id="biz1", title="P1")
        p2 = SimpleNamespace(id="p2", business_id="biz2", title="P2")

        registry_singleton.product_registry_service.get_all_products = AsyncMock(return_value=[p1, p2])

        service = ProductService(image_service=MagicMock(), formatter_service=MagicMock())
        found = await service.get_product_by_id("biz1", language="ru")

        assert found == p1
        registry_singleton.product_registry_service.get_all_products.assert_awaited_once_with("ru")

    @pytest.mark.asyncio
    async def test_send_product_details_calls_formatter_and_image_service(self):
        from services.application.catalog.product_service import ProductService

        callback = MagicMock()
        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)
        product = SimpleNamespace(id="p1", business_id="biz1", title="Product")

        formatter = MagicMock()
        formatter.format_product_main_info_for_telegram.return_value = "MAIN"
        formatter.format_product_description_for_telegram.return_value = "DESC"

        image_service = MagicMock()
        image_service.send_product_details_with_image = AsyncMock()

        service = ProductService(image_service=image_service, formatter_service=formatter)
        await service.send_product_details(callback, product, loc)

        formatter.format_product_main_info_for_telegram.assert_called_once_with(product, loc)
        formatter.format_product_description_for_telegram.assert_called_once_with(product, loc)

        image_service.send_product_details_with_image.assert_awaited_once()
        kwargs = image_service.send_product_details_with_image.await_args.kwargs
        assert kwargs["callback"] == callback
        assert kwargs["product"] == product
        assert kwargs["main_info_text"] == "MAIN"
        assert kwargs["description_text"] == "DESC"
        assert kwargs["loc"] == loc

    @pytest.mark.asyncio
    async def test_send_product_details_formatter_exception_uses_fallback_but_still_calls_image_service(self):
        from services.application.catalog.product_service import ProductService

        callback = MagicMock()
        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)
        product = SimpleNamespace(id="p1", business_id="biz1", title="Product")

        formatter = MagicMock()
        formatter.format_product_main_info_for_telegram.side_effect = Exception("boom")

        image_service = MagicMock()
        image_service.send_product_details_with_image = AsyncMock()

        service = ProductService(image_service=image_service, formatter_service=formatter)
        await service.send_product_details(callback, product, loc)

        image_service.send_product_details_with_image.assert_awaited_once()
        kwargs = image_service.send_product_details_with_image.await_args.kwargs
        assert "❌ Ошибка при загрузке основной информации" in kwargs["main_info_text"]
        assert "❌ Ошибка при загрузке детальной информации" in kwargs["description_text"]


