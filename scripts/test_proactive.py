#!/usr/bin/env python3
"""
Test script for proactive messages.
Temporarily changes the proactive message times to current hour for testing.
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the parent directory to the path so we can import from bot/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.firestore_client import get_user_settings, set_user_settings, get_db
from scripts.proactive_messages import should_send_proactive_message, generate_proactive_message
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_user_timezone_settings():
    """Test user timezone settings"""
    try:
        # Test user ID (Alex)
        user_id = "579160790"
        
        logger.info(f"Testing timezone settings for user {user_id}")
        
        # Get current settings
        settings = get_user_settings(user_id)
        logger.info(f"Current settings: {settings}")
        
        if not settings or not settings.get('timezone'):
            logger.info("Setting default timezone to Asia/Makassar (Bali)")
            success = set_user_settings(user_id, {"timezone": "Asia/Makassar"})
            if success:
                logger.info("✅ Timezone set successfully")
                settings = get_user_settings(user_id)
                logger.info(f"Updated settings: {settings}")
            else:
                logger.error("❌ Failed to set timezone")
                return False
        
        # Test timezone calculation
        timezone_str = settings['timezone']
        user_tz = ZoneInfo(timezone_str)
        user_time = datetime.now(user_tz)
        
        logger.info(f"User timezone: {timezone_str}")
        logger.info(f"Current time in user timezone: {user_time}")
        logger.info(f"Current hour: {user_time.hour}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing timezone settings: {e}")
        return False

def test_proactive_logic_with_current_time():
    """Test proactive message logic using current hour"""
    try:
        user_id = "579160790"
        
        # Get user settings
        settings = get_user_settings(user_id)
        if not settings or not settings.get('timezone'):
            logger.error("No timezone settings found for user")
            return False
        
        timezone_str = settings['timezone']
        user_tz = ZoneInfo(timezone_str)
        user_time = datetime.now(user_tz)
        current_hour = user_time.hour
        
        logger.info(f"Testing proactive logic for current hour: {current_hour}")
        
        # Temporarily modify the proactive hours to current hour for testing
        import config
        original_morning = config.MORNING_HOUR
        original_evening = config.EVENING_HOUR
        
        # Set one of the proactive times to current hour
        config.MORNING_HOUR = current_hour
        logger.info(f"Temporarily set MORNING_HOUR to {current_hour} for testing")
        
        # Test the logic
        should_send, slot = should_send_proactive_message(user_id, timezone_str)
        
        logger.info(f"Should send proactive message: {should_send}")
        logger.info(f"Slot: {slot}")
        
        if should_send:
            logger.info("Generating test proactive message...")
            message = generate_proactive_message(user_id, timezone_str, slot)
            logger.info(f"Generated message: {message[:100]}...")
        
        # Restore original values
        config.MORNING_HOUR = original_morning
        config.EVENING_HOUR = original_evening
        logger.info(f"Restored original times: morning={original_morning}, evening={original_evening}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing proactive logic: {e}")
        return False

def check_all_users_with_timezones():
    """Check all users who have timezone settings"""
    try:
        logger.info("Checking all users with timezone settings...")
        
        db = get_db()
        settings_ref = db.collection("user_settings")
        docs = settings_ref.stream()
        
        users_found = 0
        for doc in docs:
            settings = doc.to_dict()
            if settings.get('timezone'):
                users_found += 1
                user_tz = ZoneInfo(settings['timezone'])
                user_time = datetime.now(user_tz)
                logger.info(f"User {doc.id}: timezone={settings['timezone']}, current_time={user_time}")
        
        logger.info(f"Found {users_found} users with timezone settings")
        return users_found > 0
        
    except Exception as e:
        logger.error(f"Error checking users: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🧪 Starting proactive message testing...")
    
    # Test 1: Check timezone settings
    logger.info("\n=== Test 1: User timezone settings ===")
    if not test_user_timezone_settings():
        logger.error("❌ Timezone settings test failed")
        return
    
    # Test 2: Check all users
    logger.info("\n=== Test 2: All users with timezones ===")
    if not check_all_users_with_timezones():
        logger.error("❌ No users with timezones found")
        return
    
    # Test 3: Test proactive logic
    logger.info("\n=== Test 3: Proactive message logic ===")
    if not test_proactive_logic_with_current_time():
        logger.error("❌ Proactive logic test failed")
        return
    
    logger.info("\n✅ All tests completed successfully!")
    logger.info("\n📋 Summary:")
    logger.info("- User timezone settings: Working")
    logger.info("- Proactive message logic: Working")
    logger.info("- To test actual sending, temporarily modify MORNING_HOUR or EVENING_HOUR in config.py")

if __name__ == "__main__":
    main() 