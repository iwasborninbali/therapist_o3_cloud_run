import logging
from openai import OpenAI
from config import Config
from bot.retry_utils import retry_sync

logger = logging.getLogger(__name__)

# OpenAI client will be initialized lazily
_client = None

def get_client():
    """Get OpenAI client, creating it if needed"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=Config.OPENAI_API_KEY)
    return _client


@retry_sync()
def get_response(messages):
    """
    Get a response from OpenAI based on the conversation messages

    Args:
        messages (list): List of message dictionaries with role and content

    Returns:
        str: The AI-generated response
    """
    try:
        logger.debug(
            f"Sending request to OpenAI with {len(messages)} messages")

        client = get_client()
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ],
            temperature=0.7,
            max_tokens=1000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )

        # Extract the response content
        response_text = response.choices[0].message.content
        logger.debug(f"Received response from OpenAI: {response_text[:50]}...")

        return response_text

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return "I'm sorry, I encountered an issue processing your request. " \
               "Please try again later."
