import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Voice, Audio, Chat, User, File
from telegram.ext import ContextTypes

os.environ.setdefault("TESTING", "True")

from bot.telegram_router import handle_voice_message, _process_user_message


@pytest.fixture
def mock_update_voice():
    """Create a mock Update with voice message"""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 67890
    
    update.message = MagicMock(spec=Message)
    update.message.voice = MagicMock(spec=Voice)
    update.message.voice.file_unique_id = "test_voice_id"
    update.message.voice.duration = 10
    update.message.voice.file_size = 50000
    update.message.audio = None
    
    return update


@pytest.fixture
def mock_update_audio():
    """Create a mock Update with audio message"""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 67890
    
    update.message = MagicMock(spec=Message)
    update.message.voice = None
    update.message.audio = MagicMock(spec=Audio)
    update.message.audio.file_unique_id = "test_audio_id"
    update.message.audio.duration = 15
    update.message.audio.file_size = 75000
    
    return update


@pytest.fixture
def mock_context():
    """Create a mock context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.mark.asyncio
async def test_handle_voice_message_success(mock_update_voice, mock_context):
    """Test successful voice message processing"""
    # Mock the file download
    mock_file = MagicMock(spec=File)
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_audio_data"))
    mock_update_voice.message.voice.get_file = AsyncMock(return_value=mock_file)
    
    with patch('bot.telegram_router.transcribe_audio', new_callable=AsyncMock) as mock_transcribe, \
         patch('bot.telegram_router._process_user_message', new_callable=AsyncMock) as mock_process:
        
        mock_transcribe.return_value = "Hello, this is a test message"
        
        await handle_voice_message(mock_update_voice, mock_context)
        
        # Verify transcription was called
        mock_transcribe.assert_called_once_with(b"fake_audio_data")
        
        # Verify message processing was called with transcribed text
        mock_process.assert_called_once_with(
            mock_context, 12345, "67890", "Hello, this is a test message"
        )


@pytest.mark.asyncio
async def test_handle_voice_message_too_long(mock_update_voice, mock_context):
    """Test rejection of voice messages that are too long"""
    mock_update_voice.message.voice.duration = 150  # Too long
    
    with patch('bot.telegram_router.safe_send_message', new_callable=AsyncMock) as mock_send:
        await handle_voice_message(mock_update_voice, mock_context)
        
        mock_send.assert_called_once_with(
            mock_context, 12345, "Voice message is too long. Please keep it under 2 minutes."
        )


@pytest.mark.asyncio
async def test_handle_voice_message_too_large(mock_update_voice, mock_context):
    """Test rejection of voice messages that are too large"""
    mock_update_voice.message.voice.file_size = 6_000_000  # Too large
    
    with patch('bot.telegram_router.safe_send_message', new_callable=AsyncMock) as mock_send:
        await handle_voice_message(mock_update_voice, mock_context)
        
        mock_send.assert_called_once_with(
            mock_context, 12345, "Audio file is too large. Please keep it under 5MB."
        )


@pytest.mark.asyncio
async def test_handle_voice_message_stt_disabled(mock_update_voice, mock_context):
    """Test handling when STT is disabled"""
    with patch.dict(os.environ, {'DISABLE_STT': 'True'}), \
         patch('bot.telegram_router.safe_send_message', new_callable=AsyncMock) as mock_send:
        
        await handle_voice_message(mock_update_voice, mock_context)
        
        # Should send a disabled message
        mock_send.assert_called_once_with(
            mock_context, 12345, "⚠️ Распознавание речи временно отключено."
        )


@pytest.mark.asyncio
async def test_handle_voice_message_transcription_failed(mock_update_voice, mock_context):
    """Test handling of transcription failures"""
    # Mock the file download
    mock_file = MagicMock(spec=File)
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_audio_data"))
    mock_update_voice.message.voice.get_file = AsyncMock(return_value=mock_file)
    
    with patch('bot.telegram_router.transcribe_audio', new_callable=AsyncMock) as mock_transcribe, \
         patch('bot.telegram_router.safe_send_message', new_callable=AsyncMock) as mock_send:
        
        mock_transcribe.side_effect = Exception("API Error")
        
        await handle_voice_message(mock_update_voice, mock_context)
        
        mock_send.assert_called_once_with(
            mock_context, 12345, "Sorry, I couldn't process that audio message."
        )


@pytest.mark.asyncio
async def test_handle_voice_message_empty_transcription(mock_update_voice, mock_context):
    """Test handling of empty transcription results"""
    # Mock the file download
    mock_file = MagicMock(spec=File)
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_audio_data"))
    mock_update_voice.message.voice.get_file = AsyncMock(return_value=mock_file)
    
    with patch('bot.telegram_router.transcribe_audio', new_callable=AsyncMock) as mock_transcribe, \
         patch('bot.telegram_router.safe_send_message', new_callable=AsyncMock) as mock_send:
        
        mock_transcribe.return_value = ""  # Empty result
        
        await handle_voice_message(mock_update_voice, mock_context)
        
        mock_send.assert_called_once_with(
            mock_context, 12345, "I couldn't understand the audio message."
        )


@pytest.mark.asyncio
async def test_handle_audio_message_success(mock_update_audio, mock_context):
    """Test successful audio message processing (not voice)"""
    # Mock the file download
    mock_file = MagicMock(spec=File)
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_audio_data"))
    mock_update_audio.message.audio.get_file = AsyncMock(return_value=mock_file)
    
    with patch('bot.telegram_router.transcribe_audio', new_callable=AsyncMock) as mock_transcribe, \
         patch('bot.telegram_router._process_user_message', new_callable=AsyncMock) as mock_process:
        
        mock_transcribe.return_value = "Audio message transcribed"
        
        await handle_voice_message(mock_update_audio, mock_context)
        
        # Verify transcription was called
        mock_transcribe.assert_called_once_with(b"fake_audio_data")
        
        # Verify message processing was called with transcribed text
        mock_process.assert_called_once_with(
            mock_context, 12345, "67890", "Audio message transcribed"
        )


@pytest.mark.asyncio
async def test_handle_voice_message_download_failed(mock_update_voice, mock_context):
    """Test handling of file download failures"""
    mock_update_voice.message.voice.get_file = AsyncMock(side_effect=Exception("Download failed"))
    
    with patch('bot.telegram_router.safe_send_message', new_callable=AsyncMock) as mock_send:
        await handle_voice_message(mock_update_voice, mock_context)
        
        mock_send.assert_called_once_with(
            mock_context, 12345, "Sorry, I couldn't process that audio message."
        ) 