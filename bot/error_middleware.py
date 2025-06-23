import json
import logging
import traceback
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from telegram.ext import Application
from telegram import Update

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch unhandled exceptions in the application,
    log them in structured format, and return standardized error responses.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and handle any exceptions

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: Either the normal response or an error response
        """
        try:
            # Attempt to process the request normally
            return await call_next(request)

        except Exception as e:
            # Get exception details
            error_detail = str(e)
            stack_trace = traceback.format_exc()

            # Log the error in structured JSON format
            error_log = {
                "level": "ERROR",
                "message": f"Unhandled exception: {error_detail}",
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(e).__name__,
                "stack_trace": stack_trace,
            }

            # Log as JSON string for better Cloud Run logging integration
            logger.error(json.dumps(error_log))

            # Return a standardized error response
            # Telegram expects a 200 response, even for errors
            return JSONResponse(
                status_code=200,  # Respond with 200 for Telegram
                content={"error": "internal"},
            )


async def telegram_error_handler(update: object, context) -> None:
    """
    Handle errors from the Telegram bot application.
    
    Args:
        update: The update that caused the error (can be None)
        context: The context containing the error
    """
    try:
        # Get error details
        error = context.error
        error_detail = str(error)
        stack_trace = traceback.format_exc()
        
        # Prepare error log
        error_log = {
            "level": "ERROR",
            "message": f"Telegram bot error: {error_detail}",
            "exception_type": type(error).__name__,
            "stack_trace": stack_trace,
        }
        
        # Add update information if available
        if update:
            try:
                if isinstance(update, Update):
                    error_log.update({
                        "update_id": update.update_id,
                        "user_id": update.effective_user.id if update.effective_user else None,
                        "chat_id": update.effective_chat.id if update.effective_chat else None,
                    })
            except Exception:
                # If we can't extract update info, continue without it
                pass
        
        # Log the error
        logger.error(json.dumps(error_log))
        
    except Exception as logging_error:
        # Fallback logging if the error handler itself fails
        logger.error(f"Error in telegram error handler: {logging_error}")
        logger.error(f"Original error: {context.error}")


def setup_error_handler(application: Application) -> None:
    """
    Set up error handling for the Telegram bot application.
    
    Args:
        application: The Telegram bot Application instance
    """
    application.add_error_handler(telegram_error_handler)
    logger.info("Telegram error handler has been set up")


def add_error_middleware(app: FastAPI):
    """
    Add the error handling middleware to a FastAPI application

    Args:
        app: The FastAPI application
    """
    app.add_middleware(ErrorHandlingMiddleware)
