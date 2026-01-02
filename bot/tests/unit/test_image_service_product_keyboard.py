import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


def _collect_callback_data(reply_markup) -> set[str]:
    # aiogram InlineKeyboardMarkup: .inline_keyboard -> List[List[InlineKeyboardButton]]
    data = set()
    if not reply_markup:
        return data
    for row in getattr(reply_markup, "inline_keyboard", []) or []:
        for btn in row:
            cb = getattr(btn, "callback_data", None)
            if cb:
                data.add(cb)
    return data


@pytest.mark.unit
class TestImageServiceProductKeyboard:
    @pytest.mark.asyncio
    async def test_send_product_with_image_uses_product_id_if_present(self):
        from services.application.catalog.image_service import ImageService

        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        # cover_image_url="" => уйдём в _send_text_only (без сети)
        product = SimpleNamespace(id="p1", business_id="biz1", cover_image_url="")

        service = ImageService(storage_service=MagicMock())

        await service.send_product_with_image(callback, product, "TXT", loc)

        callback.message.answer.assert_awaited_once()
        _, kwargs = callback.message.answer.await_args
        reply_markup = kwargs.get("reply_markup")
        callbacks = _collect_callback_data(reply_markup)

        assert f"product:details:p1" in callbacks
        assert f"product:cart:p1" in callbacks

    @pytest.mark.asyncio
    async def test_send_product_with_image_falls_back_to_business_id_when_id_missing(self):
        from services.application.catalog.image_service import ImageService

        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        # id отсутствует -> ImageService берёт business_id
        product = SimpleNamespace(business_id="biz2", cover_image_url="")

        service = ImageService(storage_service=MagicMock())

        await service.send_product_with_image(callback, product, "TXT", loc)

        callback.message.answer.assert_awaited_once()
        _, kwargs = callback.message.answer.await_args
        reply_markup = kwargs.get("reply_markup")
        callbacks = _collect_callback_data(reply_markup)

        assert f"product:details:biz2" in callbacks
        assert f"product:cart:biz2" in callbacks

    @pytest.mark.asyncio
    async def test_send_product_with_image_cover_image_url_download_none_falls_back_to_text_with_keyboard(self):
        """
        GIVEN: cover_image_url задан, но download_image возвращает None
        WHEN: send_product_with_image() вызывается
        THEN: ImageService уходит в _send_text_only и отправляет текст через message.answer с keyboard,
              где callback_data корректные (product:details/product:cart)
        """
        from services.application.catalog.image_service import ImageService

        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        product = SimpleNamespace(id="p1", business_id="biz1", cover_image_url="SOME_ID")

        storage_service = MagicMock()
        storage_service.get_public_url.return_value = "https://example.invalid/image.jpg"

        service = ImageService(storage_service=storage_service)
        service.download_image = AsyncMock(return_value=None)  # форсим fallback без сети

        await service.send_product_with_image(callback, product, "TXT", loc)

        callback.message.answer.assert_awaited_once()
        _, kwargs = callback.message.answer.await_args

        # Проверяем, что keyboard реально передан
        reply_markup = kwargs.get("reply_markup")
        callbacks = _collect_callback_data(reply_markup)
        assert "product:details:p1" in callbacks
        assert "product:cart:p1" in callbacks


