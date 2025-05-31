import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from bot.firestore_client import has_processed_update, mark_update_processed
from bot.telegram_router import handle_update

# Mock Telegram update for testing
TELEGRAM_UPDATE = {
    "update_id": 987654321,
    "message": {
        "message_id": 1,
        "from": {
            "id": 54321,
            "is_bot": False,
            "first_name": "DedupeTest",
            "username": "dedupeuser"
        },
        "chat": {
            "id": 54321,
            "first_name": "DedupeTest",
            "username": "dedupeuser",
            "type": "private"
        },
        "date": 1612345678,
        "text": "duplicate test message"
    }
}


@pytest.fixture
def mock_processed_updates():
    """Mock processed updates tracking"""
    processed_updates = set()
    
    def mock_has_processed(update_id):
        return update_id in processed_updates
    
    def mock_mark_processed(update_id):
        processed_updates.add(update_id)
        return True
    
    with patch('bot.telegram_router.has_processed_update', side_effect=mock_has_processed), \
         patch('bot.telegram_router.mark_update_processed', side_effect=mock_mark_processed):
        yield processed_updates


@pytest.mark.asyncio
async def test_first_update_is_processed(mock_processed_updates):
    """Test that first update with new update_id is processed"""
    # Mock Telegram bot with async process_update
    mock_bot = MagicMock()
    mock_bot.process_update = AsyncMock()
    
    # Mock Update.de_json to return proper Update object
    mock_update = MagicMock()
    mock_update.update_id = 987654321
    
    with patch('telegram.Update.de_json', return_value=mock_update):
        # Handle update for the first time
        await handle_update(TELEGRAM_UPDATE, mock_bot)
        
        # Verify update was processed
        assert mock_bot.process_update.called
        assert 987654321 in mock_processed_updates


@pytest.mark.asyncio
async def test_duplicate_update_is_skipped(mock_processed_updates):
    """Test that duplicate update_id is skipped"""
    # Mock Telegram bot with async process_update
    mock_bot = MagicMock()
    mock_bot.process_update = AsyncMock()
    
    # Mock Update.de_json to return proper Update object
    mock_update = MagicMock()
    mock_update.update_id = 987654321
    
    with patch('telegram.Update.de_json', return_value=mock_update):
        # Handle update for the first time
        await handle_update(TELEGRAM_UPDATE, mock_bot)
        
        # Reset mock to track second call
        mock_bot.process_update.reset_mock()
        
        # Handle same update again (simulate Telegram retry)
        await handle_update(TELEGRAM_UPDATE, mock_bot)
        
        # Verify second update was NOT processed
        assert not mock_bot.process_update.called
        assert 987654321 in mock_processed_updates


@pytest.mark.asyncio
async def test_different_update_ids_are_processed(mock_processed_updates):
    """Test that different update_ids are both processed"""
    # Mock Telegram bot with async process_update
    mock_bot = MagicMock()
    mock_bot.process_update = AsyncMock()
    
    # Mock Update.de_json to return proper Update objects with different IDs
    def mock_de_json(data, bot):
        mock_update = MagicMock()
        mock_update.update_id = data["update_id"]
        return mock_update
    
    with patch('telegram.Update.de_json', side_effect=mock_de_json):
        # First update
        await handle_update(TELEGRAM_UPDATE, mock_bot)
        
        # Second update with different ID
        update_2 = TELEGRAM_UPDATE.copy()
        update_2["update_id"] = 987654322
        
        await handle_update(update_2, mock_bot)
        
        # Verify both updates were processed (total 2 calls)
        assert mock_bot.process_update.call_count == 2
        assert 987654321 in mock_processed_updates
        assert 987654322 in mock_processed_updates


def test_webhook_endpoint_deduplication(client, mock_processed_updates):
    """Test that webhook endpoint properly handles duplicate updates"""
    # Send first update
    response1 = client.post("/webhook", json=TELEGRAM_UPDATE)
    assert response1.status_code == 200
    
    # Send duplicate update (simulate Telegram retry)
    response2 = client.post("/webhook", json=TELEGRAM_UPDATE)
    assert response2.status_code == 200
    
    # Both should return OK immediately (idempotent)
    assert response1.json() == {"status": "ok"}
    assert response2.json() == {"status": "ok"}
    
    # Note: In test mode, background processing is disabled
    # so we can't test the actual deduplication logic here


@pytest.mark.asyncio
async def test_handle_update_async_behavior():
    """Test that handle_update function works correctly in async context"""
    # Mock Telegram bot with async process_update
    mock_bot = MagicMock()
    mock_bot.process_update = AsyncMock()
    
    # Mock de_json to return proper Update object
    mock_update = MagicMock()
    mock_update.update_id = 123456789
    
    with patch('telegram.Update.de_json', return_value=mock_update), \
         patch('bot.telegram_router.has_processed_update', return_value=False), \
         patch('bot.telegram_router.mark_update_processed', return_value=True):
        
        # Call handle_update
        await handle_update(TELEGRAM_UPDATE, mock_bot)
        
        # Verify the update was processed
        assert mock_bot.process_update.called


@pytest.mark.asyncio
async def test_error_handling_in_background_processing():
    """Test that errors in background processing are handled gracefully"""
    # Mock Telegram bot that raises an exception
    mock_bot = MagicMock()
    mock_bot.process_update = AsyncMock(side_effect=Exception("Test error"))
    
    mock_update = MagicMock()
    mock_update.update_id = 123456789
    
    with patch('telegram.Update.de_json', return_value=mock_update), \
         patch('bot.telegram_router.has_processed_update', return_value=False), \
         patch('bot.telegram_router.mark_update_processed', return_value=True), \
         patch('bot.telegram_router.logger') as mock_logger:
        
        # This should not raise an exception
        await handle_update(TELEGRAM_UPDATE, mock_bot)
        
        # Verify error was logged
        mock_logger.error.assert_called()
