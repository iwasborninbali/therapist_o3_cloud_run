#!/usr/bin/env python3
"""
Script to check notes in Firestore
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.firestore_client import get_notes, get_db

def check_all_notes():
    """Check all notes in the notes collection"""
    try:
        db = get_db()
        notes_ref = db.collection("notes")
        
        # Get all notes
        docs = notes_ref.order_by("timestamp", direction="DESCENDING").limit(10).stream()
        
        print("Recent notes in Firestore:")
        print("=" * 50)
        
        count = 0
        for doc in docs:
            count += 1
            note_data = doc.to_dict()
            
            print(f"Note {count}:")
            print(f"  ID: {doc.id}")
            print(f"  User ID: {note_data.get('user_id', 'N/A')}")
            print(f"  Content: {note_data.get('content', 'N/A')}")
            print(f"  Timestamp: {note_data.get('timestamp', 'N/A')}")
            print(f"  Created by: {note_data.get('created_by', 'N/A')}")
            print("-" * 30)
        
        if count == 0:
            print("No notes found in the collection.")
        else:
            print(f"Total notes shown: {count}")
            
    except Exception as e:
        print(f"Error checking notes: {e}")

if __name__ == "__main__":
    check_all_notes() 