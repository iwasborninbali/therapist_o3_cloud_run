import os
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Load environment variables from .env file first
load_dotenv(override=False)

# Handle Firebase credentials - Use service identity when running on Cloud Run
# For local development, fall back to GOOGLE_APPLICATION_CREDENTIALS
google_app_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Check if running on Cloud Run (has metadata server)


def is_running_on_cloud_run():
    try:
        import requests

        response = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
            timeout=1,
        )
        return response.status_code == 200
    except Exception:
        return False


if is_running_on_cloud_run():
    # Running on Cloud Run - use service identity (no explicit credentials needed)
    logging.info(
        "Running on Cloud Run - using service identity for Firebase authentication"
    )
elif google_app_creds_path:
    # Local development with existing GOOGLE_APPLICATION_CREDENTIALS
    logging.info(
        "Local development - using GOOGLE_APPLICATION_CREDENTIALS: %s",
        google_app_creds_path,
    )
elif os.getenv("TESTING") == "True":
    logging.warning("Running in test mode without Firebase credentials")
else:
    raise RuntimeError(
        "Firebase credentials required for local development: "
        "set GOOGLE_APPLICATION_CREDENTIALS path in your .env file"
    )


class Config:
    """Configuration settings loaded from environment variables"""

    # Telegram Bot credentials
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")

    # OpenAI API credentials
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "o3")



    # Firebase configuration
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # Retry configuration
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))

    # History and Summarization configuration
    HISTORY_THRESHOLD_MESSAGES = int(os.getenv("HISTORY_THRESHOLD_MESSAGES", "50"))
    MESSAGES_TO_SUMMARIZE_COUNT = int(os.getenv("MESSAGES_TO_SUMMARIZE_COUNT", "30"))
    MAX_SUMMARIES = int(os.getenv("MAX_SUMMARIES", "5"))

    # Idempotency configuration
    IDEMPOTENCY_COLLECTION = os.getenv("IDEMPOTENCY_COLLECTION", "processed_updates")

    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        missing = []

        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")

        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")



        if not cls.FIREBASE_PROJECT_ID:
            missing.append("FIREBASE_PROJECT_ID")

        # Only require GOOGLE_APPLICATION_CREDENTIALS for local development
        if (
            not is_running_on_cloud_run()
            and not cls.GOOGLE_APPLICATION_CREDENTIALS
            and os.getenv("TESTING") != "True"
        ):
            missing.append("GOOGLE_APPLICATION_CREDENTIALS")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return True


# Create a global instance of the config
config = Config()


# Default system prompt for AI therapist, loaded from file
def load_default_prompt():
    """Loads the default system prompt from a file."""
    try:
        # Construct path relative to the config.py file
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "bot",
            "prompts",
            "o3_therapist_default_prompt.txt",
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.error("Default system prompt file not found! Using a basic fallback.")
        return "You are a helpful AI therapist."


DEFAULT_SYSTEM_PROMPT = load_default_prompt()

# Export the config instance and constants
__all__ = [
    "config",
    "DEFAULT_SYSTEM_PROMPT",
]
