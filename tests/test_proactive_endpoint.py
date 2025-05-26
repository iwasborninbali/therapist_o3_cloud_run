"""
Tests for proactive message HTTP endpoint.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from bot.main import build_app


@pytest.fixture
def client():
    """Create test client for the FastAPI app"""
    app = build_app()
    return TestClient(app)


@pytest.fixture
def mock_send_for_timezone_slot():
    """Mock the send_for_timezone_slot function"""
    with patch('bot.main.send_for_timezone_slot') as mock:
        yield mock


class TestProactiveEndpoint:
    """Test cases for the proactive message endpoint"""

    def test_send_proactive_success(self, client, mock_send_for_timezone_slot):
        """Test successful proactive message sending"""
        # Mock successful response
        mock_send_for_timezone_slot.return_value = {"sent": 3, "skipped": 1}
        
        # Make request
        response = client.post("/admin/send-proactive?timezone=Asia/Makassar&slot=morning")
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"sent": 3, "skipped": 1}
        
        # Verify function was called correctly
        mock_send_for_timezone_slot.assert_called_once_with("Asia/Makassar", "morning")

    def test_send_proactive_url_encoded_timezone(self, client, mock_send_for_timezone_slot):
        """Test with URL-encoded timezone parameter"""
        # Mock successful response
        mock_send_for_timezone_slot.return_value = {"sent": 2, "skipped": 0}
        
        # Make request with URL-encoded timezone
        response = client.post("/admin/send-proactive?timezone=Asia%2FMakassar&slot=evening")
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"sent": 2, "skipped": 0}
        
        # Verify function was called with decoded timezone
        mock_send_for_timezone_slot.assert_called_once_with("Asia/Makassar", "evening")

    def test_send_proactive_moscow_timezone(self, client, mock_send_for_timezone_slot):
        """Test with Moscow timezone"""
        # Mock successful response
        mock_send_for_timezone_slot.return_value = {"sent": 1, "skipped": 2}
        
        # Make request
        response = client.post("/admin/send-proactive?timezone=Europe/Moscow&slot=morning")
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"sent": 1, "skipped": 2}
        
        # Verify function was called correctly
        mock_send_for_timezone_slot.assert_called_once_with("Europe/Moscow", "morning")

    def test_send_proactive_invalid_slot(self, client, mock_send_for_timezone_slot):
        """Test with invalid slot parameter"""
        # Make request with invalid slot
        response = client.post("/admin/send-proactive?timezone=Asia/Makassar&slot=afternoon")
        
        # Verify error response
        assert response.status_code == 400
        assert "Invalid slot" in response.json()["detail"]
        
        # Verify function was not called
        mock_send_for_timezone_slot.assert_not_called()

    def test_send_proactive_invalid_timezone(self, client, mock_send_for_timezone_slot):
        """Test with invalid timezone parameter"""
        # Make request with invalid timezone
        response = client.post("/admin/send-proactive?timezone=America/New_York&slot=morning")
        
        # Verify error response
        assert response.status_code == 400
        assert "Invalid timezone" in response.json()["detail"]
        
        # Verify function was not called
        mock_send_for_timezone_slot.assert_not_called()

    def test_send_proactive_function_exception(self, client, mock_send_for_timezone_slot):
        """Test when send_for_timezone_slot raises an exception"""
        # Mock function to raise exception
        mock_send_for_timezone_slot.side_effect = Exception("Database error")
        
        # Make request
        response = client.post("/admin/send-proactive?timezone=Asia/Makassar&slot=morning")
        
        # Verify error response
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
        
        # Verify function was called
        mock_send_for_timezone_slot.assert_called_once_with("Asia/Makassar", "morning")

    def test_send_proactive_no_users(self, client, mock_send_for_timezone_slot):
        """Test when no users are found for timezone"""
        # Mock response with no users
        mock_send_for_timezone_slot.return_value = {"sent": 0, "skipped": 0}
        
        # Make request
        response = client.post("/admin/send-proactive?timezone=Europe/Moscow&slot=evening")
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"sent": 0, "skipped": 0}
        
        # Verify function was called correctly
        mock_send_for_timezone_slot.assert_called_once_with("Europe/Moscow", "evening")

    @pytest.mark.parametrize("timezone,slot", [
        ("Asia/Makassar", "morning"),
        ("Asia/Makassar", "evening"),
        ("Europe/Moscow", "morning"),
        ("Europe/Moscow", "evening"),
    ])
    def test_send_proactive_all_valid_combinations(self, client, mock_send_for_timezone_slot, timezone, slot):
        """Test all valid timezone/slot combinations"""
        # Mock successful response
        mock_send_for_timezone_slot.return_value = {"sent": 1, "skipped": 0}
        
        # Make request
        response = client.post(f"/admin/send-proactive?timezone={timezone}&slot={slot}")
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"sent": 1, "skipped": 0}
        
        # Verify function was called correctly
        mock_send_for_timezone_slot.assert_called_once_with(timezone, slot) 
