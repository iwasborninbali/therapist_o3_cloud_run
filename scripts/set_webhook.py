#!/usr/bin/env python3
"""
Script to set Telegram webhook after Cloud Run deployment
"""
import os
import sys
import argparse
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def set_telegram_webhook(bot_token: str, webhook_url: str) -> bool:
    """
    Set Telegram webhook URL
    
    Args:
        bot_token: Telegram bot token
        webhook_url: Full webhook URL
        
    Returns:
        bool: Success status
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    payload = {
        "url": webhook_url,
        "drop_pending_updates": True,  # Clear any pending updates
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            logger.info(f"✅ Webhook set successfully to: {webhook_url}")
            return True
        else:
            logger.error(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Set Telegram webhook")
    parser.add_argument("--url", required=True, help="Webhook URL")
    parser.add_argument("--token", help="Bot token (or use TELEGRAM_BOT_TOKEN env var)")
    
    args = parser.parse_args()
    
    # Get bot token
    bot_token = args.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("❌ Bot token not provided. Use --token or set TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    # Validate webhook URL
    webhook_url = args.url
    if not webhook_url.startswith("https://"):
        logger.error("❌ Webhook URL must use HTTPS")
        sys.exit(1)
    
    logger.info(f"Setting webhook to: {webhook_url}")
    
    # Set webhook
    if set_telegram_webhook(bot_token, webhook_url):
        logger.info("🎉 Webhook setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Failed to set webhook")
        sys.exit(1)


if __name__ == "__main__":
    main() 