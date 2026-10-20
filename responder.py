"""Message handling independent of Telegram login and the health server."""

import asyncio
import logging

logger = logging.getLogger(__name__)
TEST_COMMANDS = {"/test", "/reset", "тест", "test"}


class PrivateResponder:
    def __init__(self, client, replied_users, save_replied, get_reply_text, delay=1.0):
        self.client = client
        self.replied_users = replied_users
        self.save_replied = save_replied
        self.get_reply_text = get_reply_text
        self.delay = delay
        self.locks = {}

    async def handle(self, event):
        if event.out or not event.is_private:
            return
        sender = await event.get_sender()
        if not sender or getattr(sender, "bot", False) or not event.sender_id:
            return

        sender_id = event.sender_id
        is_test = (event.raw_text or "").strip().lower() in TEST_COMMANDS
        lock = self.locks.setdefault(sender_id, asyncio.Lock())
        async with lock:
            if sender_id in self.replied_users and not is_test:
                logger.info("Skipping user %s: already replied", sender_id)
                return

            if not is_test:
                try:
                    # Only history BEFORE this event counts. Messages sent in
                    # the same incoming burst must not hide the first message.
                    previous = await self.client.get_messages(
                        event.chat_id, limit=1, max_id=event.id
                    )
                except Exception:
                    logger.exception("Cannot check history for user %s; reply skipped", sender_id)
                    return
                if previous:
                    logger.info("Skipping user %s: earlier conversation exists", sender_id)
                    return

            try:
                await asyncio.sleep(self.delay)
                await event.reply(self.get_reply_text())
            except Exception:
                logger.exception("Auto-reply failed for user %s", sender_id)
                return

            # A failed send must never be recorded as a successful reply.
            self.replied_users.add(sender_id)
            self.save_replied()
            logger.info("Auto-reply sent to user %s", sender_id)
