#!/usr/bin/env python3
"""
Telegram Userbot Auto-Responder.
Отвечает ТОЛЬКО на первое входящее сообщение от новых пользователей в личке
и перенаправляет в бот-секретарь.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from responder import PrivateResponder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
telegram_ready = False

# Загружаем переменные окружения из .env
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
raw_session = os.getenv("SESSION_STRING", "")
SESSION_STRING = raw_session.strip().strip('"').strip("'").replace("\n", "").replace("\r", "").replace(" ", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "secretary_mellorybot").replace("@", "").strip()
PORT = int(os.getenv("PORT", 8080))

if not API_ID or not API_HASH:
    print("❌ ОШИБКА: Задайте API_ID и API_HASH в файле .env или переменных окружения!")
    print("Их можно получить за 1 минуту на сайте https://my.telegram.org")
    sys.exit(1)

API_ID = int(API_ID)

# Файл для сохранения списка ID, которым уже ответили
DATA_FILE = Path(__file__).resolve().parent / "replied_users.json"
replied_users = set()

if DATA_FILE.exists():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            replied_users = set(json.load(f))
        print(f"📦 Загружено ранее отвеченных пользователей: {len(replied_users)}")
    except Exception as e:
        print(f"⚠️ Ошибка чтения {DATA_FILE}: {e}")

def save_replied():
    try:
        temporary = DATA_FILE.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(sorted(replied_users)), encoding="utf-8")
        temporary.replace(DATA_FILE)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения в {DATA_FILE}: {e}")

# Инициализируем клиент (через строку сессии или локальный файл)
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("user_session", API_ID, API_HASH)

# Точный текст автоответа по запросу пользователя
def get_reply_text() -> str:
    bot_link = f"@{BOT_USERNAME}" if BOT_USERNAME else "моему боту-секретарю"
    return (
        f"👋 Привет! Я сейчас занят.\n\n"
        f"Чтобы быстрее обсудить проект, посмотреть примеры работ или рассчитать смету — переходи в мой бот-секретарь:\n"
        f"👉 {bot_link}\n\n"
        f"Бот работает 24/7, поможет составить ТЗ и сразу передаст мне заявку в приоритетный список!"
    )

responder = PrivateResponder(client, replied_users, save_replied, get_reply_text)
client.add_event_handler(
    responder.handle,
    events.NewMessage(incoming=True, func=lambda e: e.is_private),
)

# Легковесный веб-сервер для бесплатного хостинга (Render, Koyeb, Hugging Face)
async def init_web_server():
    app = web.Application()
    async def health(request):
        ready = telegram_ready and client.is_connected()
        return web.Response(
            text="Telegram Auto-Responder ready" if ready else "Telegram unavailable or not authorized",
            status=200 if ready else 503,
        )
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Health-check веб-сервер запущен на порту {PORT}", flush=True)

async def main():
    global telegram_ready
    # 1. Запускаем веб-сервер в первую очередь, чтобы Render мгновенно увидел открытый порт (Live)
    await init_web_server()
    print("🚀 Запуск Telegram Автоответчика...", flush=True)

    # 2. Подключаемся к Telegram
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ ОШИБКА: Авторизация не удалась! Проверьте значение SESSION_STRING в Render Environment.", flush=True)
        await client.disconnect()
        raise RuntimeError("Telegram authorization failed; check SESSION_STRING")

    me = await client.get_me()
    telegram_ready = True
    print(f"👤 Авторизован как: {me.first_name} (@{me.username or me.id})", flush=True)
    print("🟢 Автоответчик активен! Если чат новый или пустой — автоответ сработает мгновенно.", flush=True)
    try:
        await client.run_until_disconnected()
    finally:
        telegram_ready = False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Скрипт остановлен.")
