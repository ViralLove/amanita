print("=== STARTING BOT INITIALIZATION ===")

import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
import logging
import sys
from bot.handlers.onboarding_fsm import router as onboarding_router
from bot.handlers.webapp_common import router as webapp_router
from bot.handlers.menu import router as menu_router
from bot.handlers.seller_product_creation_fsm import router as product_creation_router
from bot.handlers.seller_menu import router as seller_router
from bot.handlers.catalog import router as catalog_router

print("=== IMPORTS DONE ===")

# Настройка логирования - принудительный вывод в консоль
# Настраиваем корневой логгер для всех модулей
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Очищаем все обработчики, чтобы избежать дублирования
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Устанавливаем формат
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', 
                             datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)

# Добавляем обработчик к корневому логгеру
root_logger.addHandler(console_handler)

# Создаем логгер для текущего модуля
logger = logging.getLogger(__name__)

print("=== LOGGING INITIALIZED ===")

# Отладочная информация о пути
env_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"Поиск .env файла по пути: {env_path}")
print(f"Файл существует: {os.path.exists(env_path)}")

# Загрузка переменных окружения
load_dotenv(env_path)
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

print(f"API_TOKEN найден: {API_TOKEN is not None}")
if API_TOKEN:
    print(f"Длина токена: {len(API_TOKEN)}")

if not API_TOKEN:
    logger.error("Не найден TELEGRAM_BOT_TOKEN в .env файле")
    exit(1)

logger.info("=== Инициализация AMANITA Telegram Bot ===")
print("Логи работают! Если вы видите это сообщение, то увидите и логи ниже.")

async def main():
    print("=== ВХОД В ФУНКЦИЮ MAIN() ===")
    try:
        # Инициализация бота - простая инициализация, которая работает в тесте
        logger.info("Создание экземпляра бота...")
        bot = Bot(
            token=API_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        print("=== БОТ СОЗДАН ===")
        
        # Получение информации о боте
        print("=== ПОЛУЧЕНИЕ ИНФОРМАЦИИ О БОТЕ ===")
        bot_info = await bot.get_me()
        logger.info(f"Бот успешно создан: @{bot_info.username} (ID: {bot_info.id})")
        
        # Инициализация диспетчера
        logger.info("Инициализация диспетчера...")
        dp = Dispatcher()
        print("=== ДИСПЕТЧЕР СОЗДАН ===")
        
        # Регистрация хендлеров
        logger.info("Регистрация обработчиков...")
        dp.include_router(onboarding_router)
        dp.include_router(menu_router)
        dp.include_router(webapp_router)
        dp.include_router(product_creation_router)
        dp.include_router(seller_router)
        dp.include_router(catalog_router)
        logger.info("Все обработчики успешно зарегистрированы")
        print("=== ОБРАБОТЧИКИ ЗАРЕГИСТРИРОВАНЫ ===")
        
        # Запуск поллинга
        logger.info("Запуск поллинга...")
        print("=== ЗАПУСК ПОЛЛИНГА ===")
        logger.info("=== Бот запущен и готов к работе ===")
        
        # Запускаем поллинг с настройками, которые работают в тесте
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка в функции main(): {e}")
        import traceback
        logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
    finally:
        if 'bot' in locals():
            logger.info("=== Бот остановлен ===")
            await bot.session.close()

if __name__ == "__main__":
    print("=== STARTING MAIN ===")
    try:
        # Используем простой способ запуска, который работает в тесте
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        logger.error(f"Трассировка ошибки: {traceback.format_exc()}") 