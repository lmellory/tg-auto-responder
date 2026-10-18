#!/usr/bin/env python3
"""
Скрипт для надёжной генерации SESSION_STRING.
Сохраняет проверенную строку сессии в файл session_string.txt
после полного завершения авторизации и миграции на ваш дата-центр Telegram.
"""

import os
from pathlib import Path
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

api_id = int(api_id)

print("\nПодключаюсь к Telegram...")
client = TelegramClient(StringSession(), api_id, api_hash)
client.start()

# Запрашиваем информацию об аккаунте (это гарантирует завершение миграции на ваш рабочий DC)
me = client.get_me()

# Сохраняем сессию ТОЛЬКО ПОСЛЕ успешного get_me()
session_str = client.session.save()

# Проверяем строку сессии тестовым подключением
print("Проверяю валидность сессии...")
verifier = TelegramClient(StringSession(session_str), api_id, api_hash)
verifier.connect()
if not verifier.is_user_authorized():
    print("⚠️ Повторная синхронизация ключа...")
    verifier.start()
    session_str = verifier.session.save()
verifier.disconnect()

client.disconnect()

# Записываем в отдельный файл session_string.txt без переносов строк
output_file = Path("session_string.txt")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(session_str.strip())

print("\n" + "=" * 65)
print(f"🎉 УСПЕШНО АВТОРИЗОВАН: {me.first_name} (@{me.username})")
print("=" * 65)
print(f"\n✅ Строка сессии сохранена в файл: {output_file.resolve()}")
print("Оттуда её можно скопировать без пробелов и без переносов строк!\n")
print("-" * 65)
print(session_str)
print("-" * 65)
print("\n👉 Скопируйте это значение в Render (переменная SESSION_STRING).")
