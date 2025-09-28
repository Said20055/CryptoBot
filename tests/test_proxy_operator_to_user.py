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
operator_reply_to_user_handler = proxy_mod.operator_reply_to_user_handler

class DummyMessage:
    def __init__(self, thread_id, is_topic=True):
        self.message_thread_id = thread_id
        self.is_topic_message = is_topic
        self.from_user = SimpleNamespace(id=999)
        self._copied = []
    async def copy_to(self, chat_id=None, reply_markup=None):
        self._copied.append((chat_id, reply_markup))
    async def reply(self, text):
        return None


@pytest.mark.asyncio
async def test_operator_reply_happy_path(monkeypatch):
    topic_id = 555
    user_id = 123
    message = DummyMessage(topic_id)

    async def fake_get_order_by_topic_id(tid):
        assert tid == topic_id
        return {'order_id': 1, 'user_id': user_id}

    monkeypatch.setattr(proxy_mod, 'get_order_by_topic_id', fake_get_order_by_topic_id)

    await operator_reply_to_user_handler(message)

    assert message._copied, "Operator reply was not copied to user"
    assert message._copied[0][0] == user_id


@pytest.mark.asyncio
async def test_operator_reply_no_order(monkeypatch):
    topic_id = 555
    message = DummyMessage(topic_id)

    async def fake_none(tid):
        return None
    monkeypatch.setattr(proxy_mod, 'get_order_by_topic_id', fake_none)

    await operator_reply_to_user_handler(message)
    assert not message._copied
