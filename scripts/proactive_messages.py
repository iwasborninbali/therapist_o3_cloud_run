#!/usr/bin/env python3
"""
Universal proactive message scheduler for Telegram bot.
Checks all users individually based on their timezone settings.
Sends messages at 10:00 and 20:00 local time with deduplication.
"""

import sys
import os
import logging
import time
import requests
from datetime import datetime
from pathlib import Path
import pytz
from zoneinfo import ZoneInfo

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.firestore_client import (
    get_history, get_summaries, get_system_prompt, add_message, 
    get_user_settings, get_last_proactive_meta, set_last_proactive_meta,
    generate_timestamp_info
)
from bot.openai_client import get_response
from config import Config, DEFAULT_SYSTEM_PROMPT, MORNING_HOUR, EVENING_HOUR, PROACTIVE_CHECK_INTERVAL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proactive_messages.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_TIMEZONE = "Asia/Makassar"  # Bali timezone as default



def send_telegram_message(user_id: str, message: str) -> bool:
    """
    Send a message to user via Telegram Bot API
    
    Args:
        user_id (str): Telegram user ID
        message (str): Message text to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": user_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            logger.info(f"Successfully sent message to user {user_id}")
            return True
        else:
            logger.error(f"Telegram API error: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False


def generate_proactive_message(user_id: str, timezone_str: str, slot: str) -> str:
    """
    Generate a proactive message using AI with full context
    
    Args:
        user_id (str): User ID to generate message for
        timezone_str (str): Timezone string (e.g., 'Asia/Makassar', 'Europe/Moscow')
        slot (str): Time slot ('morning' or 'evening')
        
    Returns:
        str: Generated message text
    """
    try:
        # Get current time in user's timezone
        user_tz = ZoneInfo(timezone_str)
        user_time = datetime.now(user_tz)
        timestamp = user_time.strftime("%d.%m.%Y %H:%M")
        
        # Determine location name
        location = "Bali" if timezone_str == "Asia/Makassar" else "Moscow" if timezone_str == "Europe/Moscow" else timezone_str
        
        # Get user context
        system_prompt = get_system_prompt(user_id) or DEFAULT_SYSTEM_PROMPT
        history = get_history(user_id)
        summaries = get_summaries(user_id)
        
        # Generate timestamp information
        timestamp_info = generate_timestamp_info(user_id)
        
        # Build context for AI
        messages = []
        
        # Add system prompt
        messages.append({"role": "system", "content": system_prompt})
        
        # Add summaries as context
        for summary in summaries:
            messages.append({
                "role": "system", 
                "content": f"Previous conversation summary: {summary['content']}"
            })
        
        # Add timestamp information as system message
        messages.append({
            "role": "system", 
            "content": f"Временная информация: {timestamp_info}"
        })
        
        # Add recent history (last 10 messages)
        recent_history = history[-10:] if len(history) > 10 else history
        for msg in recent_history:
            messages.append({
                "role": msg["role"], 
                "content": msg["content"]
            })
        
        # Add the proactive prompt
        time_of_day = "утром" if slot == "morning" else "вечером"
        proactive_prompt = (
            f"Привет! Это - системное сообщение. Сейчас в {location} {timestamp} ({time_of_day}). "
            f"Напиши своему клиенту сообщение, которое считаешь нужным "
            f"(можно поинтересоваться самочувствием клиента либо продолжить диалог, "
            f"где вы оставили его в прошлый раз). Отвечай прямо от имени терапевта, "
            f"без упоминания что это системное сообщение."
        )
        
        messages.append({"role": "user", "content": proactive_prompt})
        
        # Generate response
        logger.info(f"Generating proactive {slot} message for user {user_id} in {location}")
        ai_response = get_response(messages)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error generating proactive message: {e}")
        return f"Привет! Как дела? Как себя чувствуешь {time_of_day}?"


def get_all_users_with_settings():
    """
    Get all users who have timezone settings configured.
    
    Returns:
        list: List of tuples (user_id, timezone_str)
    """
    try:
        from bot.firestore_client import get_db
        
        db = get_db()
        settings_ref = db.collection("user_settings")
        docs = settings_ref.stream()
        
        users = []
        for doc in docs:
            settings = doc.to_dict()
            if settings.get('timezone'):
                users.append((doc.id, settings['timezone']))
        
        return users
        
    except Exception as e:
        logger.error(f"Error getting users with settings: {str(e)}")
        return []


def should_send_proactive_message(user_id: str, timezone_str: str) -> tuple:
    """
    Check if we should send a proactive message to this user right now.
    
    Args:
        user_id (str): User ID
        timezone_str (str): User's timezone
        
    Returns:
        tuple: (should_send: bool, slot: str or None)
    """
    try:
        # Get current time in user's timezone
        user_tz = ZoneInfo(timezone_str)
        user_time = datetime.now(user_tz)
        current_hour = user_time.hour
        current_date = user_time.date().isoformat()
        
        # Determine if it's a proactive message time
        slot = None
        if current_hour == MORNING_HOUR:
            slot = "morning"
        elif current_hour == EVENING_HOUR:
            slot = "evening"
        else:
            return False, None
        
        # Check if we already sent a message for this slot today
        last_meta = get_last_proactive_meta(user_id)
        last_sent_date = last_meta.get(slot)
        
        if last_sent_date == current_date:
            logger.debug(f"Already sent {slot} message to user {user_id} today ({current_date})")
            return False, None
        
        logger.info(f"Should send {slot} message to user {user_id} (timezone: {timezone_str})")
        return True, slot
        
    except Exception as e:
        logger.error(f"Error checking proactive message for user {user_id}: {str(e)}")
        return False, None


def process_all_users():
    """
    Process all users and send proactive messages if needed.
    """
    try:
        users = get_all_users_with_settings()
        
        if not users:
            logger.info("No users with timezone settings found")
            return
        
        logger.info(f"Processing {len(users)} users for proactive messages")
        
        sent_count = 0
        for user_id, timezone_str in users:
            try:
                should_send, slot = should_send_proactive_message(user_id, timezone_str)
                
                if should_send and slot:
                    # Generate and send message
                    message = generate_proactive_message(user_id, timezone_str, slot)
                    success = send_telegram_message(user_id, message)
                    
                    if success:
                        # Save message to history
                        add_success = add_message(user_id, "assistant", message)
                        if add_success:
                            # Update metadata to prevent duplicates
                            current_date = datetime.now(ZoneInfo(timezone_str)).date().isoformat()
                            set_last_proactive_meta(user_id, slot, current_date)
                            
                            logger.info(f"Sent {slot} proactive message to user {user_id}: {message[:50]}...")
                            sent_count += 1
                        else:
                            logger.error(f"Failed to save proactive message to history for user {user_id}")
                    else:
                        logger.error(f"Failed to send proactive message to user {user_id}")
                
                # Small delay between users to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {str(e)}")
        
        logger.info(f"Proactive message processing completed. Sent: {sent_count}/{len(users)}")
        
    except Exception as e:
        logger.error(f"Error in process_all_users: {str(e)}")


def main():
    """Main scheduler loop"""
    logger.info("Starting universal proactive message scheduler...")
    logger.info(f"Check interval: {PROACTIVE_CHECK_INTERVAL} seconds")
    logger.info(f"Proactive times: {MORNING_HOUR}:00 and {EVENING_HOUR}:00 (local time per user)")
    
    while True:
        try:
            logger.debug("Checking all users for proactive messages...")
            process_all_users()
            
            logger.debug(f"Sleeping for {PROACTIVE_CHECK_INTERVAL} seconds...")
            time.sleep(PROACTIVE_CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main scheduler loop: {e}")
            time.sleep(PROACTIVE_CHECK_INTERVAL)


if __name__ == "__main__":
    main() 