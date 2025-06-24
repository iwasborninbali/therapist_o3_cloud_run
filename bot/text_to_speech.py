import base64
import httpx
import logging

from config import Config
from bot.retry_utils import retry_async

logger = logging.getLogger(__name__)

@retry_async()
async def text_to_speech(text: str) -> bytes:
    payload = {
        "contents": [{
            "parts": [{
                "text": text
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Kore"
                    }
                }
            }
        }
    }
    url = f"{Config.GEMINI_TTS_URL}?key={Config.GEMINI_API_KEY}"

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(url, json=payload)
        r.raise_for_status()
        # Response structure for new TTS API
        audio_b64 = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    return base64.b64decode(audio_b64)
