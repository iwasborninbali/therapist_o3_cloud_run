"""
Proactive message delivery module for HTTP endpoint approach.
Handles sending proactive messages to users based on timezone and time slot.
"""

import logging
import requests
import concurrent.futures
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Tuple, Dict

from .firestore_client import (
    get_history, get_summaries, get_system_prompt, add_message,
    get_last_proactive_meta, set_last_proactive_meta,
    generate_timestamp_info, get_db
)
from .openai_client import get_response
from config import Config, DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def get_users_by_timezone(timezone_str: str) -> List[str]:
    """
    Get all user IDs who have the specified timezone setting.
    
    Args:
        timezone_str (str): Timezone string (e.g., 'Asia/Makassar', 'Europe/Moscow')
        
    Returns:
        List[str]: List of user IDs with this timezone
    """
    try:
        db = get_db()
        settings_ref = db.collection("user_settings")
        
        # Query users with specific timezone
        query = settings_ref.where("timezone", "==", timezone_str)
        docs = query.stream()
        
        user_ids = [doc.id for doc in docs]
        logger.info(f"Found {len(user_ids)} users with timezone {timezone_str}")
        return user_ids
        
    except Exception as e:
        logger.error(f"Error getting users by timezone {timezone_str}: {str(e)}")
        return []


def should_send_proactive_message(user_id: str, timezone_str: str, slot: str) -> bool:
    """
    Check if we should send a proactive message to this user for the given slot.
    
    Args:
        user_id (str): User ID
        timezone_str (str): User's timezone
        slot (str): Time slot ('morning' or 'evening')
        
    Returns:
        bool: True if message should be sent, False if already sent today
    """
    try:
        # Get current date in user's timezone
        user_tz = ZoneInfo(timezone_str)
        current_date = datetime.now(user_tz).date().isoformat()
        
        # Check if we already sent a message for this slot today
        last_meta = get_last_proactive_meta(user_id)
        last_sent_date = last_meta.get(slot)
        
        if last_sent_date == current_date:
            logger.debug(f"Already sent {slot} message to user {user_id} today ({current_date})")
            return False
        
        logger.info(f"Should send {slot} message to user {user_id} (timezone: {timezone_str})")
        return True
        
    except Exception as e:
        logger.error(f"Error checking proactive message for user {user_id}: {str(e)}")
        return False


def generate_proactive_message(user_id: str, timezone_str: str, slot: str) -> str:
    """
    Generate a proactive message using AI with full context.
    
    Args:
        user_id (str): User ID to generate message for
        timezone_str (str): Timezone string
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
        time_of_day = "утром" if slot == "morning" else "вечером"
        return f"Привет! Как дела? Как себя чувствуешь {time_of_day}?"


def send_telegram_message(user_id: str, message: str) -> bool:
    """
    Send a message to user via Telegram Bot API.
    
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


def process_single_user(user_id: str, timezone_str: str, slot: str) -> bool:
    """
    Process a single user for proactive message.
    
    Args:
        user_id (str): User ID
        timezone_str (str): User's timezone
        slot (str): Time slot ('morning' or 'evening')
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        if not should_send_proactive_message(user_id, timezone_str, slot):
            return False
        
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
                return True
            else:
                logger.error(f"Failed to save proactive message to history for user {user_id}")
        else:
            logger.error(f"Failed to send proactive message to user {user_id}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing user {user_id}: {str(e)}")
        return False


def send_for_timezone_slot(timezone_str: str, slot: str) -> Dict[str, int]:
    """
    Send proactive messages to all users in a specific timezone and time slot.
    
    Args:
        timezone_str (str): Timezone string (e.g., 'Asia/Makassar', 'Europe/Moscow')
        slot (str): Time slot ('morning' or 'evening')
        
    Returns:
        Dict[str, int]: Results with 'sent' and 'skipped' counts
    """
    try:
        # Validate inputs
        if slot not in ['morning', 'evening']:
            raise ValueError(f"Invalid slot: {slot}. Must be 'morning' or 'evening'")
        
        # Get users for this timezone
        user_ids = get_users_by_timezone(timezone_str)
        
        if not user_ids:
            logger.info(f"No users found for timezone {timezone_str}")
            return {"sent": 0, "skipped": 0}
        
        logger.info(f"Processing {len(user_ids)} users for {slot} messages in {timezone_str} (parallel)")
        
        # Process users in parallel
        sent_count = 0
        skipped_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(user_ids), 10)) as executor:
            # Submit all user processing tasks
            future_to_user = {
                executor.submit(process_single_user, user_id, timezone_str, slot): user_id
                for user_id in user_ids
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    success = future.result()
                    if success:
                        sent_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    logger.error(f"Error in parallel processing for user {user_id}: {str(e)}")
                    skipped_count += 1
        
        result = {"sent": sent_count, "skipped": skipped_count}
        logger.info(f"Proactive {slot} processing completed for {timezone_str}. Result: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in send_for_timezone_slot: {str(e)}")
        return {"sent": 0, "skipped": 0} 
