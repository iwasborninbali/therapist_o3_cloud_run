import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from bot.main import build_app

# Set testing mode
os.environ["TESTING"] = "True"
# os.environ["FIREBASE_CRED_JSON"] = "" # Set by monkeypatch in fixture
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dummy_path" # Set by monkeypatch

# In-memory storage for mocked Firestore data
mock_firestore_data = {
    "history": {},
    "summaries": {},
    "system_prompts": {}
}


@pytest.fixture
def reset_mock_data():
    """Reset the mock data between tests"""
    mock_firestore_data["history"] = {}
    mock_firestore_data["summaries"] = {}
    mock_firestore_data["system_prompts"] = {}


@pytest.fixture
def app(monkeypatch, reset_mock_data):
    """Create a fresh FastAPI app with mocked dependencies for testing"""

    # Ensure Firebase credential env vars are set appropriately for tests
    # to prevent attempts to load real/deleted credentials.
    monkeypatch.setenv("FIREBASE_CRED_JSON", "")
    # Create a dummy credentials file for testing
    dummy_creds_path = "/tmp/dummy.json"
    Path(dummy_creds_path).write_text("{}")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", dummy_creds_path)

    # Mock google.auth.default() to prevent real credential loading
    # This needs to be active *before* firestore_client is imported by other modules.
    # The cleanest way is often to patch it where it's *used* or *looked up*,
    # but for a quick fix, patching it in 'google.auth' might work if done early enough.
    # However, conftest fixtures run *after* collection and initial imports.
    # The error indicates `google.auth.default` IS being called at import time.

    # Let's try patching where google.auth.default is called from, which is
    # google.cloud.client, or even higher up if that doesn't work.
    # For now, we will apply the patch globally to google.auth as the error originates there.

    with patch('google.auth.default', return_value=(MagicMock(), 'test-project')) as mock_auth_default:
        # Mock firestore.Client() as well, as it might do other initializations
        mock_fs_client_instance = MagicMock()
        # Make the client's project attribute accessible if needed by Config
        mock_fs_client_instance.project = "test-project"
        
        with patch('google.cloud.firestore.Client', return_value=mock_fs_client_instance) as mock_firestore_constructor:

            # Mock OpenAI API responses
            def mock_get_response(messages):
                return "STUB-REPLY"

            monkeypatch.setattr("bot.openai_client.get_response", mock_get_response)

            # Mock Firestore get_history
            def mock_get_history(user_id):
                if user_id not in mock_firestore_data["history"]:
                    mock_firestore_data["history"][user_id] = []
                return mock_firestore_data["history"][user_id]

            monkeypatch.setattr("bot.firestore_client.get_history", mock_get_history)

            # Mock Firestore add_message
            def mock_add_message(user_id, role, content):
                if user_id not in mock_firestore_data["history"]:
                    mock_firestore_data["history"][user_id] = []

                mock_firestore_data["history"][user_id].append({
                    "role": role,
                    "content": content,
                    "timestamp": "2023-01-01T00:00:00"  # Dummy timestamp
                })
                return True

            monkeypatch.setattr("bot.firestore_client.add_message", mock_add_message)

            # Mock Firestore get_summaries
            def mock_get_summaries(user_id):
                if user_id not in mock_firestore_data["summaries"]:
                    mock_firestore_data["summaries"][user_id] = []
                return mock_firestore_data["summaries"][user_id]

            monkeypatch.setattr(
                "bot.firestore_client.get_summaries", mock_get_summaries)

            # Mock Firestore get_system_prompt
            def mock_get_system_prompt(user_id):
                return mock_firestore_data["system_prompts"].get(user_id)

            monkeypatch.setattr(
                "bot.firestore_client.get_system_prompt", mock_get_system_prompt)

            # Mock Firestore set_system_prompt
            def mock_set_system_prompt(user_id, prompt):
                mock_firestore_data["system_prompts"][user_id] = prompt
                return True

            monkeypatch.setattr(
                "bot.firestore_client.set_system_prompt", mock_set_system_prompt)

            # Mock Telegram Application so it doesn't need a real token
            class MockApplication:
                def __init__(self):
                    self.update_queue = MockQueue()

            class MockQueue:
                async def put(self, item):
                    # Just store the update for verification
                    self.last_update = item

            def mock_build_telegram_app():
                return MockApplication()

            # Replace the Application.builder().token().build() chain
            monkeypatch.setattr("telegram.ext.Application.builder",
                                lambda: MockApplicationBuilder())

            class MockApplicationBuilder:
                def token(self, token):
                    return self

                def build(self):
                    return MockApplication()

    # Build the app with our monkeypatched dependencies
    return build_app()


@pytest.fixture
def client(app):
    """Create a test client using the FastAPI app"""
    return TestClient(app)
