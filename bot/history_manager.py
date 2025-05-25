import logging
# Import get_db function instead of db directly
from bot.firestore_client import get_history, add_summary, get_db
from bot.summarizer import summarize
from config import config
# Add this if not already present at the top, ensuring it's available for _ensure_max_summaries
from google.cloud import firestore

logger = logging.getLogger(__name__)


def manage_history(user_id: str):
    """
    Manages user conversation history.
    If history exceeds threshold (50 messages = 25 user+assistant pairs), 
    it trims the oldest 30 messages (15 pairs), generates a summary, and stores it.

    Args:
        user_id (str): The ID of the user.

    Returns:
        list: The potentially trimmed conversation history.
    """
    current_history = get_history(user_id)
    history_len = len(current_history)

    # Count user and assistant message pairs
    user_messages = [msg for msg in current_history if msg['role'] == 'user']
    assistant_messages = [msg for msg in current_history if msg['role'] == 'assistant']
    
    # Consider complete pairs only (minimum of user and assistant counts)
    complete_pairs = min(len(user_messages), len(assistant_messages))
    total_messages_in_pairs = complete_pairs * 2

    logger.debug(
        f"User {user_id} has {history_len} total messages "
        f"({len(user_messages)} user, {len(assistant_messages)} assistant), "
        f"{complete_pairs} complete pairs ({total_messages_in_pairs} messages in pairs)"
    )

    # Trigger summarization when we have 25 or more complete pairs (50+ messages)
    if total_messages_in_pairs >= config.HISTORY_THRESHOLD_MESSAGES:
        log_msg = (
            f"History for user {user_id} ({complete_pairs} pairs = {total_messages_in_pairs} messages) "
            f"exceeds threshold ({config.HISTORY_THRESHOLD_MESSAGES} messages = "
            f"{config.HISTORY_THRESHOLD_MESSAGES // 2} pairs). Trimming."
        )
        logger.info(log_msg)

        # Take the oldest 30 messages (15 pairs) for summarization
        messages_to_summarize_count = config.MESSAGES_TO_SUMMARIZE_COUNT
        if messages_to_summarize_count > history_len:
            messages_to_summarize_count = history_len

        # Ensure we're taking complete pairs for summarization
        # Take messages in chronological order (oldest first)
        messages_for_summary_objects = current_history[:messages_to_summarize_count]
        remaining_history = current_history[messages_to_summarize_count:]

        # Extract content for summarization, formatted with role information
        message_contents_for_summary = []
        for msg in messages_for_summary_objects:
            role_label = "Пользователь" if msg['role'] == 'user' else "Терапевт"
            message_contents_for_summary.append(f"{role_label}: {msg['content']}")

        logger.info(f"📝 Generating summary for user {user_id} from {len(message_contents_for_summary)} message contents")
        summary_text = summarize(message_contents_for_summary)
        logger.info(f"📝 Summary generated for user {user_id}: {summary_text[:100]}..." if len(summary_text) > 100 else f"📝 Summary generated for user {user_id}: {summary_text}")

        logger.info(f"💾 Storing summary for user {user_id}")
        add_summary(user_id, summary_text)
        
        logger.info(f"🧹 Ensuring max summaries limit for user {user_id}")
        _ensure_max_summaries(user_id)

        # Delete old messages from Firestore
        logger.info(f"🗑️ Deleting {len(messages_for_summary_objects)} old messages from Firestore for user {user_id}")
        _delete_messages_from_firestore(user_id, messages_for_summary_objects)

        logger.info(
            f"History for user {user_id} trimmed. "
            f"Summarized {len(messages_for_summary_objects)} oldest messages. "
            f"Remaining history length: {len(remaining_history)}. Summary stored."
        )
        return remaining_history
    else:
        threshold_pairs = config.HISTORY_THRESHOLD_MESSAGES // 2
        logger.debug(
            f"History for user {user_id} ({complete_pairs} pairs) is within "
            f"threshold ({threshold_pairs} pairs). No action."
        )
        return current_history


def _delete_messages_from_firestore(user_id: str, messages_to_delete: list):
    """
    Deletes messages from a user's history in Firestore.
    Assumes `messages_to_delete` contains objects with 'firestore_doc_id'.
    """
    if not messages_to_delete:
        logger.info(f"🗑️ No messages to delete for user {user_id}")
        return

    try:
        db = get_db()  # Get the initialized db instance
        history_collection_ref = db.collection("history").document(
            user_id).collection("messages")
        batch = db.batch()
        deleted_count = 0
        missing_id_count = 0
        
        logger.info(f"🗑️ Processing {len(messages_to_delete)} messages for deletion for user {user_id}")
        
        for i, msg_data in enumerate(messages_to_delete):
            if "firestore_doc_id" in msg_data:
                doc_id = msg_data["firestore_doc_id"]
                doc_ref = history_collection_ref.document(doc_id)
                batch.delete(doc_ref)
                deleted_count += 1
                logger.debug(f"🗑️ Queued for deletion: message {i+1} with ID {doc_id}")
            else:
                missing_id_count += 1
                logger.warning(
                    f"🚨 Message {i+1} for user {user_id} missing 'firestore_doc_id'. "
                    f"Content: {msg_data.get('content', 'N/A')[:50]}... "
                    f"Role: {msg_data.get('role', 'N/A')}"
                )

        if deleted_count > 0:
            logger.info(f"🗑️ Committing deletion of {deleted_count} messages for user {user_id}")
            batch.commit()
            logger.info(f"✅ Successfully deleted {deleted_count} old messages for user {user_id}")
        
        if missing_id_count > 0:
            logger.warning(f"⚠️ {missing_id_count} messages could not be deleted due to missing firestore_doc_id")
        
        if deleted_count == 0:
            logger.error(f"❌ No messages were deleted for user {user_id} during trim - check ID retrieval")

    except Exception as e:
        logger.error(f"❌ Error deleting old messages for user {user_id}: {str(e)}")


def _ensure_max_summaries(user_id: str):
    """
    Ensures stored summaries for a user don't exceed MAX_SUMMARIES (FIFO).
    """
    try:
        db = get_db()  # Get the initialized db instance
        summaries_collection_ref = db.collection("summaries").document(
            user_id).collection("items")
        all_summaries_query = summaries_collection_ref.order_by(
            "timestamp", direction=firestore.Query.ASCENDING)
        summary_docs = list(all_summaries_query.stream())  # Get all to count

        if len(summary_docs) > config.MAX_SUMMARIES:
            num_to_delete = len(summary_docs) - config.MAX_SUMMARIES
            # Oldest ones are at the beginning due to ASCENDING order
            summaries_to_delete = summary_docs[:num_to_delete]

            batch = db.batch()
            for summary_doc_to_delete in summaries_to_delete:
                batch.delete(summary_doc_to_delete.reference)
            batch.commit()
            logger.info(
                f"Deleted {num_to_delete} oldest summaries for user {user_id} "
                f"to maintain max of {config.MAX_SUMMARIES}."
            )

    except Exception as e:
        logger.error(
            f"Error ensuring max summaries for user {user_id}: {str(e)}"
        )
