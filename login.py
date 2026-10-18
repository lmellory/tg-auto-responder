#!/usr/bin/env python3
"""
Скрипт для генерации SESSION_STRING.
Нужен для бесплатного деплоя на облачные хостинги (Koyeb, Hugging Face, Render),
чтобы бот работал 24/7 без ввода смс в облаке.
"""

import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

if not api_id or not api_hash:
    print("👉 Получите API_ID и API_HASH на сайте https://my.telegram.org (раздел API development tools)")
    api_id = input("Введите ваш API_ID: ").strip()
    api_hash = input("Введите ваш API_HASH: ").strip()

with TelegramClient(StringSession(), int(api_id), api_hash) as client:
    session_str = client.session.save()
    me = client.get_me()
    print("\n" + "=" * 60)
    print(f"🎉 Успешно авторизован как: {me.first_name} (@{me.username})")
    print("=" * 60)
    print("\nВаша строка сессии (SESSION_STRING):")
    print("-" * 60)
    print(session_str)
    print("-" * 60)
    print("\n💡 Скопируйте эту строку в файл .env или в Environment Variables на бесплатном хостинге:")
    print(f"SESSION_STRING={session_str}\n")
