#!/usr/bin/env python3
"""
Simple script to check and set user timezone settings.
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the parent directory to the path so we can import from bot/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.firestore_client import get_user_settings, set_user_settings

def main():
    user_id = "579160790"  # Alex's user ID
    
    print(f"Checking timezone settings for user {user_id}...")
    
    # Get current settings
    settings = get_user_settings(user_id)
    print(f"Current settings: {settings}")
    
    if not settings or not settings.get('timezone'):
        print("No timezone found. Setting to Asia/Makassar (Bali)...")
        success = set_user_settings(user_id, {"timezone": "Asia/Makassar"})
        if success:
            print("✅ Timezone set successfully")
            settings = get_user_settings(user_id)
            print(f"Updated settings: {settings}")
        else:
            print("❌ Failed to set timezone")
            return
    
    # Show current time in user's timezone
    timezone_str = settings['timezone']
    user_tz = ZoneInfo(timezone_str)
    user_time = datetime.now(user_tz)
    
    print(f"\nUser timezone: {timezone_str}")
    print(f"Current time in user timezone: {user_time}")
    print(f"Current hour: {user_time.hour}")
    print(f"Current date: {user_time.date().isoformat()}")

if __name__ == "__main__":
    main() 