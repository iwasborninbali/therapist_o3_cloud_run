import os
import logging
import argparse
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from telegram.ext import Application
from telegram import Update
from bot.telegram_router import setup_handlers, handle_update
from bot.error_middleware import add_error_middleware, setup_error_handler
from config import Config
from bot.firestore_client import get_db
from google.auth.exceptions import DefaultCredentialsError, TransportError
import httpx

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for health checking
last_health_check = 0
health_check_interval = 300  # 5 minutes
firebase_healthy = False

# Keep-alive task
keep_alive_task = None

def check_firebase_health():
    """Check if Firebase is healthy and update global state"""
    global firebase_healthy, last_health_check
    
    current_time = time.time()
    if current_time - last_health_check < health_check_interval:
        return firebase_healthy
    
    try:
        logger.info("Checking Firebase connectivity...")
        db = get_db()
        # Simple test operation
        test_doc = db.collection('_health_check').document('test')
        test_doc.set({'timestamp': time.time(), 'status': 'healthy'}, merge=True)
        firebase_healthy = True
        logger.info("Firebase health check passed")
    except (DefaultCredentialsError, TransportError) as e:
        logger.error(f"Firebase authentication error: {e}")
        firebase_healthy = False
    except Exception as e:
        logger.error(f"Firebase health check failed: {e}")
        firebase_healthy = False
    
    last_health_check = current_time
    return firebase_healthy

def create_telegram_bot(local_mode=False):
    """Factory function to create and configure the Telegram bot application"""
    try:
        # Validate configuration
        Config.validate()
        
        # Get the appropriate token based on mode
        token = Config.get_telegram_token(local_mode=local_mode)
        
        # Create the Application
        app = Application.builder().token(token).build()
        
        # Set up handlers
        setup_handlers(app)
        
        # Set up error handler
        setup_error_handler(app)
        
        logger.info("Telegram bot application created successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create telegram bot: {e}")
        raise

async def initialize_bot():
    """Initialize the Telegram bot application"""
    try:
        telegram_bot = create_telegram_bot()
        await telegram_bot.initialize()

        # In local mode, we will run polling from the main script entrypoint
        if os.getenv("RUN_MODE") == "local":
            logger.info("Bot initialized for polling mode.")

        return telegram_bot
    except Exception:
        # In test environments, we might not have a real token, so return a stub
        if os.environ.get("TESTING") == "True":
            return None
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the FastAPI app"""
    global keep_alive_task
    
    # Initialize the bot on startup
    logger.info("Starting up application...")
    
    # Check Firebase health on startup
    check_firebase_health()
    
    # Warm up OpenAI connection
    from bot.openai_client import warmup_openai_connection
    await warmup_openai_connection()
    
    # Initialize the bot
    app.state.telegram_bot = await initialize_bot()
    
    # Start keep-alive task in production
    if os.getenv("RUN_MODE") != "local":
        keep_alive_task = asyncio.create_task(keep_alive_worker())
        logger.info("Keep-alive task started")
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Cancel keep-alive task
    if keep_alive_task and not keep_alive_task.done():
        keep_alive_task.cancel()
        try:
            await keep_alive_task
        except asyncio.CancelledError:
            logger.info("Keep-alive task cancelled")
    
    # Shutdown the bot
    if app.state.telegram_bot:
        await app.state.telegram_bot.shutdown()
    logger.info("Application shutdown completed")

def build_app():
    """Build and configure the FastAPI application"""
    app = FastAPI(
        title="Telegram Therapist Bot",
        lifespan=lifespan
    )

    # Add error handling middleware
    add_error_middleware(app)

    @app.get("/")
    async def root():
        """Root endpoint to indicate bot is active."""
        return {
            "status": "ok",
            "message": (
                "Bot is active. Webhook is configured at /webhook. "
                "Health check at /health."
            ),
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

        # Check Firebase health before processing (non-blocking)
        if not check_firebase_health():
            logger.warning("Processing update with degraded Firebase connectivity")

        # Schedule background processing of the update
        background_tasks.add_task(handle_update, update_data, app.state.telegram_bot)

        return response

    @app.get("/health")
    async def health():
        """Health check endpoint with Firebase connectivity test"""
        try:
            firebase_status = check_firebase_health()
            
            health_data = {
                "status": "healthy" if firebase_status else "degraded",
                "firebase": "connected" if firebase_status else "disconnected",
                "timestamp": time.time()
            }
            
            status_code = 200 if firebase_status else 503
            return JSONResponse(content=health_data, status_code=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                },
                status_code=503
            )

    return app

# Create the app instance
app = build_app()

async def keep_alive_worker():
    """Keep the container and OpenAI connections warm"""
    if os.getenv("RUN_MODE") == "local":
        logger.info("Keep-alive disabled in local mode")
        return
        
    # Wait a bit before starting keep-alive
    await asyncio.sleep(120)  # 2 minutes initial delay
    
    service_url = os.getenv("SERVICE_URL", "https://therapist-o3-7kgz7ksata-uc.a.run.app")
    health_url = f"{service_url}/health"
    
    logger.info(f"Starting keep-alive worker for {health_url} + OpenAI connection")
    
    from bot.openai_client import ping_openai_connection
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        ping_counter = 0
        while True:
            try:
                # Wait 8 minutes between keep-alive cycles
                await asyncio.sleep(480)  # 8 minutes (increased from 4)
                ping_counter += 1
                
                # Health check every cycle
                response = await client.get(health_url)
                if response.status_code == 200:
                    logger.debug(f"Keep-alive health check successful (cycle {ping_counter})")
                else:
                    logger.warning(f"Keep-alive health check returned: {response.status_code}")
                
                # OpenAI ping every cycle to maintain connection
                openai_success = await ping_openai_connection()
                if openai_success:
                    logger.debug(f"OpenAI connection keep-alive successful (cycle {ping_counter})")
                else:
                    logger.warning(f"OpenAI connection keep-alive failed (cycle {ping_counter})")
                    
            except Exception as e:
                logger.error(f"Keep-alive worker failed: {e}")
                # Continue trying even if one fails
                continue

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the AI Therapist Bot.")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run the bot in local polling mode instead of webhook server mode.",
    )
    args = parser.parse_args()

    if args.local:
        # In local mode, we run the bot with polling, no web server
        logger.info("Starting bot in polling mode for local development...")

        # Initialize and run the bot directly
        # Application.run_polling() handles the asyncio event loop automatically
        try:
            # Re-create the application object here for the polling context
            local_bot = create_telegram_bot(local_mode=True)

            logger.info("Bot is running in polling mode. Press Ctrl+C to stop.")
            # run_polling is a blocking call that sets up its own asyncio loop
            local_bot.run_polling(allowed_updates=Update.ALL_TYPES)

        except KeyboardInterrupt:
            logger.info("Polling stopped by user.")
        except Exception as e:
            logger.error(f"An error occurred during polling: {e}")

    else:
        # Default mode: run with uvicorn for Cloud Run (webhook)
        logger.info("Starting bot in webhook server mode...")
        uvicorn.run("bot.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
