#!/usr/bin/env python3
"""
Генератор API ключей для AMANITA API
"""
import secrets

def generate_api_key():
    return "ak_" + secrets.token_hex(8)  # 16 hex-символов

def generate_api_secret():
    return "sk_" + secrets.token_hex(32)  # 64 hex-символа

if __name__ == "__main__":
    api_key = generate_api_key()
    api_secret = generate_api_secret()
    print("\nСкопируйте эти строки в ваш .env файл:\n")
    print(f"AMANITA_API_KEY={api_key}")
    print(f"AMANITA_API_SECRET={api_secret}") 