import logging
import asyncio
import json
import os
import time

# from datetime import datetime # Unused
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)

# from telegram.error import TelegramError  # Unused

from bot.firestore_client import (
    get_history,
    get_history_async,
    add_message_with_timestamp,
    get_system_prompt,
    set_system_prompt,
    get_facts,
    get_facts_async,
    get_user_settings,
    has_processed_update,
    mark_update_processed,
)
from bot.openai_client import (
    get_o4_mini_summary,
    get_o3_response_tool,
    ask_o3_with_image,
)
from bot.retry_utils import retry_async
from bot.prompt_builder import build_o4_mini_payload, build_payload
from bot.factology_manager import FactologyManager
from bot.schemas import AnalysisResult, ResponseMode
from bot.speech_to_text import transcribe_audio
from bot.text_to_speech import text_to_speech
from io import BytesIO

logger = logging.getLogger(__name__)

# Initialize factology manager lazily
_factology_manager = None

# Buffering of multi-part user messages
MESSAGE_BUFFER_TIMEOUT = 5  # seconds to wait for additional parts
MESSAGE_BUFFER_MAX_LENGTH = 40000  # limit to avoid huge buffers
_message_buffers = {}


def get_factology_manager():
    """Get FactologyManager instance, creating it if needed"""
    global _factology_manager
    if _factology_manager is None:
        try:
            import bot.firestore_client as firestore_client

            _factology_manager = FactologyManager(firestore_client)
            logger.info("FactologyManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FactologyManager: {e}")
            raise
    return _factology_manager


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


async def keep_typing(context, chat_id, interval=5):
    """
    Continuously send typing action every interval seconds
    Used during long operations like OpenAI requests
    """
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        # This is expected when the task is cancelled
        pass
    except Exception as e:
        logger.debug(f"Typing task error (not critical): {e}")


def split_long_message(text, max_length=4000):
    """
    Split a long message into chunks that fit Telegram's limits

    Args:
        text (str): The message text to split
        max_length (int): Maximum length per chunk (default 4000 to be safe)

    Returns:
        list: List of message chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Find a good breaking point (end of sentence, then word)
        chunk = remaining[:max_length]

        # Try to break at sentence end
        sentence_end = max(chunk.rfind("."), chunk.rfind("!"), chunk.rfind("?"))
        if (
            sentence_end > max_length * 0.5
        ):  # If we found a sentence end in the latter half
            break_point = sentence_end + 1
        else:
            # Try to break at word boundary
            break_point = chunk.rfind(" ")
            if break_point == -1:  # No space found, force break
                break_point = max_length

        chunks.append(remaining[:break_point].strip())
        remaining = remaining[break_point:].strip()

    return chunks


@retry_async()
async def safe_send_message(context, chat_id, text, **kwargs):
    """
    Send a message with retry capability and automatic splitting for long messages

    Args:
        context: Telegram context
        chat_id: Chat ID to send the message to
        text: Message text
        **kwargs: Additional arguments for send_message

    Returns:
        The last message object if successful
    """
    try:
        # Split message if it's too long
        chunks = split_long_message(text)

        last_message = None
        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk uses original kwargs
                last_message = await context.bot.send_message(
                    chat_id=chat_id, text=chunk, **kwargs
                )
            else:
                # Subsequent chunks without special formatting
                last_message = await context.bot.send_message(
                    chat_id=chat_id, text=chunk
                )

        return last_message
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {str(e)}")
        raise  # Let the retry decorator handle retrying


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name

    welcome_message = (
        f"Hello {user_name}! 👋\n\n"
        f"Welcome to your AI Therapist! I'm here to provide compassionate support "
        f"and guidance whenever you need it.\n\n"
        f"Just send me a message and I'll respond with care and understanding.\n\n"
        f"Type /help to see available commands."
    )

    await safe_send_message(context, update.effective_chat.id, welcome_message)

    # Initialize with default system prompt if user doesn't have one
    from config import DEFAULT_SYSTEM_PROMPT
    if not get_system_prompt(user_id):
        set_system_prompt(user_id, DEFAULT_SYSTEM_PROMPT)
        logger.info(f"Set default system prompt for new user {user_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    help_message = (
        "Here are the available commands:\n\n"
        "/start - Start or restart the bot\n"
        "/help  - Show this help message\n"
        "/voice - always respond with voice\n"
        "/text  - always respond with text\n"
        "/auto  - let the model decide\n\n"
        "I'm your AI therapist, here to provide compassionate support. "
        "Just send me any message to start our conversation! \ud83d\udc9a\n"
        "You can also send voice messages, and I'll transcribe them for you.\n"
        "You can send photos too — I can analyze them."
    )

    await safe_send_message(context, update.effective_chat.id, help_message)


async def _set_reply_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str | None):
    set_user_settings(str(update.effective_user.id), {"reply_mode": mode})
    await safe_send_message(
        context,
        update.effective_chat.id,
        f"\u0420\u0435\u0436\u0438\u043c \u043e\u0442\u0432\u0435\u0442\u0430: {mode or 'auto'}",
    )


async def _process_user_message(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: str, user_message: str, image_data: bytes = None
) -> None:
    """Core logic for processing a user message and responding."""
    start_time = time.time()
    logger.info(f"[TIMING] Message handling started for user {user_id}")

    # Start a background task to send "typing..." action
    typing_task = asyncio.create_task(keep_typing(context, chat_id))

    try:
        # --- o4-mini Pre-processing Step ---
        o4_summary = None
        try:
            # 1. Fetch all necessary data: facts and recent history (ASYNC!)
            db_start = time.time()
            facts = await get_facts_async(user_id)
            history = await get_history_async(user_id)
            recent_history = history[-6:]
            logger.info(f"[TIMING] DB operations took {time.time() - db_start:.2f}s")

            # 2. Build the payload for o4-mini
            payload_start = time.time()
            o4_payload = build_o4_mini_payload(user_message, facts, recent_history)
            logger.info(f"[TIMING] Payload building took {time.time() - payload_start:.2f}s")

            # 3. Call o4-mini to get summary and perform fact management
            if o4_payload:
                o4_start = time.time()
                logger.info("[TIMING] Starting o4-mini request...")
                summary_result, _ = await get_o4_mini_summary(o4_payload)
                logger.info(f"[TIMING] o4-mini request took {time.time() - o4_start:.2f}s")

                # 4. Use the summary and manage facts
                if summary_result:
                    o4_summary = summary_result.summary
                    if summary_result.references:
                        o4_summary += f"\n(References: {summary_result.references})"
                    logger.info(
                        f"Successfully got summary from o4-mini for user {user_id}"
                    )

                    # Perform fact management (updates, merges, pruning)
                    fact_manager = get_factology_manager()
                    if summary_result.references:
                        fact_manager.update_hot_scores(
                            user_id, summary_result.references
                        )
                    if summary_result.reorganisation:
                        fact_manager.merge_facts(user_id, summary_result.reorganisation)
                    fact_manager.prune_facts(user_id)

        except Exception as e:
            logger.error(
                f"Could not get summary from o4-mini or manage facts: {e}",
                exc_info=True,
            )

        # --- o3 Therapist Model Step ---
        last_6_messages = history[-6:]
        payload = build_payload(user_id, user_message, last_6_messages, o4_summary)

        # Call the API with function calling enabled
        message = await get_o3_response_tool(payload, image_data)
        bot_response_text = ""
        analysis = None

        # Check for tool calls and process them
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            if tool_call.function.name == "process_user_message":
                try:
                    args = json.loads(tool_call.function.arguments)
                    analysis = AnalysisResult.model_validate(args)

                    bot_response_text = analysis.response

                    if analysis.factology:
                        fact_manager = get_factology_manager()
                        saved_count = 0
                        for fact in analysis.factology:
                            try:
                                fact_manager.save_new_fact(
                                    user_id=user_id,
                                    fact_content=fact.content,
                                    category=fact.category,
                                    priority=fact.priority,
                                )
                                saved_count += 1
                            except Exception as e:
                                logger.error(
                                    f"Failed to save fact: {fact.content}",
                                    exc_info=True,
                                )

                        if saved_count > 0:
                            logger.info(
                                f"Saved {saved_count} new fact(s) for user {user_id}."
                            )

                except Exception:
                    logger.error("Error processing tool call", exc_info=True)
                    bot_response_text = "I had a little trouble processing that, sorry."
            else:
                bot_response_text = "I received a tool call I don't know how to handle."

        elif message.content:
            bot_response_text = message.content
        else:
            bot_response_text = "I'm not sure how to respond to that."

        user_settings = get_user_settings(user_id) or {}
        user_pref = user_settings.get("reply_mode")
        model_mode = analysis.response_mode.value if analysis and analysis.response_mode else None
        mode = user_pref or model_mode or "text"

        if mode == "voice" and os.getenv("DISABLE_TTS") != "True":
            try:
                audio_bytes = await text_to_speech(bot_response_text)
                if len(audio_bytes) > 50 * 1024 * 1024:
                    logger.warning("Voice message too large (>50MB). Sending text instead.")
                    await safe_send_message(context, chat_id, bot_response_text)
                else:
                    voice_file = BytesIO(audio_bytes)
                    voice_file.name = "response.ogg"
                    await context.bot.send_voice(chat_id=chat_id, voice=voice_file)
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
                await safe_send_message(context, chat_id, bot_response_text)
                await safe_send_message(context, chat_id, "\u26a0\ufe0f Voice response unavailable.")
        else:
            await safe_send_message(context, chat_id, bot_response_text)

        # Save the interaction to history
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc)
        # If image was provided, note it in the user message
        user_message_for_history = f"{user_message} (изображение)" if image_data else user_message
        add_message_with_timestamp(user_id, "user", user_message_for_history, timestamp)
        add_message_with_timestamp(user_id, "assistant", bot_response_text, timestamp)

    except Exception as e:
        logger.error(f"Error handling message for user {user_id}: {e}", exc_info=True)
        error_message = (
            "I'm sorry, I've encountered a problem and can't respond right now. "
            "Please try again later."
        )
        await safe_send_message(context, chat_id, error_message)

    finally:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages with temporary buffering of multi-part inputs."""
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    text = update.message.text

    now = time.monotonic()

    buffer = _message_buffers.get(user_id)
    if buffer:
        # Append new text and reset timer
        buffer["text"] += "\n" + text
        buffer["timestamp"] = now
        if len(buffer["text"]) > MESSAGE_BUFFER_MAX_LENGTH:
            await safe_send_message(
                context,
                chat_id,
                "🚧 Сообщение слишком длинное, сократите его.",
            )
            if not buffer["task"].done():
                buffer["task"].cancel()
                try:
                    await buffer["task"]
                except asyncio.CancelledError:
                    pass
            _message_buffers.pop(user_id, None)
            return
        if not buffer["task"].done():
            buffer["task"].cancel()
            try:
                await buffer["task"]
            except asyncio.CancelledError:
                pass
        buffer["task"] = asyncio.create_task(_delayed_process(user_id, context))
    else:
        _message_buffers[user_id] = {
            "text": text,
            "timestamp": now,
            "chat_id": chat_id,
            "task": asyncio.create_task(_delayed_process(user_id, context)),
        }


async def _delayed_process(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Wait for MESSAGE_BUFFER_TIMEOUT, then process the buffered text."""
    try:
        await asyncio.sleep(MESSAGE_BUFFER_TIMEOUT)
    except asyncio.CancelledError:
        return

    buffer = _message_buffers.get(user_id)
    if not buffer:
        return

    if time.monotonic() - buffer["timestamp"] >= MESSAGE_BUFFER_TIMEOUT:
        text = buffer["text"].strip()
        chat_id = buffer["chat_id"]
        _message_buffers.pop(user_id, None)
        await _process_user_message(context, chat_id, user_id, text)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages by transcribing them and delegating to handle_message."""
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    voice = update.message.voice or update.message.audio

    # Allow disabling STT for CI or maintenance
    if os.getenv("DISABLE_STT") == "True":
        await safe_send_message(context, chat_id, "\u26a0\ufe0f \u0420\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u0432\u0430\u043d\u0438\u0435 \u0440\u0435\u0447\u0438 \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043e\u0442\u043a\u043b\u044e\u0447\u0435\u043d\u043e.")
        return

    logger.info(
        f"Voice message from {user_id}, file_id={voice.file_unique_id} duration={voice.duration}s"
    )

    if voice.duration and voice.duration > 120:
        await safe_send_message(
            context,
            chat_id,
            "Voice message is too long. Please keep it under 2 minutes.",
        )
        return

    if voice.file_size and voice.file_size > 5_000_000:
        await safe_send_message(
            context,
            chat_id,
            "Audio file is too large. Please keep it under 5MB.",
        )
        return

    try:
        tfile = await voice.get_file()
        audio_bytes = bytes(await tfile.download_as_bytearray())
        text = await transcribe_audio(audio_bytes)
    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        await safe_send_message(context, chat_id, "Sorry, I couldn't process that audio message.")
        return

    if not text:
        await safe_send_message(context, chat_id, "I couldn't understand the audio message.")
        return

    # Reuse the buffered message processing logic with the transcribed text
    # Create a fake update object for voice message buffering
    now = time.monotonic()
    buffer = _message_buffers.get(user_id)
    if buffer:
        # Append new text and reset timer
        buffer["text"] += "\n" + text
        buffer["timestamp"] = now
        if len(buffer["text"]) > MESSAGE_BUFFER_MAX_LENGTH:
            await safe_send_message(
                context,
                chat_id,
                "🚧 Сообщение слишком длинное, сократите его.",
            )
            if not buffer["task"].done():
                buffer["task"].cancel()
                try:
                    await buffer["task"]
                except asyncio.CancelledError:
                    pass
            _message_buffers.pop(user_id, None)
            return
        if not buffer["task"].done():
            buffer["task"].cancel()
            try:
                await buffer["task"]
            except asyncio.CancelledError:
                pass
        buffer["task"] = asyncio.create_task(_delayed_process(user_id, context))
    else:
        _message_buffers[user_id] = {
            "text": text,
            "timestamp": now,
            "chat_id": chat_id,
            "task": asyncio.create_task(_delayed_process(user_id, context)),
        }


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photo messages by using the full therapist pipeline."""
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)

    try:
        photo = update.message.photo[-1]
        tfile = await photo.get_file()
        img_bytes = bytes(await tfile.download_as_bytearray())
    except Exception as e:
        logger.error(f"Failed to download photo: {e}")
        await safe_send_message(context, chat_id, "Sorry, I couldn't process that image.")
        return

    if len(img_bytes) > 20 * 1024 * 1024:
        await safe_send_message(
            context,
            chat_id,
            "Image is too large. Please keep it under 20MB.",
        )
        return

    caption_or_default = update.message.caption or "Опиши изображение"

    # Use the full therapist pipeline with image support
    await _process_user_message(context, chat_id, user_id, caption_or_default, img_bytes)


def setup_handlers(application: Application) -> None:
    """Configure message handlers for the Telegram bot"""
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("voice", lambda u, c: _set_reply_mode(u, c, "voice")))
    application.add_handler(CommandHandler("text", lambda u, c: _set_reply_mode(u, c, "text")))
    application.add_handler(CommandHandler("auto", lambda u, c: _set_reply_mode(u, c, None)))

    # Add handler for regular text messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Add handler for voice messages
    application.add_handler(
        MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message)
    )

    # Add handler for photo messages
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Telegram message handlers have been set up")
