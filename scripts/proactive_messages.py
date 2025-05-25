#!/usr/bin/env python3
"""
Proactive message sender for Telegram bot.
Sends automated messages at scheduled times (10:00 and 20:00) for specific timezone.
"""

import sys
import os
import logging
import schedule
import time
import requests
from datetime import datetime
from pathlib import Path
import pytz

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.firestore_client import get_history, get_summaries, get_system_prompt, add_message, get_users_by_timezone, generate_timestamp_info
from bot.openai_client import get_response
from config import Config

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

# Bali timezone
BALI_TZ = pytz.timezone('Asia/Makassar')  # UTC+8, same as Bali

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """SYSTEM PROMPT – AI-Therapist (universal version)

⸻

1 | Role & Purpose

You are ChatGPT (OpenAI o3) acting as a compassionate, psychologically supportive companion and micro-coach for the Client.
Your overarching goal is to help the Client strengthen self-awareness, build healthy coping skills, and feel understood and encouraged in everyday life.

⸻

2 | Core Principles

Principle	What it means in practice
Empathy	Listen deeply, validate feelings, reflect back key emotions.
Collaboration	Position the Client as expert on their life; co-create next steps.
Simplicity	Offer clear, bite-sized suggestions; avoid jargon unless invited.
Cultural Humility	Adapt language and examples to the Client's cultural, spiritual, and personal context.
Boundaries & Safety	Stay within supportive-conversation scope; encourage professional help when needed.

⸻

3 | Language & Tone
	•	Default to warm, conversational English unless the Client prefers another language—then switch seamlessly.
	•	Use short paragraphs and everyday words.
	•	Convey hope and curiosity; never shame, preach, or minimize pain.
	•	Emojis are optional and sparing—mirror the Client's style.

⸻

4 | Conversation Framework (flexible template)
	1.	Greeting & Orientation
	•	Acknowledge time/date or previous message ("Good morning! How are you feeling today?").
	2.	Check-In (1-3 quick questions)
	•	Body or stress level (0-10)
	•	Mood (0-10)
	•	Key thought, feeling, or concern
	3.	Exploration / Support
	•	Invite the Client to elaborate.
	•	Use open questions ("What's been on your mind about that?").
	•	Reflect, normalize, and empathize.
	•	Offer one micro-technique (see §5) or a guiding prompt if requested.
	4.	Action or Reflection Step
	•	Co-design a realistic next action (e.g., a 15-minute task, a grounding exercise).
	•	Confirm the Client's willingness and confidence (0-10).
	5.	Closure
	•	Summarize key insights or commitments.
	•	Offer gentle encouragement ("I'm here whenever you'd like to check in again.").

⸻

5 | Sample Micro-Techniques (choose as relevant)
	•	Breath work: box breathing (4-4-4-4) or 4-7-8 breath
	•	5-4-3-2-1 grounding (senses)
	•	Thought-parking / worry list for intrusive thoughts
	•	Gratitude jot: list two or three positives
	•	Pomodoro 25/5 for focused work or study
	•	Visualization: safe-place or future-self imagery
	•	Progressive muscle relaxation: brief body scan

⸻

6 | Boundaries & Ethical Guidelines
	•	No formal diagnosis, prescription, or legal advice.
	•	If the Client expresses intent to self-harm, harm others, or shows signs of crisis (e.g., hopelessness, active suicidal ideation, severe panic):
	1.	Acknowledge the distress with empathy.
	2.	Encourage immediate professional or emergency help (local hotline, therapist, trusted person).
	3.	Provide widely available crisis resources (e.g., worldwide emergency number 112, or "988" in the U.S.)—adapt for Client's country if known.
	•	Respect confidentiality within this chat; do not request unnecessary personal identifiers.
	•	Avoid bias and discriminatory language; treat all identities with respect.

⸻

7 | Best-Practice Behaviors
	•	Ask clarifying questions when anything is ambiguous.
	•	Mirror the Client's preferred pronouns, name, and terminology.
	•	Offer choices rather than directives; highlight the Client's agency.
	•	Celebrate small wins and normalize setbacks as part of growth.
	•	Keep responses concise (≈ 120 words) unless the Client asks for depth.
	•	Periodically invite feedback on the conversation style ("Is this pace helpful for you?").

⸻

8 | Optional Scheduled Check-Ins

If integrated with an external scheduler that pings you (e.g., at 10:00 and 20:00 local time), gracefully begin or resume the dialogue:

"Hi [Name], it's 10 AM on Tuesday. How's your body feeling on a scale of 0-10 right now?"

Adjust frequency, timing, and content of prompts to fit the Client's preferences.

⸻

9 | Primary Objectives
	1.	Reduce immediate emotional distress through validation and brief coping tools.
	2.	Support ongoing self-reflection so the Client can understand patterns and needs.
	3.	Strengthen self-efficacy by guiding the Client toward achievable micro-actions.
	4.	Promote help-seeking when challenges exceed the scope of chat-based support.

⸻

Always center the Client's experience, adapt flexibly, and remain a steady, empathic presence."""

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

def generate_proactive_message(user_id: str, timezone_str: str) -> str:
    """
    Generate a proactive message using AI with full context
    
    Args:
        user_id (str): User ID to generate message for
        timezone_str (str): Timezone string (e.g., 'Asia/Makassar', 'Europe/Moscow')
        
    Returns:
        str: Generated message text
    """
    try:
        # Get current time in user's timezone
        user_tz = pytz.timezone(timezone_str)
        user_time = datetime.now(user_tz)
        timestamp = user_time.strftime("%d.%m.%Y %H:%M")
        
        # Determine location name
        location = "Bali" if timezone_str == "Asia/Makassar" else "Moscow"
        
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
        proactive_prompt = (
            f"Привет! Это - системное сообщение. Сейчас в {location} {timestamp}. "
            f"Напиши своему клиенту сообщение, которое считаешь нужным "
            f"(можно поинтересоваться самочувствием клиента либо продолжить диалог, "
            f"где вы оставили его в прошлый раз). Отвечай прямо от имени терапевта, "
            f"без упоминания что это системное сообщение."
        )
        
        messages.append({"role": "user", "content": proactive_prompt})
        
        # Generate response
        logger.info(f"Generating proactive message for user {user_id} in {location}")
        ai_response = get_response(messages)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error generating proactive message: {e}")
        return "Привет! Как дела? Как себя чувствуешь сегодня?"

def send_proactive_messages_for_timezone(timezone_str: str) -> None:
    """Send proactive messages to all users in a specific timezone"""
    try:
        location = "Bali" if timezone_str == "Asia/Makassar" else "Moscow"
        logger.info(f"Starting proactive message generation for {location} timezone...")
        
        # Get all users with this timezone
        user_ids = get_users_by_timezone(timezone_str)
        
        if not user_ids:
            logger.info(f"No users found with timezone {timezone_str}")
            return
        
        logger.info(f"Found {len(user_ids)} users with timezone {timezone_str}")
        
        # Send message to each user
        success_count = 0
        for user_id in user_ids:
            try:
                # Generate AI message for this user
                message = generate_proactive_message(user_id, timezone_str)
                
                # Send to user via Telegram
                success = send_telegram_message(user_id, message)
                
                if success:
                    # Save message to Firestore history
                    add_success = add_message(user_id, "assistant", message)
                    if add_success:
                        logger.info(f"Proactive message sent and saved for user {user_id}: {message[:50]}...")
                        success_count += 1
                    else:
                        logger.error(f"Failed to save proactive message to history for user {user_id}")
                else:
                    logger.error(f"Failed to send proactive message to user {user_id}")
                    
                # Small delay between messages to avoid rate limiting
                time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error processing proactive message for user {user_id}: {e}")
        
        logger.info(f"Proactive messages completed for {location}. Success: {success_count}/{len(user_ids)}")
            
    except Exception as e:
        logger.error(f"Error in send_proactive_messages_for_timezone: {e}")

def send_proactive_message():
    """Send a proactive message to the hardcoded user (backward compatibility)"""
    # For backward compatibility with single user
    USER_ID = "579160790"
    BALI_TZ = "Asia/Makassar"
    
    try:
        logger.info("Starting proactive message generation for hardcoded user...")
        
        # Generate AI message
        message = generate_proactive_message(USER_ID, BALI_TZ)
        
        # Send to user via Telegram
        success = send_telegram_message(USER_ID, message)
        
        if success:
            # Save message to Firestore history
            add_success = add_message(USER_ID, "assistant", message)
            if add_success:
                logger.info(f"Proactive message sent and saved to history: {message[:50]}...")
            else:
                logger.error("Failed to save proactive message to history")
        else:
            logger.error("Failed to send proactive message")
            
    except Exception as e:
        logger.error(f"Error in send_proactive_message: {e}")

def main():
    """Main function to set up scheduling"""
    logger.info("Starting proactive message scheduler...")
    logger.info("Schedule: 10:00 and 20:00 for both Bali and Moscow timezones")
    
    # Schedule messages for Bali timezone (Asia/Makassar)
    schedule.every().day.at("10:00").do(
        lambda: send_proactive_messages_for_timezone("Asia/Makassar")
    ).tag('bali_morning')
    
    schedule.every().day.at("20:00").do(
        lambda: send_proactive_messages_for_timezone("Asia/Makassar")
    ).tag('bali_evening')
    
    # Schedule messages for Moscow timezone (Europe/Moscow)
    schedule.every().day.at("10:00").do(
        lambda: send_proactive_messages_for_timezone("Europe/Moscow")
    ).tag('moscow_morning')
    
    schedule.every().day.at("20:00").do(
        lambda: send_proactive_messages_for_timezone("Europe/Moscow")
    ).tag('moscow_evening')
    
    logger.info("Scheduler configured. Waiting for scheduled times...")
    
    # Keep the script running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main() 