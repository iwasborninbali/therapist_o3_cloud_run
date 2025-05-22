import logging
from datetime import datetime
from google.cloud import firestore
from config import Config
from bot.retry_utils import retry_sync

logger = logging.getLogger(__name__)

# Initialize Firestore client lazily
db = None


def get_db():
    global db
    if db is None:
        db = firestore.Client(project=Config.FIREBASE_PROJECT_ID)
    return db


@retry_sync()
def get_history(user_id):
    """
    Retrieve conversation history for a user, including Firestore doc IDs.

    Args:
        user_id (str): The user's Telegram ID

    Returns:
        list: List of message dictionaries sorted by timestamp, including 'firestore_doc_id'.
    """
    try:
        current_db = get_db()
        history_ref = current_db.collection("history").document(
            user_id).collection("messages")
        # Order by timestamp to ensure chronological order for trimming
        messages_query = history_ref.order_by(
            "timestamp", direction=firestore.Query.ASCENDING)
        message_docs = messages_query.stream()

        history = []
        for doc in message_docs:
            msg_data = doc.to_dict()
            history.append({
                "firestore_doc_id": doc.id,  # Include the document ID
                "role": msg_data["role"],
                "content": msg_data["content"],
                "timestamp": msg_data["timestamp"]
            })

        return history

    except Exception as e:
        logger.error(f"Error retrieving history for user {user_id}: {str(e)}")
        return []


@retry_sync()
def add_message(user_id, role, content):
    """
    Add a message to the user's conversation history

    Args:
        user_id (str): The user's Telegram ID
        role (str): Message role ('user' or 'assistant')
        content (str): Message content

    Returns:
        bool: Success status
    """
    try:
        timestamp = datetime.utcnow()
        current_db = get_db()
        history_ref = current_db.collection("history").document(
            user_id).collection("messages")
        history_ref.add({
            "role": role,
            "content": content,
            "timestamp": timestamp
        })

        logger.debug(f"Added {role} message to history for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error adding message for user {user_id}: {str(e)}")
        return False


@retry_sync()
def get_summaries(user_id):
    """
    Retrieve summaries for a user, including Firestore doc IDs and timestamps.

    Args:
        user_id (str): The user's Telegram ID

    Returns:
        list: List of summary dictionaries sorted by timestamp, including 'firestore_doc_id' and 'timestamp'.
    """
    try:
        current_db = get_db()
        summaries_ref = current_db.collection("summaries").document(
            user_id).collection("items")
        # Order by timestamp to ensure chronological order for FIFO management
        summary_docs_query = summaries_ref.order_by(
            "timestamp", direction=firestore.Query.ASCENDING)
        summary_docs = summary_docs_query.stream()

        summaries = []
        for doc in summary_docs:
            summary_data = doc.to_dict()
            summaries.append({
                "firestore_doc_id": doc.id,  # Include the document ID
                "content": summary_data["content"],
                "timestamp": summary_data["timestamp"]
            })

        return summaries

    except Exception as e:
        logger.error(
            f"Error retrieving summaries for user {user_id}: {str(e)}")
        return []


@retry_sync()
def add_summary(user_id, summary_content):
    """
    Add a conversation summary for a specific user.
    FIFO logic is in history_manager.py.

    Args:
        user_id (str): The user's Telegram ID
        summary_content (str): The summary text

    Returns:
        bool: Success status
    """
    try:
        timestamp = datetime.utcnow()
        current_db = get_db()
        summaries_ref = current_db.collection("summaries").document(
            user_id).collection("items")
        summaries_ref.add({
            "content": summary_content,
            "timestamp": timestamp
        })

        logger.debug(f"Added summary for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error adding summary for user {user_id}: {str(e)}")
        return False


@retry_sync()
def get_system_prompt(user_id):
    """
    Retrieve the custom system prompt for a specific user.

    Args:
        user_id (str): The user's Telegram ID

    Returns:
        str or None: The system prompt if found, None otherwise
    """
    try:
        current_db = get_db()
        prompt_ref = current_db.collection("system_prompts").document(user_id)
        prompt_doc = prompt_ref.get()

        if prompt_doc.exists:
            return prompt_doc.to_dict().get("prompt")
        return None

    except Exception as e:
        logger.error(
            f"Error retrieving system prompt for user {user_id}: {str(e)}")
        return None


@retry_sync()
def set_system_prompt(user_id, prompt):
    """
    Set the custom system prompt for a specific user

    Args:
        user_id (str): The user's Telegram ID
        prompt (str): The system prompt text

    Returns:
        bool: Success status
    """
    try:
        current_db = get_db()
        prompt_ref = current_db.collection("system_prompts").document(user_id)
        prompt_ref.set({
            "prompt": prompt,
            "updated_at": datetime.utcnow()
        })

        logger.debug(f"Set system prompt for user {user_id}")
        return True

    except Exception as e:
        logger.error(
            f"Error setting system prompt for user {user_id}: {str(e)}")
        return False
