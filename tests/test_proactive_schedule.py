#!/usr/bin/env python3
"""
Tests for proactive message scheduling logic.
Tests deduplication and timezone-based scheduling.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_firestore_data():
    """Mock Firestore data for testing"""
    return {
        "user_settings": {
            "user1": {"timezone": "Asia/Makassar"},
            "user2": {"timezone": "Europe/Moscow"},
        },
        "proactive_meta": {
            "user1": {},
            "user2": {},
        }
    }


@pytest.fixture
def mock_datetime():
    """Mock datetime for testing"""
    # Mock a specific time: 10:00 AM Bali time (2:00 AM UTC)
    bali_time = datetime(2025, 5, 25, 10, 0, 0, tzinfo=ZoneInfo("Asia/Makassar"))
    utc_time = bali_time.astimezone(ZoneInfo("UTC"))
    return utc_time


class TestProactiveScheduling:
    
    @patch('scripts.proactive_messages.get_all_users_with_settings')
    @patch('scripts.proactive_messages.get_last_proactive_meta')
    @patch('scripts.proactive_messages.set_last_proactive_meta')
    @patch('scripts.proactive_messages.send_telegram_message')
    @patch('scripts.proactive_messages.add_message')
    @patch('scripts.proactive_messages.generate_proactive_message')
    @patch('scripts.proactive_messages.datetime')
    def test_should_send_morning_message_bali(
        self, mock_datetime_class, mock_generate, mock_add_message, 
        mock_send_telegram, mock_set_meta, mock_get_meta, mock_get_users
    ):
        """Test that morning message is sent for Bali timezone at 10:00 AM"""
        from scripts.proactive_messages import should_send_proactive_message
        
        # Mock current time as 10:00 AM Bali time
        bali_time = datetime(2025, 5, 25, 10, 0, 0, tzinfo=ZoneInfo("Asia/Makassar"))
        mock_datetime_class.now.return_value = bali_time
        
        # Mock no previous message sent today
        mock_get_meta.return_value = {}
        
        should_send, slot = should_send_proactive_message("user1", "Asia/Makassar")
        
        assert should_send is True
        assert slot == "morning"
    
    @patch('scripts.proactive_messages.get_all_users_with_settings')
    @patch('scripts.proactive_messages.get_last_proactive_meta')
    @patch('scripts.proactive_messages.set_last_proactive_meta')
    @patch('scripts.proactive_messages.send_telegram_message')
    @patch('scripts.proactive_messages.add_message')
    @patch('scripts.proactive_messages.generate_proactive_message')
    @patch('scripts.proactive_messages.datetime')
    def test_should_not_send_duplicate_message(
        self, mock_datetime_class, mock_generate, mock_add_message, 
        mock_send_telegram, mock_set_meta, mock_get_meta, mock_get_users
    ):
        """Test that duplicate message is not sent if already sent today"""
        from scripts.proactive_messages import should_send_proactive_message
        
        # Mock current time as 10:00 AM Bali time
        bali_time = datetime(2025, 5, 25, 10, 0, 0, tzinfo=ZoneInfo("Asia/Makassar"))
        mock_datetime_class.now.return_value = bali_time
        
        # Mock that morning message was already sent today
        mock_get_meta.return_value = {"morning": "2025-05-25"}
        
        should_send, slot = should_send_proactive_message("user1", "Asia/Makassar")
        
        assert should_send is False
        assert slot is None
    
    @patch('scripts.proactive_messages.get_all_users_with_settings')
    @patch('scripts.proactive_messages.get_last_proactive_meta')
    @patch('scripts.proactive_messages.set_last_proactive_meta')
    @patch('scripts.proactive_messages.send_telegram_message')
    @patch('scripts.proactive_messages.add_message')
    @patch('scripts.proactive_messages.generate_proactive_message')
    @patch('scripts.proactive_messages.datetime')
    def test_should_not_send_outside_schedule(
        self, mock_datetime_class, mock_generate, mock_add_message, 
        mock_send_telegram, mock_set_meta, mock_get_meta, mock_get_users
    ):
        """Test that message is not sent outside of scheduled hours"""
        from scripts.proactive_messages import should_send_proactive_message
        
        # Mock current time as 3:00 PM Bali time (not a scheduled time)
        bali_time = datetime(2025, 5, 25, 15, 0, 0, tzinfo=ZoneInfo("Asia/Makassar"))
        mock_datetime_class.now.return_value = bali_time
        
        # Mock no previous message sent
        mock_get_meta.return_value = {}
        
        should_send, slot = should_send_proactive_message("user1", "Asia/Makassar")
        
        assert should_send is False
        assert slot is None
    
    @patch('scripts.proactive_messages.get_all_users_with_settings')
    @patch('scripts.proactive_messages.get_last_proactive_meta')
    @patch('scripts.proactive_messages.set_last_proactive_meta')
    @patch('scripts.proactive_messages.send_telegram_message')
    @patch('scripts.proactive_messages.add_message')
    @patch('scripts.proactive_messages.generate_proactive_message')
    @patch('scripts.proactive_messages.datetime')
    def test_evening_message_moscow(
        self, mock_datetime_class, mock_generate, mock_add_message, 
        mock_send_telegram, mock_set_meta, mock_get_meta, mock_get_users
    ):
        """Test that evening message is sent for Moscow timezone at 8:00 PM"""
        from scripts.proactive_messages import should_send_proactive_message
        
        # Mock current time as 8:00 PM Moscow time
        moscow_time = datetime(2025, 5, 25, 20, 0, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        mock_datetime_class.now.return_value = moscow_time
        
        # Mock no previous message sent today
        mock_get_meta.return_value = {}
        
        should_send, slot = should_send_proactive_message("user2", "Europe/Moscow")
        
        assert should_send is True
        assert slot == "evening"
    
    @patch('scripts.proactive_messages.get_all_users_with_settings')
    @patch('scripts.proactive_messages.get_last_proactive_meta')
    @patch('scripts.proactive_messages.set_last_proactive_meta')
    @patch('scripts.proactive_messages.send_telegram_message')
    @patch('scripts.proactive_messages.add_message')
    @patch('scripts.proactive_messages.generate_proactive_message')
    @patch('scripts.proactive_messages.datetime')
    def test_process_all_users_sends_only_to_eligible(
        self, mock_datetime_class, mock_generate, mock_add_message, 
        mock_send_telegram, mock_set_meta, mock_get_meta, mock_get_users
    ):
        """Test that process_all_users only sends to eligible users"""
        from scripts.proactive_messages import process_all_users
        
        # Mock users
        mock_get_users.return_value = [
            ("user1", "Asia/Makassar"),
            ("user2", "Europe/Moscow"),
        ]
        
        # Mock current time as 10:00 AM Bali time (2:00 AM UTC)
        # This means it's 5:00 AM Moscow time - not a scheduled time
        bali_time = datetime(2025, 5, 25, 10, 0, 0, tzinfo=ZoneInfo("Asia/Makassar"))
        moscow_time = datetime(2025, 5, 25, 5, 0, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        
        def mock_now(tz):
            if tz == ZoneInfo("Asia/Makassar"):
                return bali_time
            elif tz == ZoneInfo("Europe/Moscow"):
                return moscow_time
            return bali_time
        
        mock_datetime_class.now.side_effect = mock_now
        
        # Mock no previous messages sent
        mock_get_meta.return_value = {}
        
        # Mock successful message sending
        mock_generate.return_value = "Test message"
        mock_send_telegram.return_value = True
        mock_add_message.return_value = True
        
        process_all_users()
        
        # Should only send to user1 (Bali user at 10:00 AM)
        # user2 (Moscow user) should not receive message as it's 5:00 AM there
        assert mock_send_telegram.call_count == 1
        assert mock_set_meta.call_count == 1
        
        # Verify the call was for user1 with morning slot
        mock_set_meta.assert_called_with("user1", "morning", "2025-05-25")


if __name__ == "__main__":
    pytest.main([__file__]) 