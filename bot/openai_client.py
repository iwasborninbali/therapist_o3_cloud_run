import logging
from typing import List, Dict, Any, Tuple
from openai import OpenAI, AsyncOpenAI
from config import Config
from bot.retry_utils import retry_async
from bot.prompt_builder import FactSummaryResult
import json
from bot.schemas import tools_schema as o3_tools_schema
import httpx
import time
import base64

logger = logging.getLogger(__name__)

# OpenAI client will be initialized lazily
_client = None
_async_client = None


def get_client():
    """Get OpenAI client, creating it if needed"""
    global _client
    if _client is None:
        # Create custom httpx client with connection pooling and timeouts
        http_client = httpx.Client(
            timeout=httpx.Timeout(240.0),  # 4 minutes total timeout
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30.0
            ),
            http2=True  # Enable HTTP/2 for better performance
        )
        
        _client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            timeout=240.0,  # 4 minutes timeout for OpenAI requests (increased from 2)
            http_client=http_client
        )
    return _client


def get_async_client():
    """Get Async OpenAI client, creating it if needed"""
    global _async_client
    if _async_client is None:
        # Create custom async httpx client with connection pooling and timeouts
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(240.0),  # 4 minutes total timeout
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=15,  # Increased for better connection reuse
                keepalive_expiry=600.0  # 10 minutes - longer connection lifetime
            ),
            http2=True  # Enable HTTP/2 for better performance
        )
        
        _async_client = AsyncOpenAI(
            api_key=Config.OPENAI_API_KEY,
            timeout=240.0,  # 4 minutes timeout (increased from 2)
            http_client=http_client
        )
    return _async_client


@retry_async()
async def get_o3_response_tool(messages: List[Dict[str, Any]]):
    """
    Gets a response from the o3 model, forcing it to use the 'process_user_message' tool.

    This function makes a single API call and returns the resulting message,
    which is expected to contain a tool_call with the analysis.

    Args:
        messages: A list of message dictionaries for the conversation history.

    Returns:
        The message object from the OpenAI API response.
    """
    logger.debug(
        f"Sending request to o3 with {len(messages)} messages, forcing tool call."
    )
    aclient = get_async_client()

    try:
        response = await aclient.chat.completions.create(
            model=Config.OPENAI_MODEL,  # Should be "o3"
            messages=messages,
            tools=o3_tools_schema,
            tool_choice={
                "type": "function",
                "function": {"name": "process_user_message"},
            },
            extra_body={"reasoning_effort": "high"},
            # No max_completion_tokens needed as response is in tool
        )
        message = response.choices[0].message
        logger.debug(f"Raw o3 response message: {message}")
        return message

    except Exception as e:
        logger.error(f"Error calling o3 API with tool forcing: {e}", exc_info=True)
        # Re-raise the exception to be handled by the caller
        raise


@retry_async()
async def get_o4_mini_summary(
    messages: List[Dict[str, str]],
) -> Tuple[FactSummaryResult, str]:
    """
    Calls o4-mini with a specific payload to get a summary and reorganisation plan.
    It enforces the tool call and validates the response.

    Args:
        messages: The payload containing the system prompt and user message.

    Returns:
        A tuple containing the validated Pydantic object and the raw JSON string.

    Raises:
        ValueError: If the model response is not a valid JSON or doesn't match the schema.
    """
    overall_start = time.time()
    
    logger.info("Requesting summary from o4-mini.")
    logger.info(f"[OPENAI-TIMING] Starting o4-mini request at {time.time()}")
    
    aclient = get_async_client()

    # o4-mini requires a specific tool schema, which is defined in prompt_builder
    from bot.prompt_builder import o4_mini_tools_schema

    try:
        api_start = time.time()
        logger.info(f"[OPENAI-TIMING] About to call OpenAI API...")
        
        response = await aclient.chat.completions.create(
            model="o4-mini",
            messages=messages,
            tools=o4_mini_tools_schema,
            tool_choice={
                "type": "function",
                "function": {"name": "process_context_for_summary"},
            },
            extra_body={"reasoning_effort": "high"},
        )
        
        api_end = time.time()
        logger.info(f"[OPENAI-TIMING] OpenAI API call completed in {api_end - api_start:.2f}s")

        raw_response_content = response.choices[0].message.tool_calls[0].function.arguments
        logger.debug(f"Raw o4-mini response: {raw_response_content}")

        try:
            parse_start = time.time()
            # First, parse the string into a Python dictionary
            response_data = json.loads(raw_response_content)
            # Then, validate the dictionary against the Pydantic model
            validated_result = FactSummaryResult.model_validate(response_data)
            parse_end = time.time()
            
            logger.info("o4-mini response validated successfully.")
            logger.info(f"[OPENAI-TIMING] Parsing took {parse_end - parse_start:.2f}s")
            logger.info(f"[OPENAI-TIMING] Total o4-mini operation took {time.time() - overall_start:.2f}s")
            
            return validated_result, raw_response_content
            
        except json.JSONDecodeError:
            logger.error(
                f"Failed to decode JSON from o4-mini response: {raw_response_content}"
            )
            raise ValueError("Invalid JSON response from model.")
        except Exception as e:
            logger.error(f"Pydantic validation failed for o4-mini response: {e}")
            raise ValueError(f"Model response does not match expected schema: {e}")
            
    except Exception as e:
        api_failed_time = time.time()

        logger.error(
            f"[OPENAI-TIMING] OpenAI API failed after {api_failed_time - overall_start:.2f}s"
        )
        logger.error(f"OpenAI API error: {e}", exc_info=True)
        raise


@retry_async()
async def ask_o3_with_image(img_bytes: bytes, user_text: str, mime_type: str = "image/jpeg") -> str:
    """Send an image and optional text to the o3 model and return the reply."""
    b64 = base64.b64encode(img_bytes).decode()
    data_uri = f"data:{mime_type};base64,{b64}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ],
        }
    ]

    aclient = get_async_client()
    response = await aclient.chat.completions.create(
        model=Config.OPENAI_MODEL,
        messages=messages,
    )

    return response.choices[0].message.content


async def warmup_openai_connection():
    """
    Warm up OpenAI connection during startup to establish SSL handshake and connection pooling.
    This helps avoid slow first requests when CPU is throttled.
    """
    try:
        logger.info("🔥 Warming up OpenAI connection...")
        aclient = get_async_client()
        
        # Make a minimal request to establish connection
        start_time = time.time()
        response = await aclient.chat.completions.create(
            model="gpt-3.5-turbo",  # Cheap model for warmup
            messages=[{"role": "user", "content": "warmup"}],
            max_tokens=1  # Minimal response
        )
        
        warmup_time = time.time() - start_time
        logger.info(f"✅ OpenAI connection warmed up successfully in {warmup_time:.2f}s")
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ OpenAI warmup failed: {e}")
        return False


async def ping_openai_connection():
    """
    Send a lightweight ping to OpenAI to keep connection alive.
    Used by keep-alive worker to maintain warm connections.
    """
    try:
        logger.debug("🏓 Pinging OpenAI connection...")
        aclient = get_async_client()
        
        start_time = time.time()
        response = await aclient.chat.completions.create(
            model="gpt-3.5-turbo",  # Cheap model for ping
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1  # Minimal response
        )
        
        ping_time = time.time() - start_time
        logger.debug(f"✅ OpenAI ping successful in {ping_time:.2f}s")
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ OpenAI ping failed: {e}")
        return False
