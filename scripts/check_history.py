#!/usr/bin/env python3
"""
Script to check conversation history for debugging purposes.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.firestore_client import get_history

USER_ID = "579160790"

def format_timestamp(timestamp):
    """Format timestamp for display"""
    if hasattr(timestamp, 'timestamp'):
        # Firestore timestamp
        return datetime.fromtimestamp(timestamp.timestamp()).strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return str(timestamp)

def main():
    print(f"Checking conversation history for user {USER_ID}...")
    print("=" * 60)
    
    history = get_history(USER_ID)
    
    if not history:
        print("No history found!")
        return
    
    print(f"Found {len(history)} messages:")
    print()
    
    for i, msg in enumerate(history, 1):
        role = msg['role']
        content = msg['content']
        timestamp = format_timestamp(msg['timestamp'])
        
        # Limit content length for display
        if len(content) > 100:
            content_display = content[:100] + "..."
        else:
            content_display = content
        
        print(f"{i}. [{timestamp}] {role.upper()}: {content_display}")
        print()
    
    # Show last few messages in detail
    print("=" * 60)
    print("LAST 3 MESSAGES IN DETAIL:")
    print("=" * 60)
    
    for msg in history[-3:]:
        role = msg['role']
        content = msg['content']
        timestamp = format_timestamp(msg['timestamp'])
        
        print(f"[{timestamp}] {role.upper()}:")
        print(content)
        print("-" * 40)

if __name__ == "__main__":
    main() 