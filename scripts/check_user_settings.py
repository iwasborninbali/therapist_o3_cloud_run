#!/usr/bin/env python3
"""
Script to check and manage user settings.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.firestore_client import get_user_settings, set_user_settings

USER_ID = "579160790"

def main():
    print(f"Checking user settings for user {USER_ID}...")
    print("=" * 50)
    
    # Get current settings
    settings = get_user_settings(USER_ID)
    
    if settings:
        print("Current settings:")
        for key, value in settings.items():
            print(f"  {key}: {value}")
    else:
        print("No settings found for this user.")
        
        # Set default timezone for Bali
        print("\nSetting default timezone to Bali...")
        success = set_user_settings(USER_ID, {"timezone": "Asia/Makassar"})
        
        if success:
            print("✅ Timezone set to Bali (Asia/Makassar)")
            
            # Verify
            updated_settings = get_user_settings(USER_ID)
            print("\nUpdated settings:")
            for key, value in updated_settings.items():
                print(f"  {key}: {value}")
        else:
            print("❌ Failed to set timezone")

if __name__ == "__main__":
    main() 