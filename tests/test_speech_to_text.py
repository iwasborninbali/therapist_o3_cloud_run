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

@pytest.mark.asyncio
async def test_transcribe_audio_whitespace_only(monkeypatch):
    """Test that whitespace-only responses are treated as empty"""
    monkeypatch.setattr(Config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        return Response(200, json={"text": "   \n\t  "}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(ValueError, match="Empty transcription"):
        await transcribe_audio(b"bytes")

@pytest.mark.asyncio
async def test_transcribe_audio_rate_limit(monkeypatch):
    """Test handling of rate limit errors"""
    monkeypatch.setattr(Config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        return Response(429, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        await transcribe_audio(b"bytes")

@pytest.mark.asyncio
async def test_transcribe_audio_timeout(monkeypatch):
    """Test handling of timeout errors"""
    monkeypatch.setattr(Config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(httpx.TimeoutException):
        await transcribe_audio(b"bytes")

@pytest.mark.asyncio
async def test_transcribe_audio_with_custom_filename(monkeypatch):
    """Test transcription with custom filename"""
    monkeypatch.setattr(Config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        # Verify that custom filename is used
        assert files["file"][0] == "custom.mp3"
        return Response(200, json={"text": "custom test"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await transcribe_audio(b"bytes", filename="custom.mp3")
    assert result == "custom test"

@pytest.mark.asyncio
async def test_transcribe_audio_invalid_json_response(monkeypatch):
    """Test handling of invalid JSON response"""
    monkeypatch.setattr(Config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(Config, "GROQ_WHISPER_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

    async def fake_post(self, url, headers=None, data=None, files=None):
        response = Response(200, request=httpx.Request("POST", url))
        response._content = b"invalid json"
        return response

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(Exception):  # Will raise JSONDecodeError or similar
        await transcribe_audio(b"bytes")
