def test_catalog_display_uses_localized_title(catalog_formatter, localization_service_primed, ipfs_factory):
    """
    4.3.1 → 2.1: Смоделировать вход каталога (product/component) и убедиться,
    что форматтер использует локализованные заголовки из LocalizationService.
    """
    localization_service, ids = localization_service_primed
    items = [
        {"type": "product", "id": ids["product_id"]},
        {"type": "component", "id": ids["component_id"]},
    ]
    ipfs = ipfs_factory.get_service()
    slides = catalog_formatter.build_carousel(items)

    assert isinstance(slides, list) and len(slides) == 2
    p_slide = next(s for s in slides if s["type"] == "product")
    c_slide = next(s for s in slides if s["type"] == "component")

    assert p_slide["title"] == "TG Product"
    assert p_slide["description"] == "Product for Telegram carousel"
    assert c_slide["title"] == "TG Component"
    assert c_slide["description"] == "Component for Telegram carousel"
    # 4.2: Нет плейсхолдеров
    assert "[title]" not in p_slide["title"]
    assert "[title]" not in c_slide["title"]
    # 4.3: Повторный рендер не обращается к IPFS
    start_downloads = ipfs.download_calls
    slides_2 = catalog_formatter.build_carousel(items)
    assert ipfs.download_calls == start_downloads


def test_catalog_builds_message_payload_without_sending(catalog_formatter, localization_service_primed, telegram_bot):
    """
    4.3.1 → 3.2: Отрендерить сообщения/карусель (без фактической отправки).
    Проверяем, что формируется корректный payload на основе локализованных данных.
    """
    localization_service, ids = localization_service_primed
    items = [
        {"type": "product", "id": ids["product_id"]},
        {"type": "component", "id": ids["component_id"]},
    ]
    slides = catalog_formatter.build_carousel(items)

    # Формируем message payload, не вызывая telegram_bot.send_*
    messages = []
    for s in slides:
        text = f"{s['title']}\n\n{s['description']}".strip()
        messages.append({"chat_id": 12345, "text": text})

    assert len(messages) == 2
    assert "TG Product" in messages[0]["text"]
    assert "Product for Telegram carousel" in messages[0]["text"]
    assert "TG Component" in messages[1]["text"]
    assert "Component for Telegram carousel" in messages[1]["text"]

    # Убеждаемся, что реальная отправка не выполнялась
    assert len(telegram_bot.sent_messages) == 0


def test_fallback_placeholder_in_message(catalog_formatter, localization_service, ipfs_factory, fallback_service, telegram_bot):
    """
    4.3.2: Проверяем плейсхолдеры при отсутствии переводов (CID отсутствуют, IPFS пуст, fallback ничего не даёт).
    """
    # Моки: IPFS пуст, gateway вернёт None (ничего не сетапим), fallback возвращает None
    ipfs = ipfs_factory.get_service()

    # Элементы каталога без подготовленных переводов
    items = [
        {"type": "product", "id": "missing-product"},
        {"type": "component", "id": "missing-component"},
    ]

    # Первый рендер
    start_downloads = ipfs.download_calls
    slides = catalog_formatter.build_carousel(items)
    assert len(slides) == 2
    p_slide = next(s for s in slides if s["type"] == "product")
    c_slide = next(s for s in slides if s["type"] == "component")

    # 4.1/4.2: ожидаем плейсхолдеры, т.к. переводов нет
    assert p_slide["title"] == "[title]"
    assert p_slide["description"] == "[description]"
    assert c_slide["title"] == "[title]"
    assert c_slide["description"] == "[description]"

    # Повторный рендер — результат стабилен, IPFS не дёргается
    slides2 = catalog_formatter.build_carousel(items)
    assert ipfs.download_calls == start_downloads

    # Сообщения не отправляем
    assert len(telegram_bot.sent_messages) == 0

