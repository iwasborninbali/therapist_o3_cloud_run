#!/usr/bin/env python3
"""
Test tool calling functionality specifically
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Set up environment for testing with tool calling enabled
os.environ['TESTING'] = 'True'
os.environ['ENABLE_TOOL_CALLING'] = 'true'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_tool_calling():
    """Test tool calling functionality"""
    try:
        # Import bot modules
        from bot.telegram_router import handle_message, get_tools_manager
        from bot.firestore_client import add_message, get_history, get_notes
        from telegram import Update, Message, User, Chat
        import config
        
        logger.info("=== Testing Tool Calling ===")
        logger.info(f"ENABLE_TOOL_CALLING: {config.Config.ENABLE_TOOL_CALLING}")
        
        # Test user data
        test_user_id = "tool_test_user"  # Different user for clean test
        test_chat_id = 987654321
        
        # Clear test message that explicitly requests note creation
        test_message = """
        Сегодня у меня был отличный день! Пожалуйста, создай заметку с такой информацией:
        
        - Утром сделал зарядку 30 минут
        - Позавтракал овсянкой с ягодами
        - Работал над проектом 4 часа
        - Обедал с коллегами в новом ресторане
        - Вечером читал книгу про медитацию
        
        Заметка должна называться "Хороший день 1 июня" и содержать все эти пункты. Спасибо!
        """
        
        logger.info("Creating test objects...")
        
        # Create mock Telegram objects
        user = User(
            id=test_user_id,
            first_name="TestUser",
            is_bot=False,
            username="test_user"
        )
        
        chat = Chat(
            id=test_chat_id,
            type="private"
        )
        
        message = Message(
            message_id=11111,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            text=test_message
        )
        
        update = Update(
            update_id=22222,
            message=message
        )
        
        # Create mock context
        class MockContext:
            def __init__(self):
                self.bot = MockBot()
                
        class MockBot:
            def __init__(self):
                self.sent_messages = []
                
            async def send_message(self, chat_id, text, **kwargs):
                logger.info(f"Bot response: {text[:150]}...")
                self.sent_messages.append({
                    'chat_id': chat_id,
                    'text': text,
                    'kwargs': kwargs
                })
                return MockMessage()
                
        class MockMessage:
            def __init__(self):
                self.message_id = 888
        
        context = MockContext()
        
        # Test the tools manager initialization
        logger.info("Testing ToolsManager...")
        tools_manager = get_tools_manager()
        tools = tools_manager.get_tools_for_openai()
        logger.info(f"Available tools: {len(tools)}")
        for tool in tools:
            logger.info(f"  - {tool['function']['name']}")
        
        # Process the message
        logger.info("Processing message...")
        await handle_message(update, context)
        
        # Check if note was created
        logger.info("Checking if note was created...")
        notes = get_notes(test_user_id)
        
        if notes:
            logger.info("✅ SUCCESS! Notes were created:")
            for i, note in enumerate(notes):
                logger.info(f"  Note {i+1}: {note['content'][:100]}...")
                logger.info(f"  Created by: {note.get('created_by', 'unknown')}")
        else:
            logger.error("❌ FAILED! No notes were created")
        
        # Check conversation history
        history = get_history(test_user_id)
        logger.info(f"Conversation history: {len(history)} messages")
        
        # Show bot response
        if context.bot.sent_messages:
            last_response = context.bot.sent_messages[-1]['text']
            logger.info(f"Bot's final response: {last_response[:200]}...")
        
        logger.info("=== Tool Calling Test Complete ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tool_calling()) 