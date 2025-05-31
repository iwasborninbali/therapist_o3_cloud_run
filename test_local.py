#!/usr/bin/env python3
"""
Local test script for therapist bot
Tests the full pipeline: message processing, AI response, tool calling
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Set up environment for testing
os.environ['TESTING'] = 'True'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_message_processing():
    """Test the full message processing pipeline"""
    try:
        # Import bot modules
        from bot.telegram_router import handle_message, get_tools_manager
        from bot.firestore_client import add_message, get_history
        from telegram import Update, Message, User, Chat
        from telegram.ext import ContextTypes
        import config
        
        logger.info("=== Starting Local Bot Test ===")
        
        # Test user data
        test_user_id = "123456789"  # Test user ID
        test_chat_id = 123456789
        
        # Create a long test message about Alexey's day
        test_message = """
        Привет! Хочу рассказать тебе о моём сегодняшнем дне, это был удивительный день! 

        Утром я пошёл в спа-центр "Relax Zone" - это было потрясающе! Сначала я сделал 90-минутный тайский массаж, массажист работал очень профессионально, проработал все зажимы в спине и шее. Потом я посетил сауну с эвкалиптовым паром - там я расслабился и медитировал около 20 минут. После этого был контрастный душ и джакузи с морской солью. В конце процедур я выпил травяной чай с имбирем и лимоном. Чувствую себя совершенно обновлённым!

        После спа я поехал домой и решил приготовить особенный ужин для семьи. Готовил азиатское блюдо - тайскую лапшу Пад Тай с креветками. Сначала я замариновал креветки в соевом соусе с чесноком и имбирем на 30 минут. Потом обжарил их до золотистого цвета. Лапшу варил точно по инструкции - 3 минуты в кипящей воде. Соус делал из соевого соуса, рыбного соуса, тамаринда, пальмового сахара и сока лайма. Добавил ростки фасоли, зеленый лук, арахис и листья кинзы. Получилось очень ароматно и вкусно! Вся семья была в восторге.

        Вечером мы всей семьей смотрели фильм "Интерстеллар" - я уже видел его раньше, но каждый раз открываю что-то новое. Обсуждали с детьми концепцию времени и пространства. Дочка задавала много вопросов о черных дырах и путешествиях во времени.

        Перед сном читал книгу "Атомные привычки" Джеймса Клира - очень интересные идеи о том, как маленькие изменения могут привести к большим результатам.

        Пожалуйста, создай заметку об этом дне, чтобы я мог вспомнить все эти прекрасные моменты! И напиши, какие выводы и рекомендации ты можешь дать на основе моего рассказа.
        """
        
        logger.info(f"Test message length: {len(test_message)} characters")
        logger.info("Creating mock Telegram objects...")
        
        # Create mock Telegram objects
        user = User(
            id=test_user_id,
            first_name="Алексей",
            is_bot=False,
            username="test_alexey"
        )
        
        chat = Chat(
            id=test_chat_id,
            type="private"
        )
        
        message = Message(
            message_id=12345,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            text=test_message
        )
        
        update = Update(
            update_id=67890,
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
                logger.info(f"Bot would send to {chat_id}: {text[:100]}...")
                self.sent_messages.append({
                    'chat_id': chat_id,
                    'text': text,
                    'kwargs': kwargs
                })
                return MockMessage()
                
        class MockMessage:
            def __init__(self):
                self.message_id = 999
        
        context = MockContext()
        
        # Test the tools manager initialization
        logger.info("Testing ToolsManager initialization...")
        tools_manager = get_tools_manager()
        logger.info(f"ToolsManager initialized: {tools_manager}")
        
        # Manually add the message to history (simulating what would happen)
        logger.info("Adding message to Firestore...")
        add_message(test_user_id, "user", test_message)
        
        # Test message handling
        logger.info("Processing message through handler...")
        await handle_message(update, context)
        
        # Check what messages were "sent"
        logger.info(f"Bot sent {len(context.bot.sent_messages)} messages")
        for i, msg in enumerate(context.bot.sent_messages):
            logger.info(f"Message {i+1}: {msg['text'][:200]}...")
        
        # Check history
        logger.info("Checking conversation history...")
        history = get_history(test_user_id)
        logger.info(f"History has {len(history)} messages")
        for msg in history[-3:]:  # Show last 3 messages
            logger.info(f"  {msg['role']}: {msg['content'][:100]}...")
            
        logger.info("=== Test completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_message_processing()) 