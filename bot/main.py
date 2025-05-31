import os
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from telegram.ext import Application
from telegram import Update
from bot.telegram_router import setup_handlers, handle_update
from bot.proactive import send_for_timezone_slot
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
            Config.TELEGRAM_BOT_TOKEN).read_timeout(120).write_timeout(120).build()
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
    async def webhook(request: Request, background_tasks: BackgroundTasks):
        """Handle Telegram webhook updates with immediate acknowledgment"""
        # Get update data
        update_data = await request.json()

        # Return OK immediately to Telegram
        response = {"status": "ok"}

        # Handle the update differently in test mode
        if os.environ.get("TESTING") == "True" or app.state.telegram_bot is None:
            # For testing, just return OK without background processing
            return response

        # Schedule background processing of the update
        background_tasks.add_task(handle_update, update_data, app.state.telegram_bot)
        
        return response

    @app.get("/health")
    async def health():
        """Health check endpoint for Cloud Run"""
        return {"status": "ok"}

    @app.post("/admin/send-proactive")
    async def send_proactive_messages(timezone: str, slot: str):
        """
        Send proactive messages to all users in a specific timezone and time slot.
        Called by Cloud Scheduler jobs.
        
        Args:
            timezone (str): Timezone string (e.g., 'Asia/Makassar', 'Europe/Moscow')
            slot (str): Time slot ('morning' or 'evening')
            
        Returns:
            dict: Results with 'sent' and 'skipped' counts
        """
        try:
            # Validate slot parameter
            if slot not in ['morning', 'evening']:
                raise HTTPException(status_code=400, detail=f"Invalid slot: {slot}. Must be 'morning' or 'evening'")
            
            # Validate timezone parameter
            valid_timezones = ['Asia/Makassar', 'Europe/Moscow']
            if timezone not in valid_timezones:
                raise HTTPException(status_code=400, detail=f"Invalid timezone: {timezone}. Must be one of {valid_timezones}")
            
            logger.info(f"Received proactive message request: timezone={timezone}, slot={slot}")
            
            # Send messages
            result = send_for_timezone_slot(timezone, slot)
            
            logger.info(f"Proactive message request completed: {result}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in send_proactive_messages endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

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
