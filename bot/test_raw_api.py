# Минимальный скрипт для тестирования API Telegram напрямую через aiohttp
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

async def test_telegram_api():
    print("=== Прямой тест API Telegram через aiohttp ===")
    
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
    
    # Прямой запрос к API через aiohttp
    try:
        api_url = f"https://api.telegram.org/bot{token}/getMe"
        print(f"Отправка запроса к: {api_url[:40]}...")
        
        # Создание SSL контекста с отключенной проверкой для тестирования
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, ssl=ssl_context) as response:
                print(f"Код ответа: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Данные ответа: {data}")
                    if data.get("ok"):
                        print("API Telegram доступен и токен валиден!")
                    else:
                        print(f"Ошибка API: {data.get('description')}")
                else:
                    print(f"Ошибка HTTP: {response.status}")
                    text = await response.text()
                    print(f"Текст ответа: {text}")
        
        # Проверяем также через curl (выполнение внешней команды)
        print("\nПроверка через curl:")
        import subprocess
        try:
            result = subprocess.run(
                ["curl", "-s", api_url], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            print(f"Код возврата curl: {result.returncode}")
            print(f"Вывод curl: {result.stdout[:200]}")
            if result.stderr:
                print(f"Ошибка curl: {result.stderr}")
        except Exception as e:
            print(f"Ошибка при выполнении curl: {e}")
        
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_telegram_api()) 