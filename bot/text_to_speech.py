import io
import struct
import base64
import logging
from typing import Optional
import aiohttp
from config import Config

logger = logging.getLogger(__name__)

def convert_l16_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """
    Converts L16 PCM audio data to WAV format.
    
    Args:
        pcm_data: Raw PCM audio data
        sample_rate: Sample rate (default 24000 Hz)
        channels: Number of channels (default 1 for mono)
        bits_per_sample: Bits per sample (default 16)
    
    Returns:
        WAV formatted audio data
    """
    # Calculate derived values
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm_data)
    file_size = 36 + data_size
    
    # Create WAV header
    wav_header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',           # ChunkID
        file_size,         # ChunkSize
        b'WAVE',           # Format
        b'fmt ',           # Subchunk1ID
        16,                # Subchunk1Size (PCM)
        1,                 # AudioFormat (1 = PCM)
        channels,          # NumChannels
        sample_rate,       # SampleRate
        byte_rate,         # ByteRate
        block_align,       # BlockAlign
        bits_per_sample,   # BitsPerSample
        b'data',           # Subchunk2ID
        data_size          # Subchunk2Size
    )
    
    return wav_header + pcm_data

async def generate_speech(text: str, voice: str = "Kore") -> Optional[bytes]:
    """
    Generates speech audio from text using Gemini TTS API.
    
    Args:
        text: Text to convert to speech
        voice: Voice name to use (default: "Kore")
    
    Returns:
        WAV audio data as bytes, or None if generation fails
    """
    if not Config.GEMINI_TTS_URL or not Config.GEMINI_API_KEY:
        logger.error("Gemini TTS URL or API key not configured")
        return None
    
    # Инструкции для создания эмпатичного голоса терапевта
    voice_instructions = """
    Говори с теплым, эмпатичным и поддерживающим тоном профессионального психолога-терапевта. 
    Твой голос должен быть:
    - Спокойным и успокаивающим
    - Понимающим и сочувствующим
    - Профессиональным, но дружелюбным
    - Мягким, без резких интонаций
    - Внимательным и заботливым
    
    Избегай:
    - Слишком формального или холодного тона
    - Быстрой или торопливой речи
    - Резких переходов в интонации
    
    Текст для озвучивания:
    """
    
    full_text = voice_instructions + text
    
    payload = {
        "contents": [{
            "parts": [{"text": full_text}]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice
                    }
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{Config.GEMINI_TTS_URL}?key={Config.GEMINI_API_KEY}",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"TTS API error {response.status}: {error_text}")
                    return None
                
                result = await response.json()
                
                # Extract audio data from response
                try:
                    candidates = result.get("candidates", [])
                    if not candidates:
                        logger.error("No candidates in TTS response")
                        return None
                    
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if not parts:
                        logger.error("No parts in TTS response content")
                        return None
                    
                    inline_data = parts[0].get("inlineData", {})
                    if not inline_data:
                        logger.error("No inlineData in TTS response")
                        return None
                    
                    audio_data_b64 = inline_data.get("data")
                    mime_type = inline_data.get("mimeType", "")
                    
                    if not audio_data_b64:
                        logger.error("No audio data in TTS response")
                        return None
                    
                    # Decode base64 audio data
                    pcm_data = base64.b64decode(audio_data_b64)
                    logger.info(f"Decoded {len(pcm_data)} bytes of PCM data, MIME type: {mime_type}")
                    
                    # Parse sample rate from MIME type if available
                    sample_rate = 24000  # default
                    if "rate=" in mime_type:
                        try:
                            rate_part = [part for part in mime_type.split(";") if "rate=" in part][0]
                            sample_rate = int(rate_part.split("=")[1])
                        except (IndexError, ValueError):
                            logger.warning(f"Could not parse sample rate from MIME type: {mime_type}")
                    
                    # Convert L16 PCM to WAV
                    wav_data = convert_l16_to_wav(pcm_data, sample_rate=sample_rate)
                    logger.info(f"Converted to WAV format: {len(wav_data)} bytes")
                    
                    return wav_data
                    
                except KeyError as e:
                    logger.error(f"Missing key in TTS response: {e}")
                    logger.error(f"Response structure: {result}")
                    return None
                    
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error during TTS generation: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during TTS generation: {e}")
        return None
