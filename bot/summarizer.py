import logging
import google.generativeai as genai
from config import Config

logger = logging.getLogger(__name__)

# Initialize Gemini API
genai.configure(api_key=Config.GEMINI_API_KEY)


def summarize(message_contents: list[str]) -> str:
    """
    Generate a summary of conversation messages using Gemini 2.5 Pro.

    Args:
        message_contents (list[str]): A list of message content strings to summarize.

    Returns:
        str: Generated summary or an error message.
    """
    try:
        if not message_contents:
            logger.warning("No messages provided for summarization")
            return "No messages to summarize."
        
        logger.info(f"Starting summarization of {len(message_contents)} messages")
        
        # Combine all messages into a single conversation text
        conversation_text = "\n".join([
            f"Message {i+1}: {content}" 
            for i, content in enumerate(message_contents)
        ])
        
        logger.debug(f"Conversation text length: {len(conversation_text)} characters")
        
        # Create the summarization prompt
        prompt = f"""Сделай саммари этой переписки между пользователем и терапевтом. Убедись, что ты отразил все важные топики и ключевые моменты беседы. 

Выдай саммари не более чем в 5 предложениях.

Переписка для суммаризации:
{conversation_text}

Саммари:"""

        # Use Gemini 2.5 Pro model
        model = genai.GenerativeModel('gemini-2.5-pro-preview-05-06')
        logger.debug("Initialized Gemini 2.5 Pro model for summarization")
        
        # Generate the summary
        logger.info("Sending request to Gemini API for summarization")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Lower temperature for more focused summary
                max_output_tokens=10000,  # Allow longer summaries
            )
        )
        
        if response.text:
            summary = response.text.strip()
            logger.info(f"✅ Successfully generated summary for {len(message_contents)} messages. Summary length: {len(summary)} characters")
            logger.debug(f"Generated summary: {summary[:200]}..." if len(summary) > 200 else f"Generated summary: {summary}")
            return summary
        else:
            logger.error("❌ Empty response from Gemini API")
            return "Error: Empty response from Gemini API"
        
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {str(e)}")
        return f"Error generating summary: {str(e)}"
