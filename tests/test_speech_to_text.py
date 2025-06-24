import os
import pytest
import httpx
from httpx import Response

os.environ.setdefault("TESTING", "True")

from bot.speech_to_text import transcribe_audio
from config import Config

@pytest.mark.asyncio
async def test_transcribe_audio_success(monkeypatch):
    monkeypatch.setattr(Config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        return Response(200, json={"text": "hello"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await transcribe_audio(b"bytes")
    assert result == "hello"

@pytest.mark.asyncio
async def test_transcribe_audio_empty(monkeypatch):
    monkeypatch.setattr(Config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        return Response(200, json={}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(ValueError):
        await transcribe_audio(b"bytes")

@pytest.mark.asyncio
async def test_transcribe_audio_unauthorized(monkeypatch):
    monkeypatch.setattr(Config, "GROQ_API_KEY", "invalid")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        return Response(401, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    from httpx import HTTPStatusError

    with pytest.raises(HTTPStatusError):
        await transcribe_audio(b"bytes")
