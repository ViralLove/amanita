import pytest


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
class TestComponentHandlersKeyboardContracts:
    def test_section_navigation_keyboard_always_has_close_description(self):
        from handlers.catalog.component_handlers import _create_section_navigation_keyboard

        kb = _create_section_navigation_keyboard(
            component_id="c1",
            current_section="generic",
            language="ru",
            has_generic=True,
            has_effects=False,
            has_shamanic=False,
            has_warnings=False,
        )

        callbacks = _collect_callback_data(kb)
        assert "close_description" in callbacks

    def test_section_navigation_keyboard_has_prev_next_when_neighbors_exist(self):
        """
        GIVEN: sections generic/effects/shamanic exist, current=effects
        THEN: есть prev generic и next shamanic + close_description
        """
        from handlers.catalog.component_handlers import _create_section_navigation_keyboard

        kb = _create_section_navigation_keyboard(
            component_id="amanita_muscaria",
            current_section="effects",
            language="ru",
            has_generic=True,
            has_effects=True,
            has_shamanic=True,
            has_warnings=False,
        )

        callbacks = _collect_callback_data(kb)
        assert "close_description" in callbacks
        assert "component_desc:amanita_muscaria:generic:ru" in callbacks
        assert "component_desc:amanita_muscaria:shamanic:ru" in callbacks


