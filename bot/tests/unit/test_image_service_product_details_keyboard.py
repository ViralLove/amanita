import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


def _collect_callback_data(reply_markup) -> set[str]:
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
class TestImageServiceProductDetailsKeyboard:
    @pytest.mark.asyncio
    async def test_send_product_details_with_image_no_cover_sends_two_texts_with_scroll_keyboard(self):
        """
        GIVEN: cover_image_url пустой
        WHEN: send_product_details_with_image()
        THEN: отправляет 2 сообщения (main + description) и в клавиатуре есть scroll:catalog и product:cart:{id}
        """
        from services.application.catalog.image_service import ImageService

        callback = MagicMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)
        product = SimpleNamespace(id="p1", business_id="biz1", cover_image_url="")

        service = ImageService(storage_service=MagicMock())

        await service.send_product_details_with_image(
            callback=callback,
            product=product,
            main_info_text="MAIN",
            description_text="DESC",
            loc=loc,
        )

        assert callback.message.answer.await_count == 2

        # Проверяем клавиатуру в каждом сообщении
        for call in callback.message.answer.await_args_list:
            _, kwargs = call
            reply_markup = kwargs.get("reply_markup")
            callbacks = _collect_callback_data(reply_markup)
            assert "scroll:catalog" in callbacks
            assert "product:cart:p1" in callbacks


