import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram.ext import ContextTypes

os.environ.setdefault("TESTING", "True")

from bot.telegram_router import _process_user_message

@pytest.mark.asyncio
async def test_voice_reply_mode(monkeypatch):
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_voice = AsyncMock()

    monkeypatch.setattr('bot.telegram_router.safe_send_message', AsyncMock())
    monkeypatch.setattr('bot.telegram_router.get_facts_async', AsyncMock(return_value=[]))
    monkeypatch.setattr('bot.telegram_router.get_history_async', AsyncMock(return_value=[]))
    monkeypatch.setattr('bot.telegram_router.build_o4_mini_payload', lambda *a, **k: [])
    monkeypatch.setattr('bot.telegram_router.get_o4_mini_summary', AsyncMock(return_value=(None, None)))

    class Msg:
        tool_calls = None
        content = "hi"
    monkeypatch.setattr('bot.telegram_router.get_o3_response_tool', AsyncMock(return_value=Msg()))
    monkeypatch.setattr('bot.telegram_router.get_user_settings', lambda uid: {"reply_mode": "voice"})
    fake_tts = AsyncMock(return_value=b"aud")
    monkeypatch.setattr('bot.telegram_router.text_to_speech', fake_tts)
    monkeypatch.setattr('bot.telegram_router.keep_typing', AsyncMock())
    monkeypatch.setattr('bot.telegram_router.add_message_with_timestamp', lambda *a, **k: None)

    await _process_user_message(context, 1, "u", "hi")

    fake_tts.assert_called_once()
    context.bot.send_voice.assert_called_once()


@pytest.mark.asyncio
async def test_text_reply_mode(monkeypatch):
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_voice = AsyncMock()
    send_mock = AsyncMock()

    monkeypatch.setattr('bot.telegram_router.safe_send_message', send_mock)
    monkeypatch.setattr('bot.telegram_router.get_facts_async', AsyncMock(return_value=[]))
    monkeypatch.setattr('bot.telegram_router.get_history_async', AsyncMock(return_value=[]))
    monkeypatch.setattr('bot.telegram_router.build_o4_mini_payload', lambda *a, **k: [])
    monkeypatch.setattr('bot.telegram_router.get_o4_mini_summary', AsyncMock(return_value=(None, None)))

    class Msg:
        tool_calls = None
        content = "hi"
    monkeypatch.setattr('bot.telegram_router.get_o3_response_tool', AsyncMock(return_value=Msg()))
    monkeypatch.setattr('bot.telegram_router.get_user_settings', lambda uid: {"reply_mode": "text"})
    monkeypatch.setattr('bot.telegram_router.text_to_speech', AsyncMock())
    monkeypatch.setattr('bot.telegram_router.keep_typing', AsyncMock())
    monkeypatch.setattr('bot.telegram_router.add_message_with_timestamp', lambda *a, **k: None)

    await _process_user_message(context, 1, "u", "hi")

    context.bot.send_voice.assert_not_called()
    assert send_mock.call_count == 1
