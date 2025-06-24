import base64
import httpx
import logging

from config import Config
from bot.retry_utils import retry_async

logger = logging.getLogger(__name__)

@retry_async()
async def text_to_speech(text: str) -> bytes:
    payload = {
        "text": text,
        "audioConfig": {
            "audioEncoding": "OGG_OPUS",
            "sampleRateHertz": 48000,
        },
    }
    url = f"{Config.GEMINI_TTS_URL}?key={Config.GEMINI_API_KEY}"

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(url, json=payload)
        r.raise_for_status()
        audio_b64 = r.json()["audio"]["data"]
    return base64.b64decode(audio_b64)
