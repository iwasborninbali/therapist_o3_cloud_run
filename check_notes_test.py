#!/usr/bin/env python3
"""
Check the notes created during test and view full bot response
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from bot.firestore_client import get_notes, get_history

def check_test_results():
    test_user_id = "123456789"
    
    print("=== Checking Test Results ===")
    
    # Check conversation history
    print("\n📚 CONVERSATION HISTORY:")
    history = get_history(test_user_id)
    for i, msg in enumerate(history):
        role_icon = "👤" if msg['role'] == 'user' else "🤖"
        print(f"\n{i+1}. {role_icon} {msg['role'].upper()}:")
        print(f"   {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")
    
    # Check notes
    print("\n📝 NOTES CREATED:")
    notes = get_notes(test_user_id)
    if notes:
        for i, note in enumerate(notes):
            print(f"\n{i+1}. Note (created by {note.get('created_by', 'unknown')}):")
            print(f"   Timestamp: {note.get('timestamp', 'unknown')}")
            print(f"   Content: {note['content'][:300]}{'...' if len(note['content']) > 300 else ''}")
    else:
        print("   No notes found")
    
    # Show full bot response
    if history:
        last_assistant_msg = None
        for msg in reversed(history):
            if msg['role'] == 'assistant':
                last_assistant_msg = msg
                break
        
        if last_assistant_msg:
            print(f"\n🤖 FULL BOT RESPONSE:")
            print(f"{'='*50}")
            print(last_assistant_msg['content'])
            print(f"{'='*50}")

if __name__ == "__main__":
    check_test_results() 