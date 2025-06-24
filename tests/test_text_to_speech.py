import os
import pytest
import httpx
from httpx import Response
import base64

os.environ.setdefault("TESTING", "True")

from bot.text_to_speech import text_to_speech
from config import Config

@pytest.mark.asyncio
async def test_text_to_speech_success(monkeypatch):
    monkeypatch.setattr(Config, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GEMINI_TTS_URL", "https://api.example.com/tts")

    async def fake_post(self, url, headers=None, json=None):
        data = base64.b64encode(b"audio").decode()
        return Response(200, json={"audio": {"data": data}}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await text_to_speech("hello")
    assert result == b"audio"

@pytest.mark.asyncio
async def test_text_to_speech_error(monkeypatch):
    monkeypatch.setattr(Config, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GEMINI_TTS_URL", "https://api.example.com/tts")

    async def fake_post(self, url, headers=None, json=None):
        return Response(500, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    from httpx import HTTPStatusError

    with pytest.raises(HTTPStatusError):
        await text_to_speech("hello")
