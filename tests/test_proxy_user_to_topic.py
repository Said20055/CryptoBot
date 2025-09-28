import pytest
import asyncio
from types import SimpleNamespace

import pytest_asyncio

import importlib.util
import os
proxy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'handlers', 'crypto', 'proxy.py')
spec = importlib.util.spec_from_file_location('handlers_crypto_proxy', proxy_path)
proxy_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proxy_mod)
user_reply_to_topic_handler = proxy_mod.user_reply_to_topic_handler


class DummyState:
    def __init__(self):
        self._state = None
    async def clear(self):
        self._state = None
    async def set_state(self, s):
        self._state = s


class DummyBot:
    def __init__(self):
        self.sent = []
    async def send_message(self, chat_id=None, message_thread_id=None, text=None, parse_mode=None):
        self.sent.append((chat_id, message_thread_id, text))


@pytest.mark.asyncio
async def test_user_reply_to_topic_happy_path(monkeypatch):
    # Arrange
    user_id = 123
    topic_id = 555
    message_text = "Hello operator"

    message = SimpleNamespace()
    message.from_user = SimpleNamespace(id=user_id, full_name="Test User")
    message.text = message_text
    message.bot = DummyBot()
    message.answer = lambda text, **kw: asyncio.create_task(asyncio.sleep(0))

    state = DummyState()

    # Mock DB helper
    async def fake_get_active_order_for_user(uid):
        assert uid == user_id
        return {'order_id': 1, 'topic_id': topic_id}

    # proxy_mod imported the helper at module import time; patch it on proxy_mod
    monkeypatch.setattr(proxy_mod, 'get_active_order_for_user', fake_get_active_order_for_user)

    # Act
    await user_reply_to_topic_handler(message, state)

    # Assert
    assert message.bot.sent, "Bot did not send any messages to topic"
    assert message.bot.sent[0][1] == topic_id


@pytest.mark.asyncio
async def test_user_reply_no_active_order(monkeypatch):
    user_id = 123
    message = SimpleNamespace()
    message.from_user = SimpleNamespace(id=user_id, full_name="Test User")
    message.text = "Hi"
    message.bot = DummyBot()
    async def answer_stub(text, **kw):
        return None
    message.answer = answer_stub
    state = DummyState()

    async def fake_get_none(uid):
        return None
    monkeypatch.setattr('utils.database.db_helpers.get_active_order_for_user', fake_get_none)

    await user_reply_to_topic_handler(message, state)
    assert not message.bot.sent
