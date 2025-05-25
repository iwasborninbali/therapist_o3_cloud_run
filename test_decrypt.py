#!/usr/bin/env python3
"""
Test script to verify Firebase credentials and access
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env for testing
load_dotenv('.env')

# Import config to setup Firebase credentials
from config import config

def test_firebase_access():
    """Test Firebase access with credentials"""
    print("Testing Firebase access...")
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Initialize Firebase if not already done
        if not firebase_admin._apps:
            # The config.py should have already set GOOGLE_APPLICATION_CREDENTIALS
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        db = firestore.client()
        
        # Try to access users collection
        users_ref = db.collection('users')
        docs = users_ref.limit(1).stream()
        
        user_count = 0
        for doc in docs:
            user_count += 1
            print(f"✅ SUCCESS: Found user document: {doc.id}")
            break
        
        if user_count == 0:
            print("ℹ️  No users found in database (this is normal for new setup)")
        
        print("✅ SUCCESS: Firebase connection working!")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Firebase access error: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Firebase Credentials Test")
    print("=" * 40)
    
    # Check environment variables
    firebase_cred_json = os.getenv("FIREBASE_CRED_JSON")
    if firebase_cred_json:
        print("✅ FIREBASE_CRED_JSON found in environment")
        print(f"Length: {len(firebase_cred_json)} characters")
    else:
        print("❌ FIREBASE_CRED_JSON not found")
        sys.exit(1)
    
    # Test Firebase access
    firebase_ok = test_firebase_access()
    
    if firebase_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Firebase credentials loaded")
        print("✅ Firebase access works")
        print("\nReady for deployment!")
    else:
        print("\n❌ TESTS FAILED")
        sys.exit(1) 