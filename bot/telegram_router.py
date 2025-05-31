import logging
# from datetime import datetime # Unused
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
# from telegram.error import TelegramError  # Unused

from bot.firestore_client import (
    get_history,
    add_message,
    get_summaries,
    get_system_prompt,
    set_system_prompt,
    get_user_settings,
    set_user_settings,
    generate_timestamp_info,
    get_notes,
    has_processed_update,
    mark_update_processed
)
from bot.openai_client import get_response
from bot.retry_utils import retry_async
from bot.history_manager import manage_history  # Import the history manager
from bot.tools_manager import ToolsManager
from config import DEFAULT_SYSTEM_PROMPT, Config

logger = logging.getLogger(__name__)

# Initialize tools manager lazily
_tools_manager = None


def get_tools_manager():
    """Get ToolsManager instance, creating it if needed"""
    global _tools_manager
    if _tools_manager is None:
        try:
            # Pass the firestore_client module directly
            import bot.firestore_client as firestore_client
            _tools_manager = ToolsManager(firestore_client)
            logger.info("ToolsManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ToolsManager: {e}")
            raise
    return _tools_manager


async def handle_update(update_data: dict, telegram_bot: Application) -> None:
    """Handle Telegram update with idempotency check"""
    try:
        # Create Update object from JSON data
        update = Update.de_json(update_data, telegram_bot.bot)
        
        # Get update_id for idempotency
        update_id = update.update_id
        
        # Check if we've already processed this update
        if has_processed_update(update_id):
            logger.info(f"Update {update_id} already processed, skipping")
            return
            
        # Mark update as processed before handling to prevent duplicates
        mark_update_processed(update_id)
        logger.info(f"Processing update {update_id}")
        
        # Process the update
        await telegram_bot.process_update(update)
        
    except Exception as e:
        logger.error(f"Error processing update in background: {e}")


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

    # Check if user already has timezone set
    user_settings = get_user_settings(user_id)
    
    if user_settings and user_settings.get('timezone'):
        # User already has timezone set
        timezone = user_settings['timezone']
        timezone_name = "Bali" if timezone == "Asia/Makassar" else "Moscow"
        
        welcome_message = (
            f"Hello {user_name}! 👋\n\n"
            f"Welcome back! Your timezone is set to {timezone_name}.\n\n"
            f"I'm your AI therapist, ready to support you with compassionate guidance. "
            f"Just send me a message and I'll respond.\n\n"
            f"You'll receive proactive check-ins at 10:00 AM and 8:00 PM in your timezone.\n\n"
            f"Type /help to see available commands or /timezone to change your timezone."
        )
        
        await safe_send_message(context, update.effective_chat.id, welcome_message)
    else:
        # New user - show timezone selection
        welcome_message = (
            f"Hello {user_name}! 👋\n\n"
            f"Welcome to your AI Therapist! I'm here to provide compassionate support "
            f"and guidance whenever you need it.\n\n"
            f"First, please select your timezone so I can send you proactive check-ins "
            f"at the right times (10:00 AM and 8:00 PM):"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏝️ Bali (Asia/Makassar)", callback_data="timezone_bali")],
            [InlineKeyboardButton("🏙️ Moscow/SPB (Europe/Moscow)", callback_data="timezone_moscow")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_send_message(
            context, 
            update.effective_chat.id, 
            welcome_message, 
            reply_markup=reply_markup
        )

    # Initialize with default system prompt if user doesn't have one
    if not get_system_prompt(user_id):
        set_system_prompt(user_id, DEFAULT_SYSTEM_PROMPT)
        logger.info(f"Set default system prompt for new user {user_id}")


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /timezone command to change timezone."""
    user_id = str(update.effective_user.id)
    
    current_settings = get_user_settings(user_id)
    current_timezone = "Not set"
    if current_settings and current_settings.get('timezone'):
        tz = current_settings['timezone']
        current_timezone = "Bali" if tz == "Asia/Makassar" else "Moscow"
    
    message = (
        f"Current timezone: {current_timezone}\n\n"
        f"Select your timezone for proactive check-ins:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🏝️ Bali (Asia/Makassar)", callback_data="timezone_bali")],
        [InlineKeyboardButton("🏙️ Moscow/SPB (Europe/Moscow)", callback_data="timezone_moscow")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_send_message(
        context, 
        update.effective_chat.id, 
        message, 
        reply_markup=reply_markup
    )


async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle timezone selection callbacks."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    await query.answer()
    
    if query.data == "timezone_bali":
        timezone = "Asia/Makassar"
        timezone_name = "Bali"
    elif query.data == "timezone_moscow":
        timezone = "Europe/Moscow"
        timezone_name = "Moscow"
    else:
        await query.edit_message_text("Invalid selection. Please try again.")
        return
    
    # Save timezone setting
    success = set_user_settings(user_id, {"timezone": timezone})
    
    if success:
        message = (
            f"✅ Timezone set to {timezone_name}!\n\n"
            f"You'll receive proactive check-ins at:\n"
            f"• 10:00 AM {timezone_name} time\n"
            f"• 8:00 PM {timezone_name} time\n\n"
            f"I'm ready to support you! Send me a message anytime. 💚"
        )
        logger.info(f"Set timezone {timezone} for user {user_id}")
    else:
        message = "Sorry, there was an error saving your timezone. Please try again."
        logger.error(f"Failed to save timezone for user {user_id}")
    
    await query.edit_message_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    help_message = (
        "Here are the available commands:\n\n"
        "/start - Start or restart the bot\n"
        "/help - Show this help message\n"
        "/timezone - Change your timezone settings\n\n"
        "I'm your AI therapist, here to provide compassionate support. "
        "Just send me any message to start our conversation! 💚"
    )

    await safe_send_message(context, update.effective_chat.id, help_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages, process through OpenAI, and respond"""
    user_id = str(update.effective_user.id)
    user_message = update.message.text

    logger.info(f"Received message from user {user_id}")

    # Check if user has timezone set, if not - prompt to set it
    user_settings = get_user_settings(user_id)
    if not user_settings or not user_settings.get('timezone'):
        logger.info(f"User {user_id} doesn't have timezone set, prompting to set it")
        
        timezone_prompt = (
            "Hi! I notice you haven't set your timezone yet. "
            "This helps me send you proactive check-ins at the right times (10:00 AM and 8:00 PM).\n\n"
            "Please select your timezone:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🏝️ Bali (Asia/Makassar)", callback_data="timezone_bali")],
            [InlineKeyboardButton("🏙️ Moscow/SPB (Europe/Moscow)", callback_data="timezone_moscow")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_send_message(
            context, 
            update.effective_chat.id, 
            timezone_prompt, 
            reply_markup=reply_markup
        )
        
        # Still process the message normally after showing timezone prompt
    
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
    logger.info(f"📚 Loaded {len(summary_contents)} summaries for user {user_id} context")

    # 5. Get therapist notes for context
    notes_objects = get_notes(user_id)  # All notes, no limit
    notes_contents = [f"Note ({n['timestamp']}): {n['content']}" for n in notes_objects]
    logger.info(f"📝 Loaded {len(notes_contents)} notes for user {user_id} context")

    # 6. Generate timestamp information for context
    timestamp_info = generate_timestamp_info(user_id)

    # 7. Build the complete messages array for OpenAI
    messages_for_openai = []
    messages_for_openai.append({"role": "system", "content": system_prompt})
    for i, summary_content in enumerate(summary_contents):
        messages_for_openai.append({
            "role": "system",
            "content": f"Previous conversation summary: {summary_content}"
        })
        logger.debug(f"📚 Added summary {i+1} to context for user {user_id}: {summary_content[:100]}...")
    
    # Add therapist notes as system context
    if notes_contents:
        notes_context = "Previous therapist notes:\n" + "\n".join(notes_contents)
        messages_for_openai.append({
            "role": "system",
            "content": notes_context
        })
        logger.debug(f"📝 Added {len(notes_contents)} notes to context for user {user_id}")
    
    # Add timestamp information as system message
    messages_for_openai.append({
        "role": "system", 
        "content": f"Временная информация: {timestamp_info}"
    })
    for msg in current_history_for_openai:
        messages_for_openai.append({"role": msg["role"], "content": msg["content"]})

    # 8. Get response from OpenAI with tool calling support
    tools_manager = get_tools_manager() if Config.ENABLE_TOOL_CALLING else None
    ai_response = get_response(messages_for_openai, tools_manager=tools_manager, user_id=user_id)

    # 8. Send the response back to the user
    await safe_send_message(context, update.effective_chat.id, ai_response)

    # 9. Store the AI response in history
    add_ai_msg_success = add_message(user_id, "assistant", ai_response)
    if not add_ai_msg_success:
        logger.error(
            f"Failed to save assistant response to history for user {user_id}")

    # 10. Manage history (trimming and summarization if needed)
    manage_history(user_id)
    logger.debug(
        f"History management processed for user {user_id} after AI response.")


def setup_handlers(application: Application) -> None:
    """Configure message handlers for the Telegram bot"""
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("timezone", timezone_command))
    
    # Add callback query handler for timezone selection
    application.add_handler(CallbackQueryHandler(timezone_callback, pattern="^timezone_"))

    # Add handler for regular text messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram message handlers have been set up")
