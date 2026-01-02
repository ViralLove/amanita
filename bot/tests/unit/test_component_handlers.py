import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock


@pytest.mark.unit
class TestComponentHandlers:
    @pytest.fixture
    def callback(self):
        """
        Базовый callback-mock для handler тестов.
        Тесты должны установить callback.data под свой сценарий.
        """
        cb = MagicMock()
        cb.data = ""
        cb.answer = AsyncMock()
        cb.message = MagicMock()
        cb.message.answer = AsyncMock()
        return cb

    @pytest.fixture
    def loc(self):
        """Минимальный loc с t(key)->key, без реальной локализации."""
        return SimpleNamespace(t=lambda key, **kw: key)

    @pytest.mark.asyncio
    async def test_component_desc_invalid_format_answers_error_format(self, callback, loc):
        """
        GIVEN: callback.data в неверном формате (len(parts)!=4)
        WHEN: show_component_description_section вызывается
        THEN: callback.answer вызывается с loc.t(...error_format), message.answer не вызывается
        """
        from handlers.catalog import component_handlers

        callback.data = "component_desc:too:short"

        await component_handlers.show_component_description_section(callback, loc)

        callback.answer.assert_awaited_once_with("catalog.product.component_description.error_format")
        callback.message.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_component_desc_awaits_get_component_description_success_sends_message_html(self, mocker, callback, loc):
        """
        GIVEN: валидный callback + ComponentDescription с непустой секцией
        WHEN: show_component_description_section вызывается
        THEN:
          - get_component_description awaited
          - callback.message.answer вызван с parse_mode="HTML" и reply_markup
          - callback.answer вызван
        """
        from handlers.catalog import component_handlers

        callback.data = "component_desc:amanita_muscaria:generic:ru"

        desc = SimpleNamespace(
            generic_description="GENERIC TEXT",
            effects="",
            shamanic="",
            warnings="",
        )

        mock_component_service = MagicMock()
        mock_component_service.get_component_description = AsyncMock(return_value=desc)
        mock_component_service.get_component_full = Mock(
            return_value=SimpleNamespace(scientific_title="Amanita muscaria")
        )

        mocker.patch(
            "handlers.catalog.component_handlers.get_component_service",
            return_value=mock_component_service,
        )

        await component_handlers.show_component_description_section(callback, loc)

        mock_component_service.get_component_description.assert_awaited_once_with("amanita_muscaria", "ru")
        callback.message.answer.assert_awaited_once()
        _, kwargs = callback.message.answer.await_args
        assert kwargs["parse_mode"] == "HTML"
        assert kwargs["reply_markup"] is not None
        assert "GENERIC TEXT" in callback.message.answer.await_args.args[0]

        # Success path вызывает callback.answer() в конце
        assert callback.answer.await_count == 1

    @pytest.mark.asyncio
    async def test_component_desc_description_unavailable_answers_unavailable(self, mocker, callback, loc):
        """
        GIVEN: get_component_description возвращает None
        WHEN: show_component_description_section вызывается
        THEN: callback.answer(unavailable), message.answer не вызывается
        """
        from handlers.catalog import component_handlers

        callback.data = "component_desc:amanita_muscaria:generic:ru"

        mock_component_service = MagicMock()
        mock_component_service.get_component_description = AsyncMock(return_value=None)
        mock_component_service.get_component_full = Mock(return_value=None)
        mocker.patch(
            "handlers.catalog.component_handlers.get_component_service",
            return_value=mock_component_service,
        )

        await component_handlers.show_component_description_section(callback, loc)

        callback.answer.assert_awaited_once_with("catalog.product.component_description.unavailable")
        callback.message.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_component_desc_section_empty_answers_section_empty(self, mocker, callback, loc):
        """
        GIVEN: description есть, но нужная секция пустая
        WHEN: show_component_description_section вызывается
        THEN: callback.answer(section_empty), message.answer не вызывается
        """
        from handlers.catalog import component_handlers

        callback.data = "component_desc:amanita_muscaria:effects:ru"

        desc = SimpleNamespace(
            generic_description="",
            effects="",
            shamanic="",
            warnings="",
        )

        mock_component_service = MagicMock()
        mock_component_service.get_component_description = AsyncMock(return_value=desc)
        mock_component_service.get_component_full = Mock(return_value=None)
        mocker.patch(
            "handlers.catalog.component_handlers.get_component_service",
            return_value=mock_component_service,
        )

        await component_handlers.show_component_description_section(callback, loc)

        callback.answer.assert_awaited_once_with("catalog.product.component_description.section_empty")
        callback.message.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_component_desc_exception_path_answers_error_loading(self, mocker, callback, loc):
        """
        GIVEN: внутри handler возникает исключение (например, get_component_service() кидает)
        WHEN: show_component_description_section вызывается
        THEN: best-effort — callback.answer(error_loading)
        """
        from handlers.catalog import component_handlers

        callback.data = "component_desc:amanita_muscaria:generic:ru"

        mocker.patch(
            "handlers.catalog.component_handlers.get_component_service",
            side_effect=Exception("boom"),
        )

        await component_handlers.show_component_description_section(callback, loc)

        callback.answer.assert_awaited_once_with("catalog.product.component_description.error_loading")
        callback.message.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_component_menu_invalid_format_answers_error_format(self, callback, loc):
        """
        GIVEN: неверный формат component_menu (len(parts)!=3)
        THEN: callback.answer(error_format), message.answer не вызывается
        """
        from handlers.catalog import component_handlers

        callback.data = "component_menu:too:many:parts"

        await component_handlers.show_component_description_menu(callback, loc)

        callback.answer.assert_awaited_once_with("catalog.product.component_description.error_format")
        callback.message.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_component_menu_component_not_found_answers_component_not_found(self, mocker, callback, loc):
        """
        GIVEN: get_component_full возвращает None
        THEN: callback.answer(component_not_found), message.answer не вызывается
        """
        from handlers.catalog import component_handlers

        callback.data = "component_menu:amanita_muscaria:ru"

        mock_component_service = MagicMock()
        mock_component_service.get_component_full = Mock(return_value=None)
        mocker.patch(
            "handlers.catalog.component_handlers.get_component_service",
            return_value=mock_component_service,
        )

        await component_handlers.show_component_description_menu(callback, loc)

        callback.answer.assert_awaited_once_with("catalog.product.component_description.component_not_found")
        callback.message.answer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_component_menu_uses_formatter_service_to_build_keyboard(self, mocker, callback, loc):
        """
        GIVEN: компонент найден + formatter factory
        WHEN: show_component_description_menu вызывается
        THEN: get_product_formatter_service() вызван и _create_component_description_keyboard вызван с (component_id, language, "")
        """
        from handlers.catalog import component_handlers

        callback.data = "component_menu:amanita_muscaria:ru"

        mock_component_service = MagicMock()
        mock_component_service.get_component_full = Mock(
            return_value=SimpleNamespace(scientific_title="Amanita muscaria")
        )
        mocker.patch(
            "handlers.catalog.component_handlers.get_component_service",
            return_value=mock_component_service,
        )

        keyboard_sentinel = object()
        mock_formatter = MagicMock()
        mock_formatter._create_component_description_keyboard = Mock(return_value=keyboard_sentinel)

        get_formatter_spy = mocker.patch(
            "handlers.dependencies.get_product_formatter_service",
            return_value=mock_formatter,
        )

        await component_handlers.show_component_description_menu(callback, loc)

        get_formatter_spy.assert_called_once()
        mock_formatter._create_component_description_keyboard.assert_called_once_with(
            "amanita_muscaria",
            "ru",
            "",
        )

        callback.message.answer.assert_awaited_once()
        _, kwargs = callback.message.answer.await_args
        assert kwargs["parse_mode"] == "HTML"
        assert kwargs["reply_markup"] is keyboard_sentinel
        assert callback.answer.await_count == 1

    @pytest.mark.asyncio
    async def test_component_menu_exception_path_answers_error_menu(self, mocker, callback, loc):
        """
        GIVEN: внутри handler component_menu возникает исключение (например, formatter factory кидает)
        WHEN: show_component_description_menu вызывается
        THEN: best-effort — callback.answer(error_menu)
        """
        from handlers.catalog import component_handlers

        callback.data = "component_menu:amanita_muscaria:ru"

        mock_component_service = MagicMock()
        mock_component_service.get_component_full = Mock(
            return_value=SimpleNamespace(scientific_title="Amanita muscaria")
        )
        mocker.patch(
            "handlers.catalog.component_handlers.get_component_service",
            return_value=mock_component_service,
        )

        mocker.patch(
            "handlers.dependencies.get_product_formatter_service",
            side_effect=Exception("boom"),
        )

        await component_handlers.show_component_description_menu(callback, loc)

        callback.answer.assert_awaited_once_with("catalog.product.component_description.error_menu")
        callback.message.answer.assert_not_awaited()


