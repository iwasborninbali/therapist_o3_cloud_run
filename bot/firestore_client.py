import logging
from datetime import datetime, timezone
from google.cloud import firestore
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError, TransportError
import ssl
import certifi
import urllib3
from config import Config
from bot.retry_utils import retry_sync, retry_async

from google.cloud.firestore_v1.base_query import FieldFilter
from typing import List, Dict, Any
import time

logger = logging.getLogger(__name__)

# Initialize Firestore client lazily
db = None

def configure_ssl_context():
    """Configure SSL context for better compatibility"""
    try:
        # Disable SSL verification warnings for urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Create SSL context with proper certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        return ssl_context
    except Exception as e:
        logger.warning(f"Could not configure SSL context: {e}")
        return None

def get_db():
    global db
    if db is None:
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Initializing Firestore client (attempt {attempt + 1}/{max_retries})")
                
                # Configure SSL context
                configure_ssl_context()
                
                # Try to get default credentials with timeout
                credentials, project = default(
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                # Initialize Firestore client with explicit project
                project_id = Config.FIREBASE_PROJECT_ID or project
                db = firestore.Client(
                    project=project_id,
                    credentials=credentials
                )
                
                # Test the connection with a simple operation
                logger.info("Testing Firestore connection...")
                test_doc = db.collection('_connection_test').document('test')
                test_doc.set({'timestamp': datetime.utcnow(), 'test': True}, merge=True)
                
                logger.info("Firestore client initialized successfully")
                return db
                
            except (DefaultCredentialsError, TransportError) as e:
                logger.error(f"Authentication error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Failed to initialize Firestore client after all retries")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error initializing Firestore: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
    
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
        history_ref = (
            current_db.collection("history").document(user_id).collection("messages")
        )
        # Order by timestamp to ensure chronological order
        messages_query = history_ref.order_by(
            "timestamp", direction=firestore.Query.ASCENDING
        )
        message_docs = messages_query.stream()

        history = []
        for doc in message_docs:
            msg_data = doc.to_dict()
            msg_data["firestore_doc_id"] = doc.id
            history.append(msg_data)

        return history

    except Exception as e:
        logger.error(f"Error retrieving history for user {user_id}: {str(e)}")
        return []


@firestore.transactional
def _add_message_transaction(transaction, user_id, message_data):
    """
    Transactional function to add a new message with a sequential ID.
    This function should not be called directly.
    """
    current_db = get_db()
    # Path for the counter, e.g., history/123/_meta/counter
    counter_ref = (
        current_db.collection("history")
        .document(user_id)
        .collection("_meta")
        .document("counter")
    )

    counter_snapshot = counter_ref.get(transaction=transaction)

    current_count = 0
    if counter_snapshot.exists:
        current_count = counter_snapshot.to_dict().get("count", 0)

    new_message_id = current_count + 1

    # The new message will have its ID as a string (e.g., "1", "2")
    new_message_ref = (
        current_db.collection("history")
        .document(user_id)
        .collection("messages")
        .document(str(new_message_id))
    )

    transaction.set(new_message_ref, message_data)
    transaction.set(counter_ref, {"count": new_message_id})
    return True





def add_message_with_timestamp(user_id, role, content, timestamp_obj):
    """
    Adds a message for a user using a transaction to ensure a sequential ID.

    Args:
        user_id (str): The user's Telegram ID.
        role (str): 'user' or 'assistant'.
        content (str): Message content.
        timestamp_obj (datetime): The timestamp for the message.

    Returns:
        bool: Success status.
    """
    try:
        current_db = get_db()
        transaction = current_db.transaction()
        message_data = {
            "role": role,
            "content": content,
            "timestamp": timestamp_obj,
        }
        _add_message_transaction(transaction, user_id, message_data)
        return True
    except Exception as e:
        logger.error(
            f"Error adding message with sequential ID for user {user_id}: {str(e)}"
        )
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
        summaries_ref = (
            current_db.collection("summaries").document(user_id).collection("items")
        )
        # Order by timestamp to ensure chronological order for FIFO management
        summary_docs_query = summaries_ref.order_by(
            "timestamp", direction=firestore.Query.ASCENDING
        )
        summary_docs = summary_docs_query.stream()

        summaries = []
        for doc in summary_docs:
            summary_data = doc.to_dict()
            summaries.append(
                {
                    "firestore_doc_id": doc.id,  # Include the document ID
                    "content": summary_data["content"],
                    "timestamp": summary_data["timestamp"],
                }
            )

        return summaries

    except Exception as e:
        logger.error(f"Error retrieving summaries for user {user_id}: {str(e)}")
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
        summaries_ref = (
            current_db.collection("summaries").document(user_id).collection("items")
        )
        summaries_ref.add({"content": summary_content, "timestamp": timestamp})

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
        logger.error(f"Error retrieving system prompt for user {user_id}: {str(e)}")
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
        prompt_ref.set({"prompt": prompt, "updated_at": datetime.utcnow()})

        logger.debug(f"Set system prompt for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error setting system prompt for user {user_id}: {str(e)}")
        return False


@retry_sync()
def get_user_settings(user_id):
    """
    Retrieve user settings.

    Args:
        user_id (str): The user's Telegram ID

    Returns:
        dict or None: User settings if found, None otherwise
    """
    try:
        current_db = get_db()
        settings_ref = current_db.collection("user_settings").document(user_id)
        settings_doc = settings_ref.get()

        if settings_doc.exists:
            return settings_doc.to_dict()
        return None

    except Exception as e:
        logger.error(f"Error retrieving user settings for user {user_id}: {str(e)}")
        return None


@retry_sync()
def set_user_settings(user_id, settings):
    """
    Set user settings.

    Args:
        user_id (str): The user's Telegram ID
        settings (dict): Settings dictionary

    Returns:
        bool: Success status
    """
    try:
        current_db = get_db()
        settings_ref = current_db.collection("user_settings").document(user_id)

        # Merge with existing settings
        existing_settings = get_user_settings(user_id) or {}
        updated_settings = {**existing_settings, **settings}
        updated_settings["updated_at"] = datetime.utcnow()

        settings_ref.set(updated_settings)

        logger.debug(f"Set user settings for user {user_id}: {settings}")
        return True

    except Exception as e:
        logger.error(f"Error setting user settings for user {user_id}: {str(e)}")
        return False





@retry_sync()
def get_last_user_message_timestamp(user_id):
    """
    Efficiently retrieve the timestamp of the last message from a user.

    Args:
        user_id (str): The user's Telegram ID

    Returns:
        datetime or None: The UTC timestamp of the last user message, or None if not found.
    """
    try:
        current_db = get_db()
        history_ref = (
            current_db.collection("history").document(user_id).collection("messages")
        )

        # Query for the last message from the user
        query = (
            history_ref.where(filter=FieldFilter("role", "==", "user"))
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(1)
        )
        docs = query.stream()

        # Since we limited to 1, there's either one or zero docs
        for doc in docs:
            return doc.to_dict().get("timestamp")

        return None  # No user messages found

    except Exception as e:
        logger.error(
            f"Error getting last user message timestamp for user {user_id}: {str(e)}"
        )
        return None


def generate_timestamp_info(user_id):
    """
    Generate simple timestamp information for the current message.

    Args:
        user_id (str): The user's Telegram ID

    Returns:
        str: Formatted timestamp information for the AI context
    """
    try:
        current_time = datetime.now(timezone.utc)
        
        # Get the timestamp of the last user message efficiently
        last_user_message_timestamp_utc = get_last_user_message_timestamp(user_id)

        time_info = f"Текущее время UTC: {current_time.strftime('%d.%m.%Y %H:%M')}"

        # Calculate time gap if we have a previous message
        if last_user_message_timestamp_utc:
            time_diff = current_time - last_user_message_timestamp_utc

            # Format time difference
            if time_diff.days > 0:
                gap_info = f" (с последнего сообщения прошло: {time_diff.days} дн. {time_diff.seconds // 3600} ч.)"
            elif time_diff.seconds >= 3600:  # More than 1 hour
                hours = time_diff.seconds // 3600
                minutes = (time_diff.seconds % 3600) // 60
                gap_info = f" (с последнего сообщения прошло: {hours} ч. {minutes} мин.)"
            elif time_diff.seconds >= 60:  # More than 1 minute
                minutes = time_diff.seconds // 60
                gap_info = f" (с последнего сообщения прошло: {minutes} мин.)"
            else:
                gap_info = " (только что писал)"

            time_info += gap_info
        else:
            time_info += " (первое сообщение пользователя)"

        return time_info

    except Exception as e:
        logger.error(f"Error generating timestamp info for user {user_id}: {str(e)}")
        return "Текущее время: ошибка получения времени"





@firestore.transactional
def _add_fact_transaction(transaction, user_id, fact_data):
    """
    Transactional function to add a new fact with a sequential ID.
    This function should not be called directly. Use `add_fact`.
    """
    current_db = get_db()
    counter_ref = (
        current_db.collection("factology")
        .document(user_id)
        .collection("_meta")
        .document("counter")
    )

    counter_snapshot = counter_ref.get(transaction=transaction)

    current_count = 0
    if counter_snapshot.exists:
        current_count = counter_snapshot.to_dict().get("count", 0)

    new_fact_id = current_count + 1

    # The new fact will have its ID as a string (e.g., "1", "2")
    new_fact_ref = (
        current_db.collection("factology")
        .document(user_id)
        .collection("entries")
        .document(str(new_fact_id))
    )

    transaction.set(new_fact_ref, fact_data)
    transaction.set(counter_ref, {"count": new_fact_id})
    return True


def add_fact(
    user_id: str,
    category: str,
    content: str,
    priority: str,
    timestamp: str,
    hot: float = 1.0,
):
    """
    Add a structured fact for a specific user with a sequential ID.
    This function wraps a Firestore transaction.
    """
    try:
        current_db = get_db()
        transaction = current_db.transaction()
        fact_data = {
            "category": category,
            "content": content,
            "priority": priority,
            "timestamp": timestamp,
            "hot": hot,
        }
        _add_fact_transaction(transaction, user_id, fact_data)
        logger.debug(f"Added fact for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error adding fact for user {user_id}: {str(e)}")
        return False


@retry_sync()
def get_facts(user_id: str, limit: int = None) -> List[Dict[str, Any]]:
    """
    Get facts for a specific user.

    Args:
        user_id: The user's Telegram ID
        limit: Maximum number of facts to retrieve

    Returns:
        List of fact dictionaries, ordered by timestamp (newest first)
    """
    try:
        current_db = get_db()
        facts_ref = (
            current_db.collection("factology").document(user_id).collection("entries")
        )

        query = facts_ref.order_by("timestamp", direction="DESCENDING")
        if limit:
            query = query.limit(limit)
        docs = query.stream()

        facts = []
        for doc in docs:
            fact_data = doc.to_dict()
            fact_data["firestore_doc_id"] = doc.id
            facts.append(fact_data)

        return facts

    except Exception as e:
        logger.error(f"Error getting facts for user {user_id}: {str(e)}")
        return []


@retry_sync()
def update_fact(user_id: str, fact_id: str, new_content: str):
    """
    Updates the content of a specific fact.

    Args:
        user_id: The user's Telegram ID
        fact_id: The Firestore document ID of the fact
        new_content: The new content to set for the fact

    Returns:
        bool: Success status
    """
    try:
        current_db = get_db()
        fact_ref = (
            current_db.collection("factology")
            .document(user_id)
            .collection("entries")
            .document(fact_id)
        )
        fact_ref.update(
            {
                "content": new_content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info(f"Updated fact {fact_id} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating fact {fact_id} for user {user_id}: {e}")
        return False


@retry_sync()
def delete_fact(user_id: str, fact_id: str):
    """
    Deletes a specific fact.

    Args:
        user_id: The user's Telegram ID
        fact_id: The Firestore document ID of the fact

    Returns:
        bool: Success status
    """
    try:
        current_db = get_db()
        fact_ref = (
            current_db.collection("factology")
            .document(user_id)
            .collection("entries")
            .document(fact_id)
        )
        fact_ref.delete()
        logger.info(f"Deleted fact {fact_id} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting fact {fact_id} for user {user_id}: {e}")
        return False


@retry_sync()
def get_facts_by_ids(user_id: str, fact_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieves specific facts for a user based on a list of document IDs.
    This implementation fetches documents one by one.

    Args:
        user_id: The user's Telegram ID.
        fact_ids: A list of Firestore document IDs to retrieve.

    Returns:
        A list of fact dictionaries.
    """
    if not fact_ids:
        return []

    try:
        current_db = get_db()
        facts_ref = (
            current_db.collection("factology").document(user_id).collection("entries")
        )

        facts = []
        for doc_id in fact_ids:
            doc_ref = facts_ref.document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                fact_data = doc.to_dict()
                fact_data["firestore_doc_id"] = doc.id
                facts.append(fact_data)

        return facts
    except Exception as e:
        logger.error(f"Error getting facts by IDs for user {user_id}: {e}")
        return []


@retry_sync()
def update_fact_fields(user_id: str, fact_id: str, updates: Dict[str, Any]):
    """
    Updates specific fields of a fact document.

    Args:
        user_id: The user's Telegram ID.
        fact_id: The Firestore document ID of the fact to update.
        updates: A dictionary of fields and their new values.
    """
    try:
        current_db = get_db()
        fact_ref = (
            current_db.collection("factology")
            .document(user_id)
            .collection("entries")
            .document(fact_id)
        )
        fact_ref.update(updates)
        return True
    except Exception as e:
        logger.error(f"Error updating fact {fact_id} for user {user_id}: {e}")
        return False


@retry_sync()
def delete_facts_by_ids(user_id: str, fact_ids: List[str]):
    """
    Deletes multiple facts for a user in a single batched write.

    Args:
        user_id (str): The user's ID.
        fact_ids (List[str]): The Firestore document IDs of the facts to delete.
    """
    if not fact_ids:
        return 0

    try:
        current_db = get_db()
        batch = current_db.batch()
        facts_ref = (
            current_db.collection("factology").document(user_id).collection("entries")
        )

        for fact_id in fact_ids:
            fact_ref = facts_ref.document(str(fact_id))  # Ensure fact_id is a string
            batch.delete(fact_ref)

        batch.commit()
        logger.info(f"Successfully deleted {len(fact_ids)} facts for user {user_id}.")
        return len(fact_ids)
    except Exception as e:
        logger.error(
            f"Error deleting facts by batch for user {user_id}: {str(e)}",
            exc_info=True,
        )
        return 0


@retry_sync()
def has_processed_update(update_id):
    """
    Check if a Telegram update has already been processed.

    Args:
        update_id (int): Telegram update ID

    Returns:
        bool: True if already processed, False otherwise
    """
    try:
        current_db = get_db()
        collection_name = Config.IDEMPOTENCY_COLLECTION
        processed_ref = current_db.collection(collection_name).document(
            str(update_id)
        )
        doc = processed_ref.get()

        return doc.exists

    except Exception as e:
        logger.error(f"Error checking processed update {update_id}: {str(e)}")
        # In case of error, assume not processed to avoid losing messages
        return False


@retry_sync()
def mark_update_processed(update_id):
    """
    Mark a Telegram update_id as processed to prevent duplicate handling.

    Args:
        update_id (int): Telegram update ID

    Returns:
        bool: Success status
    """
    try:
        current_db = get_db()
        collection_name = Config.IDEMPOTENCY_COLLECTION
        processed_ref = current_db.collection(collection_name).document(
            str(update_id)
        )

        processed_ref.set({"processed_at": datetime.utcnow(), "update_id": update_id})

        logger.debug(f"Marked update {update_id} as processed")
        return True

    except Exception as e:
        logger.error(f"Error marking update {update_id} as processed: {str(e)}")
        return False


@retry_async()
async def get_fact_by_id(user_id: str, fact_id: str):
    """
    Fetches a single fact by its document ID.
    """
    try:
        current_db = get_db()
        fact_ref = (
            current_db.collection("users")
            .document(user_id)
            .collection("facts")
            .document(fact_id)
        )
        fact_doc = await fact_ref.get()
        return fact_doc.to_dict() if fact_doc.exists else None
    except Exception as e:
        logger.error(f"Error fetching fact {fact_id} for user {user_id}: {e}")
        return None


@retry_async()
async def get_all_facts(user_id: str) -> List[dict]:
    """
    Fetches all facts for a specific user.

    Args:
        user_id: The user's Telegram ID

    Returns:
        List of fact dictionaries
    """
    try:
        current_db = get_db()
        facts_ref = (
            current_db.collection("factology").document(user_id).collection("entries")
        )
        docs = facts_ref.stream()

        facts = []
        for doc in docs:
            fact_data = doc.to_dict()
            fact_data["firestore_doc_id"] = doc.id
            facts.append(fact_data)
        return facts
    except Exception as e:
        logger.error(f"Error getting all facts for user {user_id}: {e}")
        return []


@retry_async()
async def get_facts_async(user_id: str, limit: int = None) -> List[Dict[str, Any]]:
    """
    Async version of get_facts to prevent blocking the event loop.
    
    Args:
        user_id: The user ID to fetch facts for
        limit: Optional limit on number of facts to return
        
    Returns:
        List of fact dictionaries
    """
    import asyncio
    
    # Run the sync function in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: get_facts(user_id, limit))


@retry_async()
async def get_history_async(user_id: str):
    """
    Async version of get_history to prevent blocking the event loop.
    
    Args:
        user_id: The user ID to fetch history for
        
    Returns:
        List of message dictionaries
    """
    import asyncio
    
    # Run the sync function in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: get_history(user_id))
