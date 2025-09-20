#!/usr/bin/env python3
"""
Локальный сервер для разработки Amanita Wallet с поддержкой .env файлов
"""

import http.server
import socketserver
import os
import json
from urllib.parse import urlparse, parse_qs

class AmanitaHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Добавляем CORS заголовки для локальной разработки
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Если запрашивается config.js, генерируем его динамически
        if self.path == '/config.js':
            self.send_response(200)
            self.send_header('Content-type', 'application/javascript')
            self.end_headers()
            
            # Читаем переменные окружения
            config = {
                'DEBUG_MODE': os.getenv('DEBUG_MODE', 'true'),
                'NODE_ENV': os.getenv('NODE_ENV', 'development'),
                'PORT': os.getenv('PORT', '8080'),
                'CORS_ORIGIN': os.getenv('CORS_ORIGIN', 'http://localhost:8080'),
                'LOG_LEVEL': os.getenv('LOG_LEVEL', 'debug')
            }
            
            js_config = f'window.RAILWAY_ENV = {json.dumps(config)};'
            self.wfile.write(js_config.encode('utf-8'))
            return
        
        # Для всех остальных запросов используем стандартную обработку
        super().do_GET()

def load_env_file():
    """Загружает переменные из .env файла"""
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"📁 Загружаем переменные из {env_file}")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
                    print(f"  {key.strip()}={value.strip()}")
    else:
        print(f"⚠️  Файл {env_file} не найден, используем значения по умолчанию")

def main():
    # Загружаем переменные окружения
    load_env_file()
    
    PORT = int(os.getenv('PORT', '8080'))
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'true')
    NODE_ENV = os.getenv('NODE_ENV', 'development')
    
    print("🚀 Запуск локального сервера Amanita Wallet")
    print(f"📊 Порт: {PORT}")
    print(f"🔧 Debug режим: {DEBUG_MODE}")
    print(f"🌍 Окружение: {NODE_ENV}")
    print(f"🌐 URL: http://localhost:{PORT}")
    print("=" * 50)
    
    with socketserver.TCPServer(("", PORT), AmanitaHTTPRequestHandler) as httpd:
        print(f"✅ Сервер запущен на http://localhost:{PORT}")
        print("💡 Для остановки нажмите Ctrl+C")
        print("=" * 50)
        httpd.serve_forever()

if __name__ == "__main__":
    main()
