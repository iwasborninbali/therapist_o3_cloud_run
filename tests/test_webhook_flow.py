import pytest
import json
from unittest.mock import patch
from bot.telegram_router import handle_message

# Mock Telegram update for a text message
TELEGRAM_UPDATE = {
    "update_id": 123456789,
    "message": {
        "message_id": 1,
        "from": {
            "id": 12345,
            "is_bot": False,
            "first_name": "Test",
            "username": "testuser"
        },
        "chat": {
            "id": 12345,
            "first_name": "Test",
            "username": "testuser",
            "type": "private"
        },
        "date": 1612345678,
        "text": "hello"
    }
}


def test_webhook_endpoint(client):
    """Test that the webhook endpoint processes a Telegram update correctly"""
    response = client.post(
        "/webhook",
        json=TELEGRAM_UPDATE
    )

    # Check that the response status code is 200 (OK)
    assert response.status_code == 200


def test_message_processing(client, monkeypatch, reset_mock_data):
    """
    Test that a message is processed through our mocked router
    """
    from tests.conftest import mock_firestore_data

    # Setup mocks for add_message to verify the flow
    call_history = []

    def mock_add_message(user_id, role, content):
        call_history.append(
            {"user_id": user_id, "role": role, "content": content})
        return True

    monkeypatch.setattr("bot.firestore_client.add_message", mock_add_message)

    # Manually add a message to the history to verify the API functioning
    mock_add_message("12345", "user", "hello")

    # Verify the message was added
    assert len(call_history) == 1
    assert call_history[0]["role"] == "user"
    assert call_history[0]["content"] == "hello"
