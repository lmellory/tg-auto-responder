import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from responder import PrivateResponder


class ResponderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.history = []
        self.client = SimpleNamespace(get_messages=AsyncMock(side_effect=self.get_messages))
        self.replied = set()
        self.save = Mock()
        self.handler = PrivateResponder(self.client, self.replied, self.save, lambda: "reply", delay=0)

    async def get_messages(self, chat_id, *, limit, max_id):
        return [message for message in self.history if message.id < max_id][:limit]

    def event(self, message_id=100, text="hello", **sender_fields):
        return SimpleNamespace(
            id=message_id, chat_id=7, sender_id=7, raw_text=text,
            out=False, is_private=True,
            get_sender=AsyncMock(return_value=SimpleNamespace(bot=False, **sender_fields)),
            reply=AsyncMock(),
        )

    async def test_new_person_gets_reply(self):
        event = self.event()
        await self.handler.handle(event)
        event.reply.assert_awaited_once_with("reply")
        self.assertIn(7, self.replied)
        self.save.assert_called_once()

    async def test_burst_does_not_turn_first_message_into_old_conversation(self):
        first, second, third = self.event(100), self.event(101), self.event(102)
        self.history = [third, second, first]
        # This is the production bug: the old unbounded lookup sees 3 messages.
        self.assertGreater(len(self.history), 1)
        await asyncio.gather(*(self.handler.handle(event) for event in [first, second, third]))
        self.assertEqual(sum(event.reply.await_count for event in [first, second, third]), 1)
        first.reply.assert_awaited_once()

    async def test_burst_processed_out_of_order_still_replies_to_first(self):
        first, second = self.event(100), self.event(101)
        self.history = [second, first]
        await self.handler.handle(second)
        await self.handler.handle(first)
        first.reply.assert_awaited_once()
        second.reply.assert_not_awaited()

    async def test_existing_conversation_is_ignored(self):
        self.history = [SimpleNamespace(id=99)]
        event = self.event()
        await self.handler.handle(event)
        event.reply.assert_not_awaited()
        self.save.assert_not_called()

    async def test_saved_user_not_contacted_again_even_after_history_deleted(self):
        self.replied.add(7)
        event = self.event()
        await self.handler.handle(event)
        event.reply.assert_not_awaited()
        self.client.get_messages.assert_not_awaited()

    async def test_duplicate_updates_send_once(self):
        first, duplicate = self.event(), self.event()
        await asyncio.gather(self.handler.handle(first), self.handler.handle(duplicate))
        self.assertEqual(first.reply.await_count + duplicate.reply.await_count, 1)

    async def test_failed_send_not_saved_and_duplicate_can_retry(self):
        event = self.event()
        event.reply.side_effect = RuntimeError("send unavailable")
        with self.assertLogs("responder", level="ERROR"):
            await self.handler.handle(event)
        self.assertNotIn(7, self.replied)
        self.save.assert_not_called()
        event.reply.side_effect = None
        await self.handler.handle(event)
        self.assertIn(7, self.replied)

    async def test_history_failure_does_not_message_an_existing_contact(self):
        self.client.get_messages.side_effect = RuntimeError("history unavailable")
        event = self.event()
        with self.assertLogs("responder", level="ERROR"):
            await self.handler.handle(event)
        event.reply.assert_not_awaited()

    async def test_test_command_preserved(self):
        self.replied.add(7)
        self.history = [SimpleNamespace(id=99)]
        event = self.event(text="/test")
        await self.handler.handle(event)
        event.reply.assert_awaited_once()
        self.client.get_messages.assert_not_awaited()

    async def test_bots_are_ignored(self):
        event = self.event()
        event.get_sender.return_value.bot = True
        await self.handler.handle(event)
        event.reply.assert_not_awaited()

    async def test_groups_and_outgoing_messages_ignored(self):
        for field in ("out", "is_private"):
            event = self.event()
            setattr(event, field, field == "out")
            await self.handler.handle(event)
            event.get_sender.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
