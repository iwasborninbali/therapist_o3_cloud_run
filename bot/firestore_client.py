import logging
from datetime import datetime
from google.cloud import firestore
from config import Config
from bot.retry_utils import retry_sync
import pytz

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


@retry_sync()
def get_user_settings(user_id):
    """
    Retrieve user settings including timezone preference.

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
        logger.error(
            f"Error retrieving user settings for user {user_id}: {str(e)}")
        return None


@retry_sync()
def set_user_settings(user_id, settings):
    """
    Set user settings including timezone preference.

    Args:
        user_id (str): The user's Telegram ID
        settings (dict): Settings dictionary (e.g., {'timezone': 'Asia/Makassar'})

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
        logger.error(
            f"Error setting user settings for user {user_id}: {str(e)}")
        return False


@retry_sync()
def get_users_by_timezone(timezone):
    """
    Get all user IDs that have the specified timezone setting.
    
    Args:
        timezone (str): Timezone string (e.g., 'Asia/Makassar', 'Europe/Moscow')
        
    Returns:
        list: List of user IDs
    """
    try:
        current_db = get_db()
        settings_ref = current_db.collection("user_settings")
        query = settings_ref.where("timezone", "==", timezone)
        docs = query.stream()
        
        user_ids = []
        for doc in docs:
            user_ids.append(doc.id)
            
        return user_ids
        
    except Exception as e:
        logger.error(f"Error getting users by timezone {timezone}: {str(e)}")
        return []


def generate_timestamp_info(user_id):
    """
    Generate timestamp information for the current message, including:
    - Current time in user's timezone
    - Time gap since last user message
    
    Args:
        user_id (str): The user's Telegram ID
        
    Returns:
        str: Formatted timestamp information for the AI context
    """
    try:
        # Get user's timezone
        user_settings = get_user_settings(user_id)
        if not user_settings or not user_settings.get('timezone'):
            return "Текущее время: не задан часовой пояс пользователя"
        
        timezone_str = user_settings['timezone']
        user_tz = pytz.timezone(timezone_str)
        current_time = datetime.now(user_tz)
        
        # Get conversation history to find last user message
        history = get_history(user_id)
        
        # Find last user message (excluding the current one which hasn't been saved yet)
        last_user_message_time = None
        for msg in reversed(history):
            if msg['role'] == 'user':
                # Convert UTC timestamp to user's timezone
                if isinstance(msg['timestamp'], datetime):
                    utc_time = msg['timestamp'].replace(tzinfo=pytz.UTC)
                    last_user_message_time = utc_time.astimezone(user_tz)
                    break
        
        # Format current time
        location_name = "Bali" if timezone_str == "Asia/Makassar" else "Moscow" if timezone_str == "Europe/Moscow" else timezone_str
        time_info = f"Сейчас в {location_name}: {current_time.strftime('%d.%m.%Y %H:%M (%A)')}"
        
        # Calculate time gap if we have a previous message
        if last_user_message_time:
            time_diff = current_time - last_user_message_time
            
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


@retry_sync()
def get_last_proactive_meta(user_id):
    """
    Get the last proactive message metadata for a user.
    
    Args:
        user_id (str): The user's Telegram ID
        
    Returns:
        dict: Metadata with 'morning' and 'evening' last sent dates, or empty dict
    """
    try:
        current_db = get_db()
        meta_ref = current_db.collection("proactive_meta").document(user_id)
        meta_doc = meta_ref.get()
        
        if meta_doc.exists:
            return meta_doc.to_dict()
        return {}
        
    except Exception as e:
        logger.error(f"Error getting proactive meta for user {user_id}: {str(e)}")
        return {}


@retry_sync()
def set_last_proactive_meta(user_id, slot, date_iso):
    """
    Set the last proactive message date for a specific slot.
    
    Args:
        user_id (str): The user's Telegram ID
        slot (str): Either 'morning' or 'evening'
        date_iso (str): Date in ISO format (YYYY-MM-DD)
        
    Returns:
        bool: Success status
    """
    try:
        current_db = get_db()
        meta_ref = current_db.collection("proactive_meta").document(user_id)
        
        # Get existing metadata or create new
        existing_meta = get_last_proactive_meta(user_id) or {}
        
        # Update the specific slot
        existing_meta[slot] = date_iso
        existing_meta["updated_at"] = datetime.utcnow()
        
        meta_ref.set(existing_meta)
        
        logger.debug(f"Set proactive meta for user {user_id}, slot {slot}: {date_iso}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting proactive meta for user {user_id}: {str(e)}")
        return False


@retry_sync()
def add_note(user_id, content, timestamp, created_by="therapist_ai"):
    """
    Add a therapist note for a specific user.
    
    Args:
        user_id (str): The user's Telegram ID
        content (str): Note content
        timestamp (str): ISO timestamp when note was created
        created_by (str): Who created the note (default: "therapist_ai")
        
    Returns:
        bool: Success status
    """
    try:
        current_db = get_db()
        notes_ref = current_db.collection("notes").document(user_id).collection("items")
        
        note_data = {
            "content": content,
            "timestamp": timestamp,
            "created_by": created_by
        }
        
        # Add note with auto-generated document ID
        notes_ref.add(note_data)
        
        logger.info(f"Added note for user {user_id}: {content[:50]}...")
        return True
        
    except Exception as e:
        logger.error(f"Error adding note for user {user_id}: {str(e)}")
        return False


@retry_sync()
def get_notes(user_id, limit=None):
    """
    Get therapist notes for a specific user.
    
    Args:
        user_id (str): The user's Telegram ID
        limit (int): Maximum number of notes to retrieve
        
    Returns:
        list: List of note dictionaries, ordered by timestamp (newest first)
    """
    try:
        current_db = get_db()
        notes_ref = current_db.collection("notes").document(user_id).collection("items")
        
        # Query notes for this user, ordered by timestamp descending
        query = notes_ref.order_by("timestamp", direction="DESCENDING")
        if limit:
            query = query.limit(limit)
        docs = query.stream()
        
        notes = []
        for doc in docs:
            note_data = doc.to_dict()
            note_data["firestore_doc_id"] = doc.id  # Include document ID
            notes.append(note_data)
            
        return notes
        
    except Exception as e:
        logger.error(f"Error getting notes for user {user_id}: {str(e)}")
        return []


@retry_sync()
def has_processed_update(update_id):
    """
    Check if we've already processed this Telegram update_id.
    
    Args:
        update_id (int): Telegram update ID
        
    Returns:
        bool: True if already processed, False otherwise
    """
    try:
        current_db = get_db()
        processed_ref = current_db.collection("processed_updates").document(str(update_id))
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
        processed_ref = current_db.collection("processed_updates").document(str(update_id))
        
        processed_ref.set({
            "processed_at": datetime.utcnow(),
            "update_id": update_id
        })
        
        logger.debug(f"Marked update {update_id} as processed")
        return True
        
    except Exception as e:
        logger.error(f"Error marking update {update_id} as processed: {str(e)}")
        return False
