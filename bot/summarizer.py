import logging
import google.generativeai as genai
from config import Config

logger = logging.getLogger(__name__)

# Initialize Gemini API
genai.configure(api_key=Config.GEMINI_API_KEY)


def summarize(message_contents: list[str]) -> str:
    """
    Generate a summary of conversation messages using Gemini.

    Args:
        message_contents (list[str]): A list of message content strings to summarize.

    Returns:
        str: Generated summary or an error message.
    """
    try:
        # TODO: Implement full Gemini 2.5 Pro integration in separate task
        # This is a stub implementation for now.
        
        if not message_contents:
            return "No messages to summarize."
        
        num_messages = len(message_contents)
        
        # Combine a snippet of the messages for a placeholder summary
        # Show first 3 messages as preview
        preview = " | ".join(message_contents[:3]) 
        if len(message_contents) > 3:
            preview += "..."

        summary = f"Summary of {num_messages} messages. Preview: {preview}"
        
        log_message = f"Generated stub summary for {num_messages} message contents"
        logger.info(log_message)
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Error generating summary"
