"""Startup and readiness checks with a fake Telegram client; no external traffic."""
import importlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aiohttp.test_utils import make_mocked_request
import dotenv
import telethon


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = Mock()
        self.client.connect = AsyncMock()
        self.client.disconnect = AsyncMock()
        self.client.is_user_authorized = AsyncMock(return_value=True)
        self.client.get_me = AsyncMock(return_value=SimpleNamespace(first_name="Test", username="test"))
        self.client.run_until_disconnected = AsyncMock()
        self.client.is_connected.return_value = True
        sys.modules.pop("main", None)
        test_env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT") if key in os.environ}
        test_env.update(API_ID="1", API_HASH="test", SESSION_STRING="")
        with patch.dict(os.environ, test_env, clear=True), \
             patch.object(dotenv, "load_dotenv"), patch.object(telethon, "TelegramClient", return_value=self.client):
            self.app = importlib.import_module("main")

    async def asyncTearDown(self):
        sys.modules.pop("main", None)

    async def test_health_reports_actual_readiness(self):
        runner = Mock(setup=AsyncMock())
        site = Mock(start=AsyncMock())
        with patch.object(self.app.web, "AppRunner", return_value=runner) as create_runner, \
             patch.object(self.app.web, "TCPSite", return_value=site):
            await self.app.init_web_server()
        application = create_runner.call_args.args[0]
        request = make_mocked_request("GET", "/health", app=application)
        route = await application.router.resolve(request)
        self.assertEqual((await route.handler(request)).status, 503)
        self.app.telegram_ready = True
        self.assertEqual((await route.handler(request)).status, 200)
        self.client.is_connected.return_value = False
        self.assertEqual((await route.handler(request)).status, 503)

    async def test_invalid_session_fails_instead_of_sleeping_forever(self):
        self.client.is_user_authorized.return_value = False
        with patch.object(self.app, "init_web_server", new=AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, "authorization failed"):
                await self.app.main()
        self.client.disconnect.assert_awaited_once()
        self.assertFalse(self.app.telegram_ready)

    async def test_ready_only_while_telegram_loop_is_running(self):
        async def run_loop():
            self.assertTrue(self.app.telegram_ready)
        self.client.run_until_disconnected.side_effect = run_loop
        with patch.object(self.app, "init_web_server", new=AsyncMock()):
            await self.app.main()
        self.assertFalse(self.app.telegram_ready)
        self.client.add_event_handler.assert_called_once()


if __name__ == "__main__":
    unittest.main()
