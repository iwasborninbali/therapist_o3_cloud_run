# Task: History Rotation & Summarization

## Objective
Implement automatic conversation history rotation and summarization to manage context length and provide users with concise summaries of past interactions.

## Files to Modify/Create
- `bot/history_manager.py` (new) - Manages conversation history, triggers summarization, and stores summaries.
- `bot/telegram_router.py` - Integrate `history_manager` after saving new messages.
- `bot/summarizer.py` - Adapt `summarize` function signature to accept a list of strings and return a string.
- `bot/firestore_client.py` - Modified `get_history` to return Firestore document IDs, and `get_summaries` to return full summary objects.
- `tests/test_history_rotation.py` (new) - Pytest tests for history rotation and summarization logic.
- `config.py` - Added configuration for history thresholds and summary counts.
- `project_manifest.json` - Updated with new `bot.history_manager.py` module.
- `README.md` - Added "Conversation Length Management" section and updated feature list.

## Implementation Details

### `bot/history_manager.py`
- **History Trimming:** Counts messages; if > threshold, identifies oldest messages for summarization and removes them from active history object (deletion from Firestore is separate step).
- **Summarization Trigger:** Calls `summarizer.summarize()` with content of messages identified for summarization.
- **Summary Storage:** Adds new summary via `firestore_client.add_summary()`. Calls `_ensure_max_summaries` to maintain max number of summaries (FIFO) by deleting oldest from Firestore.
- **Message Deletion:** Calls `_delete_messages_from_firestore` to remove summarized messages from Firestore using their document IDs.
- **Return Value:** Returns the potentially trimmed list of active messages (objects).

### `bot/telegram_router.py`
- Invokes `manage_history()` after saving both user message and assistant's response to Firestore.
- Correctly passes extracted summary contents to OpenAI prompt.

### `bot/summarizer.py`
- Modified `summarize(message_contents: list[str]) -> str` signature. Stub logic updated to reflect new input type.

### `bot/firestore_client.py`
- `get_history` now returns message objects including `firestore_doc_id`.
- `get_summaries` now returns full summary objects (including `firestore_doc_id` and `timestamp`) instead of just content strings.

### `tests/test_history_rotation.py`
- Comprehensive tests for `manage_history`, `_ensure_max_summaries`, and Firestore deletion logic using mocks.
- Verified correct config patching for tests.

### `project_manifest.json` & `README.md`
- Updated as per requirements.

## Configuration
- `HISTORY_THRESHOLD_MESSAGES` (default: 30)
- `MESSAGES_TO_SUMMARIZE_COUNT` (default: 20)
- `MAX_SUMMARIES` (default: 3)

## Status: done 