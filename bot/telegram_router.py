import logging
# from datetime import datetime # Unused
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
# from telegram.error import TelegramError # Unused

from bot.firestore_client import (
    get_history,
    add_message,
    get_summaries,
    get_system_prompt,
    set_system_prompt
)
from bot.openai_client import get_response
from bot.retry_utils import retry_async
from bot.history_manager import manage_history # Import the history manager

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = ("You are a helpful AI assistant that responds in a "
                           "friendly, conversational manner. You help users with "
                           "their questions and tasks while maintaining a "
                           "respectful and supportive tone.")


@retry_async()
async def safe_send_message(context, chat_id, text, **kwargs):
    """
    Send a message with retry capability for handling temporary failures

    Args:
        context: Telegram context
        chat_id: Chat ID to send the message to
        text: Message text
        **kwargs: Additional arguments for send_message

    Returns:
        The message object if successful
    """
    try:
        return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {str(e)}")
        raise  # Let the retry decorator handle retrying


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name

    welcome_message = (
        f"Hello {user_name}! 👋\n\n"
        f"I'm your AI assistant, ready to chat with you. "
        f"Just send me a message and I'll respond.\n\n"
        f"Some things I can help with:\n"
        f"• Answering questions\n"
        f"• Having conversations\n"
        f"• Providing information\n\n"
        f"Type /help to see available commands."
    )

    await safe_send_message(context, update.effective_chat.id, welcome_message)

    # Initialize with default system prompt if user doesn't have one
    if not get_system_prompt(user_id):
        set_system_prompt(user_id, DEFAULT_SYSTEM_PROMPT)
        logger.info(f"Set default system prompt for new user {user_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    help_message = (
        "Here are the available commands:\n\n"
        "/start - Start or restart the bot\n"
        "/help - Show this help message\n\n"
        "Just send me any message to chat!"
    )

    await safe_send_message(context, update.effective_chat.id, help_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages, process through OpenAI, and respond"""
    user_id = str(update.effective_user.id)
    user_message = update.message.text

    logger.info(f"Received message from user {user_id}")

    # 1. Add the user's message to history
    add_user_msg_success = add_message(user_id, "user", user_message)
    if not add_user_msg_success:
        logger.error(
            f"Failed to save user message to history for user {user_id}")
        # Attempt to notify user, but proceed if this fails
        try:
            await safe_send_message(
                context,
                update.effective_chat.id,
                ("I'm having trouble saving our conversation. "
                 "Your message might not be included in our chat history.")
            )
        except Exception as send_error:
            logger.error(
                f"Failed to send error notification to user {user_id}: {send_error}")

    # 2. Get the user's system prompt or use default
    system_prompt = get_system_prompt(user_id) or DEFAULT_SYSTEM_PROMPT

    # 3. Get the current conversation history (includes latest user message)
    # manage_history will be called *after* the AI response is also saved.
    current_history_for_openai = get_history(user_id)

    # 4. Get any existing summaries
    summary_objects = get_summaries(user_id)
    summary_contents = [s['content'] for s in summary_objects]

    # 5. Build the complete messages array for OpenAI
    messages_for_openai = []
    messages_for_openai.append({"role": "system", "content": system_prompt})
    for summary_content in summary_contents:
        messages_for_openai.append({
            "role": "system",
            "content": f"Previous conversation summary: {summary_content}"
        })
    for msg in current_history_for_openai:
        messages_for_openai.append({"role": msg["role"], "content": msg["content"]})

    # 6. Get response from OpenAI
    ai_response = get_response(messages_for_openai)

    # 7. Send the response back to the user
    await safe_send_message(context, update.effective_chat.id, ai_response)

    # 8. Store the AI response in history
    add_ai_msg_success = add_message(user_id, "assistant", ai_response)
    if not add_ai_msg_success:
        logger.error(
            f"Failed to save assistant response to history for user {user_id}")

    # 9. Manage history (trimming and summarization if needed)
    manage_history(user_id)
    logger.debug(
        f"History management processed for user {user_id} after AI response.")


def setup_handlers(application: Application) -> None:
    """Configure message handlers for the Telegram bot"""
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add handler for regular text messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram message handlers have been set up")
