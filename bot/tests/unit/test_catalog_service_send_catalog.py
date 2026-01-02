import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.unit
class TestCatalogServiceSendCatalog:
    @pytest.mark.asyncio
    async def test_send_catalog_to_user_calls_formatter_and_image_service_for_each_product(self):
        """
        GIVEN: 2 продукта + formatter_service + image_service
        WHEN: send_catalog_to_user() вызывается
        THEN: formatter вызывается 1 раз на продукт, image_service вызывается 1 раз на продукт,
              а product_text = main_info+composition+pricing+details
        """
        from services.application.catalog.catalog_service import CatalogService

        # callback mock (aiogram-like)
        progress_message = MagicMock()
        progress_message.edit_text = AsyncMock()
        progress_message.delete = AsyncMock()

        callback = MagicMock()
        callback.from_user.id = 123
        callback.message = MagicMock()
        callback.message.answer = AsyncMock(return_value=progress_message)

        # loc minimal
        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        # products
        p1 = SimpleNamespace(id="p1", business_id="biz1", cover_image_url="", title="P1")
        p2 = SimpleNamespace(id="p2", business_id="biz2", cover_image_url="", title="P2")
        products = [p1, p2]

        # formatter mock must return all required sections
        formatter = MagicMock()
        formatter.format_product_for_telegram.side_effect = [
            {"main_info": "A", "composition": "B", "pricing": "C", "details": "D"},
            {"main_info": "E", "composition": "F", "pricing": "G", "details": "H"},
        ]
        # Важно: CatalogService вызывает formatter_service._truncate_text(...) если атрибут существует.
        # У MagicMock он существует по умолчанию → без этого тест получит MagicMock вместо строки.
        formatter._truncate_text = lambda s: s

        image_service = MagicMock()
        image_service.send_product_with_image = AsyncMock()

        service = CatalogService(image_service=image_service, formatter_service=formatter)

        await service.send_catalog_to_user(callback, products, loc)

        assert formatter.format_product_for_telegram.call_count == 2
        formatter.format_product_for_telegram.assert_any_call(p1, loc)
        formatter.format_product_for_telegram.assert_any_call(p2, loc)

        assert image_service.send_product_with_image.await_count == 2

        # Validate product_text per product
        calls = image_service.send_product_with_image.await_args_list
        assert calls[0].kwargs["callback"] == callback
        assert calls[0].kwargs["product"] == p1
        assert calls[0].kwargs["product_text"] == "ABCD"
        assert calls[0].kwargs["loc"] == loc

        assert calls[1].kwargs["product"] == p2
        assert calls[1].kwargs["product_text"] == "EFGH"

    @pytest.mark.asyncio
    async def test_send_catalog_to_user_empty_catalog_sends_empty_message(self):
        """
        GIVEN: пустой список products
        WHEN: send_catalog_to_user() вызывается
        THEN: отправляется catalog.empty и метод возвращает
        """
        from services.application.catalog.catalog_service import CatalogService

        callback = MagicMock()
        callback.from_user.id = 123
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        service = CatalogService(image_service=MagicMock(), formatter_service=MagicMock())

        await service.send_catalog_to_user(callback, [], loc)

        callback.message.answer.assert_awaited_once_with("catalog.empty")

    @pytest.mark.asyncio
    async def test_send_catalog_to_user_fallback_when_formatter_service_none(self):
        """
        GIVEN: formatter_service=None
        WHEN: send_catalog_to_user() отправляет продукт
        THEN: product_text формируется fallback-веткой (🍄 <b>{title}</b>)
        """
        from services.application.catalog.catalog_service import CatalogService

        progress_message = MagicMock()
        progress_message.edit_text = AsyncMock()
        progress_message.delete = AsyncMock()

        callback = MagicMock()
        callback.from_user.id = 123
        callback.message = MagicMock()
        callback.message.answer = AsyncMock(return_value=progress_message)

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        product = SimpleNamespace(id="p1", business_id="biz1", cover_image_url="", title="X")

        image_service = MagicMock()
        image_service.send_product_with_image = AsyncMock()

        service = CatalogService(image_service=image_service, formatter_service=None)

        await service.send_catalog_to_user(callback, [product], loc)

        image_service.send_product_with_image.assert_awaited_once()
        kwargs = image_service.send_product_with_image.await_args.kwargs
        assert kwargs["product"] == product
        assert kwargs["product_text"].startswith("🍄 <b>")
        assert "<b>X</b>" in kwargs["product_text"]

    @pytest.mark.asyncio
    async def test_send_catalog_to_user_formatter_exception_uses_fallback_text(self):
        """
        GIVEN: formatter_service есть, но format_product_for_telegram падает
        WHEN: send_catalog_to_user() отправляет продукт
        THEN: product_text формируется fallback-веткой "🏷️ ... ❌ Ошибка при форматировании"
              и всё равно передаётся в ImageService.send_product_with_image
        """
        from services.application.catalog.catalog_service import CatalogService

        progress_message = MagicMock()
        progress_message.edit_text = AsyncMock()
        progress_message.delete = AsyncMock()

        callback = MagicMock()
        callback.from_user.id = 123
        callback.message = MagicMock()
        callback.message.answer = AsyncMock(return_value=progress_message)

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        product = SimpleNamespace(id="p1", business_id="biz1", cover_image_url="", title="X")

        formatter = MagicMock()
        formatter.format_product_for_telegram.side_effect = Exception("boom")
        # Чтобы fallback-текст не превратился в MagicMock из-за _truncate_text:
        formatter._truncate_text = lambda s: s

        image_service = MagicMock()
        image_service.send_product_with_image = AsyncMock()

        service = CatalogService(image_service=image_service, formatter_service=formatter)

        await service.send_catalog_to_user(callback, [product], loc)

        image_service.send_product_with_image.assert_awaited_once()
        kwargs = image_service.send_product_with_image.await_args.kwargs
        assert kwargs["product"] == product
        assert "🏷️ <b>X</b>" in kwargs["product_text"]
        assert "❌ Ошибка при форматировании" in kwargs["product_text"]

    @pytest.mark.asyncio
    async def test_send_catalog_to_user_applies_truncate_text_before_sending(self):
        """
        GIVEN: formatter_service возвращает секции и имеет _truncate_text
        WHEN: send_catalog_to_user() отправляет продукт
        THEN: _truncate_text применяется к полной склейке секций, и в ImageService уходит результат truncation
        """
        from services.application.catalog.catalog_service import CatalogService

        progress_message = MagicMock()
        progress_message.edit_text = AsyncMock()
        progress_message.delete = AsyncMock()

        callback = MagicMock()
        callback.from_user.id = 123
        callback.message = MagicMock()
        callback.message.answer = AsyncMock(return_value=progress_message)

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        product = SimpleNamespace(id="p1", business_id="biz1", cover_image_url="", title="X")

        formatter = MagicMock()
        formatter.format_product_for_telegram.return_value = {
            "main_info": "AAAA",
            "composition": "BBBB",
            "pricing": "CCCC",
            "details": "DDDD",
        }
        formatter._truncate_text = MagicMock(return_value="TRUNCATED")

        image_service = MagicMock()
        image_service.send_product_with_image = AsyncMock()

        service = CatalogService(image_service=image_service, formatter_service=formatter)

        await service.send_catalog_to_user(callback, [product], loc)

        formatter._truncate_text.assert_called_once_with("AAAABBBBCCCCDDDD")

        image_service.send_product_with_image.assert_awaited_once()
        kwargs = image_service.send_product_with_image.await_args.kwargs
        assert kwargs["product_text"] == "TRUNCATED"


