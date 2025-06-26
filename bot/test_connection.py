# Минимальный скрипт для тестирования соединения с API Telegram
import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot
import sys

async def test_connection():
    print("=== Тест соединения с API Telegram ===")
    
    # Загрузка переменных окружения
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"Поиск .env файла по пути: {env_path}")
    print(f"Файл существует: {os.path.exists(env_path)}")
    load_dotenv(env_path)
    
    # Получение токена
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    print(f"Токен найден: {token is not None}")
    if token:
        print(f"Первые 5 символов токена: {token[:5]}")
    
    if not token:
        print("Ошибка: Токен не найден")
        return
    
    # Проверка токена по формату
    if not token.count(':') == 1 or not token.split(':')[0].isdigit():
        print(f"ПРЕДУПРЕЖДЕНИЕ: Формат токена может быть неверным. Обычно токен имеет формат '123456789:ABC...'")
    
    # Проверка proxy из переменных окружения
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    print(f"HTTP_PROXY: {http_proxy}")
    print(f"HTTPS_PROXY: {https_proxy}")
    
    try:
        print(f"Создание экземпляра бота...")
        
        # Настройка сессии для бота - правильно для aiogram 3.20.0
        import ssl
        
        # В aiogram 3.20.0 нельзя настроить connector напрямую
        # Создаем бота напрямую без дополнительных настроек
        print("Попытка подключения без дополнительных настроек...")
        bot = Bot(token=token)
        
        print("Получение информации о боте...")
        try:
            bot_info = await bot.get_me()
            print(f"Успех! Информация о боте: @{bot_info.username} (ID: {bot_info.id})")
        except Exception as e:
            print(f"Ошибка при получении информации: {str(e)}")
            print("Проверьте сетевое подключение и токен бота.")
            raise
        
        print("Получение обновлений...")
        updates = await bot.get_updates(limit=1, timeout=1)
        print(f"Успех! Получено обновлений: {len(updates)}")
        
        print("Тест успешно завершен!")
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
    finally:
        if 'bot' in locals():
            try:
                print("Закрытие сессии бота...")
                await bot.session.close()
                print("Сессия бота закрыта")
            except Exception as e:
                print(f"Ошибка при закрытии сессии: {str(e)}")

if __name__ == "__main__":
    print(f"Python версия: {sys.version}")
    try:
        asyncio.run(test_connection())
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}") 