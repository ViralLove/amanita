"""
Утилиты для форматирования текста в Telegram.
"""

def truncate_text_for_telegram(text: str, max_length: int = 4000) -> str:
    """
    Обрезает текст для Telegram, чтобы избежать ошибки "message too long".
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина (по умолчанию 4000 для безопасности)
        
    Returns:
        str: Обрезанный текст с индикатором
    """
    if len(text) <= max_length:
        return text
    
    # Обрезаем текст и добавляем индикатор
    truncated = text[:max_length-100]  # Оставляем место для индикатора
    
    # Ищем последний полный абзац
    last_newline = truncated.rfind('\n\n')
    if last_newline > max_length * 0.8:  # Если последний абзац не слишком далеко от конца
        truncated = truncated[:last_newline]
    
    truncated += f"\n\n... <i>Текст обрезан для Telegram. Полное описание доступно в детальном просмотре.</i>"
    
    return truncated
