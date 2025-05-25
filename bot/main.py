import os
from fastapi import FastAPI, Request, HTTPException
from telegram.ext import Application
from telegram import Update
from bot.telegram_router import setup_handlers
from contextlib import asynccontextmanager
from bot.error_middleware import add_error_middleware
import logging

# Configure logging
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the FastAPI app"""
    # Initialize the bot on startup
    app.state.telegram_bot = await initialize_bot()
    yield
    # Shutdown the bot on app shutdown
    if app.state.telegram_bot:
        await app.state.telegram_bot.shutdown()

# Initialize Telegram Bot application


async def initialize_bot():
    """Initialize the Telegram bot application"""
    from config import Config

    try:
        telegram_bot = Application.builder().token(
            Config.TELEGRAM_BOT_TOKEN).build()
        setup_handlers(telegram_bot)
        await telegram_bot.initialize()
        return telegram_bot
    except Exception:
        # In test environments, we might not have a real token, so return a stub
        if os.environ.get("TESTING") == "True":
            return None
        raise


def build_app():
    """Build and configure the FastAPI application"""
    app = FastAPI(lifespan=lifespan)

    # Add error handling middleware
    add_error_middleware(app)

    @app.get("/")
    async def root():
        """Root endpoint to indicate bot is active."""
        return {
            "status": "ok",
            "message": ("Bot is active. Webhook is configured at /webhook. "
                        "Health check at /health.")
        }

    @app.post("/webhook")
    async def webhook(request: Request):
        """Handle Telegram webhook updates"""
        # Get update data
        update_data = await request.json()

        # Handle the update differently in test mode
        if os.environ.get("TESTING") == "True" or app.state.telegram_bot is None:
            # For testing, just return OK
            # The test fixtures will handle mocking the appropriate components
            return {"status": "ok"}

        # Create Update object from JSON data and process it
        try:
            update = Update.de_json(update_data, app.state.telegram_bot.bot)
            await app.state.telegram_bot.process_update(update)
        except Exception as e:
            # Log the error but return OK to Telegram to avoid retries
            logger.error(f"Error processing update: {e}")
        
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        """Health check endpoint for Cloud Run"""
        return {"status": "ok"}

    @app.post("/send-proactive")
    async def send_proactive_message(request: Request):
        """Send a proactive message to the user - called by Cloud Scheduler"""
        try:
            # Import here to avoid circular imports
            from scripts.proactive_messages import send_proactive_message
            
            # Verify the request is from Cloud Scheduler (optional security check)
            user_agent = request.headers.get("user-agent", "")
            if not user_agent.startswith("Google-Cloud-Scheduler"):
                logger.warning(f"Proactive message endpoint called by non-scheduler: {user_agent}")
            
            logger.info("Received proactive message request from scheduler")
            
            # Send the proactive message (backward compatibility)
            send_proactive_message()
            
            return {"status": "success", "message": "Proactive message sent"}
            
        except Exception as e:
            logger.error(f"Error sending proactive message: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send proactive message: {str(e)}")

    @app.post("/send-proactive/{timezone}")
    async def send_proactive_message_timezone(timezone: str, request: Request):
        """Send proactive messages to all users in a specific timezone - called by Cloud Scheduler"""
        try:
            # Import here to avoid circular imports
            from scripts.proactive_messages import send_proactive_messages_for_timezone
            
            # Verify the request is from Cloud Scheduler (optional security check)
            user_agent = request.headers.get("user-agent", "")
            if not user_agent.startswith("Google-Cloud-Scheduler"):
                logger.warning(f"Proactive message endpoint called by non-scheduler: {user_agent}")
            
            # Validate timezone
            valid_timezones = ["Asia/Makassar", "Europe/Moscow"]
            if timezone not in valid_timezones:
                raise HTTPException(status_code=400, detail=f"Invalid timezone. Valid options: {valid_timezones}")
            
            logger.info(f"Received proactive message request for timezone {timezone}")
            
            # Send proactive messages for this timezone
            send_proactive_messages_for_timezone(timezone)
            
            location = "Bali" if timezone == "Asia/Makassar" else "Moscow"
            return {"status": "success", "message": f"Proactive messages sent for {location} timezone"}
            
        except Exception as e:
            logger.error(f"Error sending proactive messages for timezone {timezone}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send proactive messages: {str(e)}")

    return app


# Create the app instance
app = build_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bot.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )
