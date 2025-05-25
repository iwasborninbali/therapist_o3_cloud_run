#!/usr/bin/env python3
"""
Test script for proactive messages.
Sends one message immediately for testing.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.proactive_messages import send_proactive_message

if __name__ == "__main__":
    print("Sending test proactive message...")
    send_proactive_message()
    print("Done!") 