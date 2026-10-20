#!/usr/bin/env python3
"""Create and verify a Telegram session without printing credentials."""
import os
from getpass import getpass
from pathlib import Path
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession


def main():
    project_dir = Path(__file__).resolve().parent
    load_dotenv(project_dir / '.env')
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    if not api_id or not api_hash:
        print('API_ID и API_HASH доступны на https://my.telegram.org в API development tools.')
        api_id = input('API_ID: ').strip()
        api_hash = getpass('API_HASH (ввод скрыт): ').strip()
    api_id = int(api_id)
    print('Подключаюсь к Telegram. Код и пароль вводите только в этом окне.')
    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        client.start(
            phone=lambda: input('Номер телефона с кодом страны: ').strip(),
            code_callback=lambda: getpass('Код входа из Telegram (ввод скрыт): ').strip(),
            password=lambda: getpass('Пароль двухэтапной проверки (ввод скрыт): '),
        )
        client.get_me()
        session_str = client.session.save()
    finally:
        client.disconnect()
    print('Проверяю новую сессию...')
    verifier = TelegramClient(StringSession(session_str), api_id, api_hash)
    try:
        verifier.connect()
        if not verifier.is_user_authorized():
            raise RuntimeError('Telegram не подтвердил новую сессию. Файл не изменён.')
        verifier.get_me()
    finally:
        verifier.disconnect()
    output_file = project_dir / 'session_string.txt'
    temporary = project_dir / 'session_string.txt.tmp'
    temporary.write_text(session_str.strip(), encoding='utf-8')
    temporary.replace(output_file)
    print(f'Вход подтверждён. Новая сессия сохранена: {output_file}')
    print('Замените SESSION_STRING в Render Environment содержимым этого файла.')
    print('Не отправляйте строку сессии в чат и не загружайте её в GitHub.')


if __name__ == '__main__':
    main()
