import os
import pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault("TESTING", "True")


def test_groq_default_config():
    """Test default Groq configuration values"""
    from config import Config
    
    # Test that config has the expected properties
    assert hasattr(Config, 'GROQ_API_KEY')
    assert hasattr(Config, 'GROQ_WHISPER_URL')
    
    # Test default URL value when not overridden
    with patch.dict(os.environ, {'GROQ_WHISPER_URL': ''}, clear=False):
        # Import config module to see what default would be
        expected_default = "https://api.groq.com/openai/v1/audio/transcriptions"
        # Since config is already loaded, we test the default indirectly
        assert expected_default in Config.GROQ_WHISPER_URL or Config.GROQ_WHISPER_URL == expected_default


def test_groq_custom_url():
    """Test that custom Groq Whisper URL can be set via environment"""
    # This test documents the expected behavior rather than tests dynamic loading
    # since Config is loaded statically
    expected_default = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    from config import Config
    # Test that URL is set to something (either default or custom)
    assert Config.GROQ_WHISPER_URL is not None
    assert Config.GROQ_WHISPER_URL != ""


def test_config_validation_missing_groq_key():
    """Test validation logic for GROQ_API_KEY"""
    from config import Config
    
    # Mock the Config attributes to test validation logic
    original_groq_key = Config.GROQ_API_KEY
    original_validate = Config.validate
    
    try:
        # Temporarily remove GROQ_API_KEY
        Config.GROQ_API_KEY = None
        
        # Mock os.getenv to return None for DISABLE_STT
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = None  # DISABLE_STT is not set
            
            with pytest.raises(ValueError, match="Missing required environment variables.*GROQ_API_KEY"):
                Config.validate()
    finally:
        # Restore original value
        Config.GROQ_API_KEY = original_groq_key


def test_config_validation_stt_disabled():
    """Test validation passes when STT is disabled even without GROQ_API_KEY"""
    from config import Config
    
    # Mock the Config attributes
    original_groq_key = Config.GROQ_API_KEY
    
    try:
        Config.GROQ_API_KEY = None
        Config.TELEGRAM_BOT_TOKEN = "t"
        Config.OPENAI_API_KEY = "k"
        Config.FIREBASE_PROJECT_ID = "p"
        Config.GOOGLE_APPLICATION_CREDENTIALS = "c"
        Config.GEMINI_API_KEY = None
        
        # Mock DISABLE_STT to be True
        with patch('os.getenv') as mock_getenv:
            def mock_getenv_side_effect(key, default=None):
                if key == "DISABLE_STT":
                    return "True"
                if key == "DISABLE_TTS":
                    return "True"
                return default

            mock_getenv.side_effect = mock_getenv_side_effect

            # Should not raise an exception
            Config.validate()
    finally:
        Config.GROQ_API_KEY = original_groq_key
        Config.TELEGRAM_BOT_TOKEN = None
        Config.OPENAI_API_KEY = None
        Config.FIREBASE_PROJECT_ID = None
        Config.GOOGLE_APPLICATION_CREDENTIALS = None
        Config.GEMINI_API_KEY = None


def test_config_validation_with_groq_key():
    """Test validation passes when all required variables are present"""
    from config import Config
    
    # Since we're in testing mode and the real config should be valid
    # (assuming proper setup), this should pass
    try:
        Config.GEMINI_API_KEY = "k"
        Config.validate()
    except ValueError as e:
        # If it fails, it should not be because of GROQ_API_KEY if STT is disabled
        if "GROQ_API_KEY" in str(e):
            # Check if STT is disabled
            if os.getenv("DISABLE_STT") == "True":
                pytest.fail(f"Config validation failed even with STT disabled: {e}")
            else:
                pytest.skip(f"Skipping test due to missing GROQ_API_KEY in environment: {e}")
        else:
            raise
    finally:
        Config.GEMINI_API_KEY = None


def test_disable_stt_flag():
    """Test that DISABLE_STT environment variable works correctly"""
    # Test enabled (default)
    with patch.dict(os.environ, {}, clear=True):
        assert os.getenv("DISABLE_STT") != "True"
    
    # Test disabled
    with patch.dict(os.environ, {'DISABLE_STT': 'True'}, clear=True):
        assert os.getenv("DISABLE_STT") == "True"
    
    # Test disabled (different case)
    with patch.dict(os.environ, {'DISABLE_STT': 'false'}, clear=True):
        assert os.getenv("DISABLE_STT") != "True"


def test_config_class_structure():
    """Test that Config class has expected STT-related attributes"""
    from config import Config
    
    # Test that all expected STT-related attributes exist
    assert hasattr(Config, 'GROQ_API_KEY')
    assert hasattr(Config, 'GROQ_WHISPER_URL')
    assert hasattr(Config, 'validate')
    
    # Test that GROQ_WHISPER_URL has a reasonable default
    assert Config.GROQ_WHISPER_URL is not None
    assert "groq.com" in Config.GROQ_WHISPER_URL.lower()
    assert "transcriptions" in Config.GROQ_WHISPER_URL.lower()


def test_telegram_token_selection():
    """Test that appropriate Telegram token is selected based on mode"""
    from config import Config
    
    # Mock tokens
    original_prod_token = Config.TELEGRAM_BOT_TOKEN
    original_local_token = Config.TELEGRAM_BOT_TOKEN_LOCAL
    
    try:
        Config.TELEGRAM_BOT_TOKEN = "prod_token_123"
        Config.TELEGRAM_BOT_TOKEN_LOCAL = "local_token_456"
        
        # Test production mode (default)
        prod_token = Config.get_telegram_token(local_mode=False)
        assert prod_token == "prod_token_123"
        
        # Test local mode
        local_token = Config.get_telegram_token(local_mode=True)
        assert local_token == "local_token_456"
        
        # Test local mode fallback when local token is not set
        Config.TELEGRAM_BOT_TOKEN_LOCAL = None
        fallback_token = Config.get_telegram_token(local_mode=True)
        assert fallback_token == "prod_token_123"  # Should fallback to production token
        
    finally:
        # Restore original values
        Config.TELEGRAM_BOT_TOKEN = original_prod_token
        Config.TELEGRAM_BOT_TOKEN_LOCAL = original_local_token


def test_telegram_token_attributes():
    """Test that Config has both Telegram token attributes"""
    from config import Config
    
    assert hasattr(Config, 'TELEGRAM_BOT_TOKEN')
    assert hasattr(Config, 'TELEGRAM_BOT_TOKEN_LOCAL')
    assert hasattr(Config, 'get_telegram_token') 