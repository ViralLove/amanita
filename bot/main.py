print("=== STARTING AMANITA BOT + API INITIALIZATION ===")

import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
import logging
import sys
import uvicorn
from handlers.onboarding_fsm import router as onboarding_router
from handlers.webapp_common import router as webapp_router
from handlers.menu import router as menu_router
from handlers.seller_product_creation_fsm import router as product_creation_router
from handlers.seller_menu import router as seller_router
from handlers.catalog import router as catalog_router
from services.product.registry_singleton import product_registry_service
from services.service_factory import ServiceFactory
from api.main import create_api_app
from api.config import APIConfig
import sentry_sdk
from utils.sentry_init import init_sentry
from utils.logging_setup import setup_logging

init_sentry()
logger = setup_logging(
    log_level=APIConfig.LOG_LEVEL,
    log_file=APIConfig.LOG_FILE,
    max_size=APIConfig.LOG_MAX_SIZE,
    backup_count=APIConfig.LOG_BACKUP_COUNT
)

print("=== IMPORTS DONE ===")

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

logger.info("=== Инициализация AMANITA Telegram Bot + API Server ===")
print("Логи работают! Если вы видите это сообщение, то увидите и логи ниже.")

async def main():
    print("=== ВХОД В ФУНКЦИЮ MAIN() ===")
    try:
        # Инициализация ServiceFactory (общий для бота и API)
        logger.info("Инициализация ServiceFactory...")
        service_factory = ServiceFactory()
        logger.info("ServiceFactory успешно инициализирован")
        
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
        dp.include_router(catalog_router)
        dp.include_router(menu_router)
        dp.include_router(webapp_router)
        # dp.include_router(seller_router)
        # dp.include_router(product_creation_router)
        logger.info("Все обработчики успешно зарегистрированы")
        print("=== ОБРАБОТЧИКИ ЗАРЕГИСТРИРОВАНЫ ===")

        # === Фоновая загрузка каталога ===
        logger.info("Запуск фоновой загрузки каталога продуктов...")
        async def preload_catalog():
            await product_registry_service.get_all_products()
            logger.info("Фоновая загрузка каталога завершена!")
        asyncio.create_task(preload_catalog())
        logger.info("Фоновая задача по загрузке каталога запущена")
        # === Конец фоновой загрузки ===

        # Создание FastAPI приложения с ServiceFactory
        logger.info("Создание FastAPI приложения...")
        
        # Настройка логирования для API из конфигурации
        api_app = create_api_app(
            service_factory=service_factory,
            log_level=APIConfig.LOG_LEVEL,
            log_file=APIConfig.LOG_FILE
        )
        logger.info(f"FastAPI приложение создано с логированием: {APIConfig.LOG_LEVEL} -> {APIConfig.LOG_FILE}")
        
        # Настройка uvicorn сервера для API
        logger.info("Настройка uvicorn сервера...")
        
        # Получаем порт из переменной окружения Railway
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"Используется порт: {port}")
        
        config = uvicorn.Config(
            api_app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=False  # Отключаем access log, так как у нас есть свое логирование
        )
        server = uvicorn.Server(config)
        logger.info("Uvicorn сервер настроен")
        
        # Запуск бота и API сервера параллельно
        logger.info("Запуск бота и API сервера параллельно...")
        print("=== ЗАПУСК БОТА И API СЕРВЕРА ===")
        logger.info("=== AMANITA Bot + API Server запущены и готовы к работе ===")
        
        # Параллельный запуск через asyncio.gather
        await asyncio.gather(
            dp.start_polling(bot),
            server.serve()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в функции main(): {e}")
        import traceback
        logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
    finally:
        if 'bot' in locals():
            logger.info("=== Бот остановлен ===")
            await bot.session.close()
        logger.info("=== AMANITA Bot + API Server остановлены ===")

if __name__ == "__main__":
    print("=== STARTING AMANITA BOT + API MAIN ===")
    try:
        # Запуск бота и API сервера
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("AMANITA Bot + API Server остановлены пользователем (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        logger.error(f"Трассировка ошибки: {traceback.format_exc()}") 