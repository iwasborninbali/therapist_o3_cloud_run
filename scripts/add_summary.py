#!/usr/bin/env python3
"""
Script to add a summary from a text file to Firebase Firestore.
Usage: python scripts/add_summary.py summary_579160790.txt
"""

import sys
import os
import re
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.firestore_client import add_summary

def extract_user_id_from_filename(filename):
    """Extract user ID from filename like summary_579160790.txt"""
    match = re.search(r'summary_(\d+)\.txt$', filename)
    if match:
        return match.group(1)
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/add_summary.py <summary_file.txt>")
        print("Example: python scripts/add_summary.py summary_579160790.txt")
        sys.exit(1)
    
    summary_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(summary_file):
        print(f"Error: File '{summary_file}' not found.")
        sys.exit(1)
    
    # Extract user ID from filename
    user_id = extract_user_id_from_filename(summary_file)
    if not user_id:
        print(f"Error: Could not extract user ID from filename '{summary_file}'")
        print("Expected format: summary_<user_id>.txt (e.g., summary_579160790.txt)")
        sys.exit(1)
    
    # Read summary content
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary_content = f.read().strip()
        
        if not summary_content:
            print(f"Error: File '{summary_file}' is empty.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error reading file '{summary_file}': {e}")
        sys.exit(1)
    
    # Add summary to Firebase
    print(f"Adding summary for user {user_id}...")
    print(f"Summary preview: {summary_content[:100]}...")
    
    try:
        success = add_summary(user_id, summary_content)
        
        if success:
            print(f"✅ Successfully added summary for user {user_id}")
            print(f"Content length: {len(summary_content)} characters")
        else:
            print(f"❌ Failed to add summary for user {user_id}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error adding summary: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 