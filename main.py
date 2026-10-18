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
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

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
DATA_FILE = Path("replied_users.json")
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
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(list(replied_users), f)
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

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_private_message(event):
    # Игнорируем собственные исходящие сообщения
    if event.out:
        return

    sender = await event.get_sender()
    if not sender:
        return

    # Игнорируем ботов
    if getattr(sender, "bot", False):
        return

    sender_id = event.sender_id

    # КРИТИЧЕСКИ ВАЖНО: Проверяем, отвечали ли мы уже этому человеку
    if sender_id in replied_users:
        return

    # Защита: проверяем историю переписки. Если в диалоге уже были сообщения ранее,
    # значит это старый знакомый/клиент, автоответ не шлем.
    try:
        messages = await client.get_messages(event.chat_id, limit=3)
        # Если сообщений больше 1 (то есть были старые сообщения до этого), помечаем как отвеченного и выходим
        if len(messages) > 1 and any(m.id != event.id for m in messages):
            replied_users.add(sender_id)
            save_replied()
            return
    except Exception:
        pass

    # Фиксируем, что пользователю ответили (чтобы больше НИКОГДА не повторять)
    replied_users.add(sender_id)
    save_replied()

    print(f"📩 Новое первое сообщение от {sender.first_name} (@{sender.username or sender_id}). Отправляю автоответ...")

    try:
        # Небольшая пауза 1-2 секунды для имитации живого присутствия
        await asyncio.sleep(1.5)
        await event.reply(get_reply_text())
        print(f"✅ Автоответ успешно отправлен пользователю {sender_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки автоответа пользователю {sender_id}: {e}")

# Легковесный веб-сервер для бесплатного хостинга (Render, Koyeb, Hugging Face)
async def init_web_server():
    app = web.Application()
    async def health(request):
        return web.Response(text="Telegram Auto-Responder is running 24/7", status=200)
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Health-check веб-сервер запущен на порту {PORT}")

async def main():
    print("🚀 Запуск Telegram Автоответчика...")
    await client.start()
    me = await client.get_me()
    print(f"👤 Авторизован как: {me.first_name} (@{me.username or me.id})")

    # При первом запуске подгружаем все существующие диалоги,
    # чтобы скрипт НИКОГДА не отвечал вашим текущим друзьям и контактам
    if len(replied_users) == 0:
        print("🔍 Первичная калибровка: сканирую существующие диалоги, чтобы не писать старым контактам...")
        count = 0
        async for dialog in client.iter_dialogs():
            if dialog.is_user and not getattr(dialog.entity, "bot", False):
                replied_users.add(dialog.id)
                count += 1
        save_replied()
        print(f"✅ Учтено {count} существующих контактов. Автоответ сработает ТОЛЬКО для новых людей!")

    await init_web_server()
    print("🟢 Автоответчик активен и слушает входящие сообщения...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Скрипт остановлен.")
