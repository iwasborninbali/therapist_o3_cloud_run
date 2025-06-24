#!/usr/bin/env python3
"""
Local testing script for Telegram bot with detailed timing logs
"""

import os
import sys
import logging
import asyncio

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment for local development
os.environ["RUN_MODE"] = "local"

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("local_bot.log")
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run the bot locally with polling"""
    try:
        from config import Config
        from bot.telegram_router import setup_handlers, get_factology_manager
        from bot.error_middleware import setup_error_handler
        from telegram.ext import Application
        from telegram import Update
        
        logger.info("🚀 Starting local bot with polling...")
        logger.info("📝 Logs will be saved to local_bot.log")
        
        # Validate configuration
        Config.validate()
        
        # Create the Application
        app = Application.builder().token(Config.get_telegram_token(local_mode=True)).build()
        
        # Set up handlers
        setup_handlers(app)
        setup_error_handler(app)
        
        # Initialize factology manager
        factology_manager = get_factology_manager()
        logger.info("FactologyManager initialized for local testing")
        
        logger.info("✅ Bot is running in LOCAL POLLING mode")
        logger.info("📱 Send a message to your bot to test OpenAI timing")
        logger.info("🛑 Press Ctrl+C to stop")
        
        # Run polling
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}", exc_info=True)

if __name__ == "__main__":
    main() 