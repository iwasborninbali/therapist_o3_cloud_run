import os
import pytest
import base64
from unittest.mock import patch

os.environ.setdefault("TESTING", "True")

from bot.text_to_speech import generate_speech, convert_l16_to_wav
from config import Config

def test_convert_l16_to_wav():
    """Test L16 PCM to WAV conversion."""
    pcm_data = b'\x00\x01' * 1000  # Simple test PCM data
    wav_data = convert_l16_to_wav(pcm_data)
    
    # Check WAV header
    assert wav_data[:4] == b'RIFF'
    assert wav_data[8:12] == b'WAVE'
    assert wav_data[12:16] == b'fmt '
    assert wav_data[36:40] == b'data'
    
    # Check that PCM data is appended after header
    assert wav_data[44:] == pcm_data
    
    # Check total length
    assert len(wav_data) == 44 + len(pcm_data)

def test_convert_l16_to_wav_custom_params():
    """Test L16 PCM to WAV conversion with custom parameters."""
    pcm_data = b'\x00\x01' * 500
    wav_data = convert_l16_to_wav(pcm_data, sample_rate=16000, channels=2, bits_per_sample=8)
    
    # Check WAV header exists
    assert wav_data[:4] == b'RIFF'
    assert wav_data[8:12] == b'WAVE'
    
    # Check total length
    assert len(wav_data) == 44 + len(pcm_data)

@pytest.mark.asyncio
async def test_generate_speech_missing_config():
    """Test TTS generation when configuration is missing."""
    with patch.object(Config, 'GEMINI_API_KEY', None):
        with patch.object(Config, 'GEMINI_TTS_URL', 'https://test.com/tts'):
            result = await generate_speech("Hello world")
            assert result is None
    
    with patch.object(Config, 'GEMINI_TTS_URL', None):
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            result = await generate_speech("Hello world")
            assert result is None

def test_convert_l16_to_wav_empty_data():
    """Test L16 PCM to WAV conversion with empty data."""
    pcm_data = b''
    wav_data = convert_l16_to_wav(pcm_data)
    
    # Should still have WAV header
    assert wav_data[:4] == b'RIFF'
    assert wav_data[8:12] == b'WAVE'
    
    # Total length should be just the header (44 bytes)
    assert len(wav_data) == 44

def test_convert_l16_to_wav_different_sample_rates():
    """Test L16 PCM to WAV conversion with different sample rates."""
    pcm_data = b'\x00\x01' * 100
    
    # Test different sample rates
    for sample_rate in [8000, 16000, 22050, 44100, 48000]:
        wav_data = convert_l16_to_wav(pcm_data, sample_rate=sample_rate)
        assert wav_data[:4] == b'RIFF'
        assert wav_data[8:12] == b'WAVE'
        assert len(wav_data) == 44 + len(pcm_data)
