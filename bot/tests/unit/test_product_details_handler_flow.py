import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.unit
class TestProductDetailsHandlerFlow:
    @pytest.mark.asyncio
    async def test_show_product_details_happy_path_calls_service_and_cleans_loading(self):
        """
        GIVEN: callback product:details:ID, ProductService возвращает product
        WHEN: show_product_details вызывается
        THEN:
          - product_id корректно извлечен
          - get_product_by_id вызван с loc.language
          - loading_message.delete вызван
          - send_product_details вызван
          - callback.answer вызван (finally)
        """
        from handlers.catalog import product_handlers

        callback = MagicMock()
        callback.data = "product:details:test_product"
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = MagicMock()

        loading_message = MagicMock()
        loading_message.delete = AsyncMock()
        callback.message.answer = AsyncMock(return_value=loading_message)

        loc = SimpleNamespace(language="en", t=lambda key, **kw: key)

        product = SimpleNamespace(id="test_product", business_id="biz", cover_image_url="", title="X")

        mock_product_service = MagicMock()
        mock_product_service.get_product_by_id = AsyncMock(return_value=product)
        mock_product_service.send_product_details = AsyncMock()

        # Патчим DI и локализацию handler-а
        product_handlers.get_product_service = MagicMock(return_value=mock_product_service)
        product_handlers.product_handler.get_localization = MagicMock(return_value=loc)

        await product_handlers.show_product_details(callback)

        mock_product_service.get_product_by_id.assert_awaited_once_with("test_product", "en")
        loading_message.delete.assert_awaited_once()
        mock_product_service.send_product_details.assert_awaited_once_with(callback, product, loc)

        # В happy-path callback.answer должен быть вызван ровно 1 раз (из finally)
        assert callback.answer.await_count == 1

    @pytest.mark.asyncio
    async def test_show_product_details_invalid_product_id_sends_error_and_answers_twice(self):
        """
        GIVEN: callback product:details:details (некорректный id по текущему коду)
        WHEN: show_product_details вызывается
        THEN: отправляется ошибка и callback.answer вызывается (внутри ветки + finally) => 2 раза
        """
        from handlers.catalog import product_handlers

        callback = MagicMock()
        callback.data = "product:details:details"
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        # Локализация будет запрошена только после валидации id; здесь она не нужна
        await product_handlers.show_product_details(callback)

        callback.message.answer.assert_awaited_once()
        assert callback.answer.await_count == 2

    @pytest.mark.asyncio
    async def test_show_product_details_not_found_deletes_loading_and_answers_twice(self):
        """
        GIVEN: ProductService.get_product_by_id возвращает None
        WHEN: show_product_details вызывается
        THEN:
          - loading_message.delete вызван
          - отправлено '❌ Продукт не найден'
          - callback.answer вызван 2 раза (ветка not-found + finally)
        """
        from handlers.catalog import product_handlers

        callback = MagicMock()
        callback.data = "product:details:test_product"
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = MagicMock()

        loading_message = MagicMock()
        loading_message.delete = AsyncMock()
        callback.message.answer = AsyncMock(return_value=loading_message)

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        mock_product_service = MagicMock()
        mock_product_service.get_product_by_id = AsyncMock(return_value=None)
        mock_product_service.send_product_details = AsyncMock()

        product_handlers.get_product_service = MagicMock(return_value=mock_product_service)
        product_handlers.product_handler.get_localization = MagicMock(return_value=loc)

        await product_handlers.show_product_details(callback)

        loading_message.delete.assert_awaited_once()

        # При not-found handler отправляет второе сообщение "❌ Продукт не найден"
        assert callback.message.answer.await_count == 2
        second_call = callback.message.answer.await_args_list[1]
        assert "Продукт не найден" in (second_call.args[0] if second_call.args else "")

        assert callback.answer.await_count == 2

    @pytest.mark.asyncio
    async def test_show_product_details_exception_still_answers(self):
        """
        GIVEN: get_product_by_id кидает исключение
        WHEN: show_product_details вызывается
        THEN: callback.answer всё равно вызывается (finally), и пользователю отправляется сообщение об ошибке (best-effort)
        """
        from handlers.catalog import product_handlers

        callback = MagicMock()
        callback.data = "product:details:test_product"
        callback.from_user.id = 123
        callback.answer = AsyncMock()
        callback.message = MagicMock()

        loading_message = MagicMock()
        loading_message.delete = AsyncMock()
        callback.message.answer = AsyncMock(return_value=loading_message)

        loc = SimpleNamespace(language="ru", t=lambda key, **kw: key)

        mock_product_service = MagicMock()
        mock_product_service.get_product_by_id = AsyncMock(side_effect=Exception("boom"))

        product_handlers.get_product_service = MagicMock(return_value=mock_product_service)
        product_handlers.product_handler.get_localization = MagicMock(return_value=loc)

        await product_handlers.show_product_details(callback)

        # В finally всегда должен быть answer
        assert callback.answer.await_count == 1


