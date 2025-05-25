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
            return "No messages to summarize."
        
        # Combine all messages into a single conversation text
        conversation_text = "\n".join([
            f"Message {i+1}: {content}" 
            for i, content in enumerate(message_contents)
        ])
        
        # Create the summarization prompt
        prompt = f"""Сделай саммари этой переписки между пользователем и терапевтом. Убедись, что ты отразил все важные топики и ключевые моменты беседы. 

Выдай саммари не более чем в 5 предложениях.

Переписка для суммаризации:
{conversation_text}

Саммари:"""

        # Use Gemini 2.5 Pro model
        model = genai.GenerativeModel('gemini-2.5-pro-preview-05-06')
        
        # Generate the summary
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Lower temperature for more focused summary
                max_output_tokens=10000,  # Allow longer summaries
            )
        )
        
        if response.text:
            summary = response.text.strip()
            logger.info(f"Generated summary for {len(message_contents)} messages using Gemini 2.5 Pro")
            return summary
        else:
            logger.error("Empty response from Gemini API")
            return "Error: Empty response from Gemini API"
        
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {str(e)}")
        return f"Error generating summary: {str(e)}"
