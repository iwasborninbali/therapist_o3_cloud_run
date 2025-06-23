import os
import logging

logger = logging.getLogger(__name__)

# --- File path for the o3 default prompt ---
PROMPT_DIR = os.path.dirname(__file__)
O3_PROMPT_PATH = os.path.join(PROMPT_DIR, "o3_therapist_default_prompt.txt")


def load_o3_therapist_default_prompt() -> str:
    """Loads the o3 therapist default system prompt from its file."""
    try:
        with open(O3_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(
            f"o3 therapist default prompt not found at {O3_PROMPT_PATH}. Using a basic fallback."
        )
        return "You are a helpful AI assistant."


# Load the prompt into a constant so it's read from disk only once on module import
O3_THERAPIST_DEFAULT_PROMPT = load_o3_therapist_default_prompt()
