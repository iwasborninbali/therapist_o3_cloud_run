#!/usr/bin/env python3
"""
Simple script to check notes in Firestore
"""

import os
from google.cloud import firestore

def check_notes():
    """Check notes in Firestore"""
    try:
        # Initialize Firestore client directly
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json"
        db = firestore.Client(project="ales-f75a1")
        
        # Get notes collection - check all users
        notes_collection = db.collection("notes")
        user_docs = notes_collection.stream()
        
        all_notes = []
        for user_doc in user_docs:
            user_id = user_doc.id
            items_ref = notes_collection.document(user_id).collection("items")
            note_docs = items_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
            
            for note_doc in note_docs:
                note_data = note_doc.to_dict()
                note_data["user_id"] = user_id
                note_data["doc_id"] = note_doc.id
                all_notes.append(note_data)
        
        # Sort all notes by timestamp
        all_notes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        docs = all_notes[:10]  # Take top 10
        
        print("Recent notes in Firestore:")
        print("=" * 50)
        
        count = 0
        for note_data in docs:
            count += 1
            
            print(f"Note {count}:")
            print(f"  ID: {note_data.get('doc_id', 'N/A')}")
            print(f"  User ID: {note_data.get('user_id', 'N/A')}")
            print(f"  Content: {note_data.get('content', 'N/A')}")
            print(f"  Timestamp: {note_data.get('timestamp', 'N/A')}")
            print(f"  Created by: {note_data.get('created_by', 'N/A')}")
            print("-" * 30)
        
        if count == 0:
            print("No notes found in the collection.")
        else:
            print(f"Total notes shown: {count}")
            
        # Also check if collection exists
        collections = db.collections()
        collection_names = [col.id for col in collections]
        print(f"\nAvailable collections: {collection_names}")
        
        if "notes" in collection_names:
            print("✅ 'notes' collection exists")
        else:
            print("❌ 'notes' collection does not exist")
            
    except Exception as e:
        print(f"Error checking notes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_notes() 