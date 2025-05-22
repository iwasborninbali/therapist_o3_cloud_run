import json
import logging
import traceback
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

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
                "stack_trace": stack_trace
            }

            # Log as JSON string for better Cloud Run logging integration
            logger.error(json.dumps(error_log))

            # Return a standardized error response
            # Telegram expects a 200 response, even for errors
            return JSONResponse(
                status_code=200,  # Respond with 200 for Telegram
                content={"error": "internal"}
            )


def add_error_middleware(app: FastAPI):
    """
    Add the error handling middleware to a FastAPI application

    Args:
        app: The FastAPI application
    """
    app.add_middleware(ErrorHandlingMiddleware)
