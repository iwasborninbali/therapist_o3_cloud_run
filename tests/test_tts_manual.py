#!/usr/bin/env python3
"""
Manual TTS test script
"""

import os
import sys
import asyncio
import logging

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment for local development
os.environ["RUN_MODE"] = "local"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_tts():
    """Test TTS generation"""
    try:
        from bot.text_to_speech import generate_speech
        from config import Config
        
        logger.info("Testing TTS generation...")
        logger.info(f"GEMINI_TTS_URL: {Config.GEMINI_TTS_URL}")
        logger.info(f"GEMINI_API_KEY: {'***' if Config.GEMINI_API_KEY else 'None'}")
        
        # Test simple text
        test_text = "Привет! Это тест голосового синтеза."
        
        logger.info(f"Generating speech for: {test_text}")
        audio_data = await generate_speech(test_text)
        
        if audio_data:
            logger.info(f"✅ TTS Success! Generated {len(audio_data)} bytes of audio")
            # Save to file for testing
            with open("test_output.wav", "wb") as f:
                f.write(audio_data)
            logger.info("Audio saved to test_output.wav")
        else:
            logger.error("❌ TTS Failed - returned None")
            
    except Exception as e:
        logger.error(f"❌ Error testing TTS: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_tts()) 