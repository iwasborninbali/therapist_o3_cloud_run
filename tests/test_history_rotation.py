import pytest
from unittest.mock import patch, MagicMock, call
from bot.history_manager import manage_history, _ensure_max_summaries
from bot.summarizer import summarize  # For patching
# For a more direct patch target if needed, or use the one in history_manager
from bot.firestore_client import db
from config import Config  # To access config.HISTORY_THRESHOLD_MESSAGES etc.
from google.cloud import firestore  # For firestore.Query
import datetime

# Helper to create mock message objects as get_history might return


def create_mock_message(firestore_doc_id, role, content, timestamp_offset_seconds=0):
    return {
        "firestore_doc_id": firestore_doc_id,
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.utcnow() - datetime.timedelta(seconds=timestamp_offset_seconds)
    }

# Helper to create mock summary objects as get_summaries might return


def create_mock_summary(firestore_doc_id, content, timestamp_offset_seconds=0):
    return {
        "firestore_doc_id": firestore_doc_id,
        "content": content,
        "timestamp": datetime.datetime.utcnow() - datetime.timedelta(seconds=timestamp_offset_seconds)
    }


@pytest.fixture
def mock_config(monkeypatch):
    # Patch the actual config instance used by the history_manager module
    monkeypatch.setattr('bot.history_manager.config.HISTORY_THRESHOLD_MESSAGES', 5)
    monkeypatch.setattr('bot.history_manager.config.MESSAGES_TO_SUMMARIZE_COUNT', 2)
    monkeypatch.setattr('bot.history_manager.config.MAX_SUMMARIES', 5)
    # Return the config module/object itself if needed by tests, though direct patching is usually enough
    from config import config as actual_config_instance
    return actual_config_instance


@patch('bot.history_manager.get_history')
@patch('bot.history_manager.add_summary')
@patch('bot.history_manager.summarize')
# Patch the internal deletion helper
@patch('bot.history_manager._delete_messages_from_firestore')
# Patch this as well for focused testing
@patch('bot.history_manager._ensure_max_summaries')
def test_manage_history_triggers_summarization_and_trimming(mock_ensure_max_summaries, mock_delete_messages, mock_summarize, mock_add_summary, mock_get_history, mock_config):
    user_id = "test_user_1"
    # Create 7 messages, exceeding threshold of 5. Oldest are at the top.
    mock_history = [
        create_mock_message("msg1", "user", "Old message 1", 100),
        create_mock_message("msg2", "assistant", "Old response 1", 90),
        create_mock_message("msg3", "user", "Message 3", 80),
        create_mock_message("msg4", "assistant", "Response 4", 70),
        create_mock_message("msg5", "user", "Message 5", 60),
        create_mock_message("msg6", "assistant", "Response 6", 50),
        create_mock_message("msg7", "user", "Newest message 7", 40),
    ]
    mock_get_history.return_value = mock_history
    mock_summarize.return_value = "Test summary of old messages"

    returned_history = manage_history(user_id)

    mock_get_history.assert_called_once_with(user_id)
    # MESSAGES_TO_SUMMARIZE_COUNT is 2
    # New format includes role prefixes
    messages_expected_for_summary = [
        "Пользователь: Old message 1", 
        "Терапевт: Old response 1"
    ]
    mock_summarize.assert_called_once_with(messages_expected_for_summary)
    mock_add_summary.assert_called_once_with(
        user_id, "Test summary of old messages")
    mock_delete_messages.assert_called_once_with(
        user_id, mock_history[:2])  # Assert deletion of the 2 oldest
    mock_ensure_max_summaries.assert_called_once_with(user_id)

    # 7 original - 2 summarized = 5 remaining
    assert len(returned_history) == 5
    # Check if correct messages remain
    assert returned_history[0]["firestore_doc_id"] == "msg3"


@patch('bot.history_manager.get_history')
@patch('bot.history_manager.summarize')  # Should not be called
def test_manage_history_below_threshold(mock_summarize, mock_get_history, mock_config):
    user_id = "test_user_2"
    # Create 3 messages, below threshold of 5
    mock_history = [
        create_mock_message("m1", "user", "Hi", 30),
        create_mock_message("m2", "assistant", "Hello", 20),
        create_mock_message("m3", "user", "How are you?", 10),
    ]
    mock_get_history.return_value = mock_history

    returned_history = manage_history(user_id)

    mock_get_history.assert_called_once_with(user_id)
    mock_summarize.assert_not_called()
    assert len(returned_history) == 3
    assert returned_history == mock_history


# Patch the db instance used by _ensure_max_summaries
@patch('bot.history_manager.db')
def test_ensure_max_summaries_deletes_oldest(mock_db, mock_config):
    user_id = "test_user_3"
    # MAX_SUMMARIES is 5
    # Create 6 mock summary documents that stream() would return
    # Oldest summary (sum_old) should be deleted.
    mock_summary_doc_old = MagicMock(spec=firestore.DocumentSnapshot)
    mock_summary_doc_old.reference = MagicMock()

    mock_summary_doc_2 = MagicMock(spec=firestore.DocumentSnapshot)
    mock_summary_doc_2.reference = MagicMock()

    mock_summary_doc_3 = MagicMock(spec=firestore.DocumentSnapshot)
    mock_summary_doc_3.reference = MagicMock()

    mock_summary_doc_4 = MagicMock(spec=firestore.DocumentSnapshot)
    mock_summary_doc_4.reference = MagicMock()

    mock_summary_doc_5 = MagicMock(spec=firestore.DocumentSnapshot)
    mock_summary_doc_5.reference = MagicMock()

    mock_summary_doc_newest = MagicMock(spec=firestore.DocumentSnapshot)
    mock_summary_doc_newest.reference = MagicMock()

    # Mock the stream to return these in ASCENDING timestamp order
    mock_stream = MagicMock()
    mock_stream.stream.return_value = [
        mock_summary_doc_old, mock_summary_doc_2, mock_summary_doc_3, 
        mock_summary_doc_4, mock_summary_doc_5, mock_summary_doc_newest]

    mock_collection = MagicMock()
    # order_by returns the query obj, which then streams
    mock_collection.order_by.return_value = mock_stream

    mock_user_doc = MagicMock()
    mock_user_doc.collection.return_value = mock_collection

    mock_db.collection.return_value.document.return_value = mock_user_doc

    mock_batch = MagicMock()
    mock_db.batch.return_value = mock_batch

    _ensure_max_summaries(user_id)

    mock_db.collection.assert_called_once_with("summaries")
    mock_user_doc.collection.assert_called_once_with("items")
    mock_collection.order_by.assert_called_once_with(
        "timestamp", direction=firestore.Query.ASCENDING)
    mock_stream.stream.assert_called_once()

    # Check that batch delete was called on the oldest summary's reference
    mock_batch.delete.assert_called_once_with(mock_summary_doc_old.reference)
    mock_batch.commit.assert_called_once()


@patch('bot.history_manager.db')
@patch('bot.history_manager.get_history')  # Mock this to prevent actual calls
@patch('bot.history_manager.add_summary')  # Mock this
@patch('bot.history_manager.summarize')   # Mock this
@patch('bot.history_manager._ensure_max_summaries')  # Mock this
def test_delete_messages_from_firestore(mock_ensure, mock_summarize, mock_add_summary, mock_get_history, mock_db_in_hm, mock_config):
    user_id = "test_user_delete"
    # Setup: Create two messages to be "deleted"
    messages_to_delete = [
        create_mock_message("doc_id_1", "user", "content1"),
        create_mock_message("doc_id_2", "assistant", "content2")
    ]
    # Configure HISTORY_THRESHOLD_MESSAGES = 1, MESSAGES_TO_SUMMARIZE_COUNT = 2
    # This forces manage_history to try and delete these two messages.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mock_config, 'HISTORY_THRESHOLD_MESSAGES', 1)
    monkeypatch.setattr(mock_config, 'MESSAGES_TO_SUMMARIZE_COUNT', 2)

    mock_get_history.return_value = messages_to_delete  # These are the only messages
    mock_summarize.return_value = "summary of deleted"

    # Mock Firestore batch operations for _delete_messages_from_firestore
    mock_batch = MagicMock()
    mock_db_in_hm.batch.return_value = mock_batch

    mock_history_collection = MagicMock()
    mock_doc_ref1 = MagicMock()
    mock_doc_ref2 = MagicMock()
    # When collection("messages").document(id) is called, return the respective mock doc_refs

    def document_side_effect(doc_id):
        if doc_id == "doc_id_1":
            return mock_doc_ref1
        if doc_id == "doc_id_2":
            return mock_doc_ref2
        return MagicMock()  # default for any other unexpected calls
    mock_history_collection.document.side_effect = document_side_effect

    mock_user_history_doc = MagicMock()
    mock_user_history_doc.collection.return_value = mock_history_collection
    mock_db_in_hm.collection.return_value.document.return_value = mock_user_history_doc

    # Call manage_history, which should internally call _delete_messages_from_firestore
    # We are specifically testing the deletion part here, so the call to _delete_messages_from_firestore is *not* mocked.
    with patch('bot.history_manager._delete_messages_from_firestore',
               wraps=manage_history.__globals__['_delete_messages_from_firestore']) as wrapped_delete_spy:
        manage_history(user_id)

        # Assertions for _delete_messages_from_firestore behavior
        assert wrapped_delete_spy.called

        # Check if db.collection("history").document(user_id).collection("messages") was accessed
        mock_db_in_hm.collection.assert_any_call("history")
        mock_user_history_doc.collection.assert_called_with("messages")

        # Check if batch operations were called correctly
        mock_db_in_hm.batch.assert_called_once()
        calls_to_batch_delete = [
            call(mock_doc_ref1),
            call(mock_doc_ref2)
        ]
        mock_batch.delete.assert_has_calls(
            calls_to_batch_delete, any_order=True)
        mock_batch.commit.assert_called_once()
