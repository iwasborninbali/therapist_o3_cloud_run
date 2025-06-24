import logging
import httpx
from config import Config
from bot.retry_utils import retry_async

logger = logging.getLogger(__name__)

@retry_async()
async def transcribe_audio(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    """Send audio to Groq Whisper API and return the transcribed text."""
    url = Config.GROQ_WHISPER_URL
    headers = {"Authorization": f"Bearer {Config.GROQ_API_KEY}"}
    data = {"model": "whisper-v3-large"}
    files = {"file": (filename, audio_bytes, "audio/ogg; codecs=opus")}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, data=data, files=files)
        response.raise_for_status()
        result = response.json()
        text = result.get("text", "").strip()
        if not text:
            raise ValueError("Empty transcription")
        return text
