import os
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Handle Firebase credentials from FIREBASE_CRED_JSON if not otherwise set
firebase_cred_json_content = os.getenv("FIREBASE_CRED_JSON")
google_app_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if firebase_cred_json_content and not google_app_creds_path:
    # Use /tmp as a generally available writable path.
    # Cloud Run /workspace is also an option if targeting only Cloud Run.
    cred_file_path = "/tmp/firebase_service_account.json"
    try:
        with open(cred_file_path, "w") as f:
            f.write(firebase_cred_json_content)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_file_path
        logging.info(
            f"Set GOOGLE_APPLICATION_CREDENTIALS from FIREBASE_CRED_JSON "
            f"(written to {cred_file_path})"
        )
    except IOError as e:
        logging.error(
            f"Failed to write FIREBASE_CRED_JSON to {cred_file_path}: {e}"
        )
        # App may fail Firebase init.

# Load environment variables from .env file
# This is after potential GOOGLE_APPLICATION_CREDENTIALS modification.
load_dotenv(override=False)


@dataclass
class Config:
    """Configuration settings loaded from environment variables"""

    # Telegram Bot credentials
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")

    # OpenAI API credentials
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "o3")

    # Gemini API credentials
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")

    # Firebase configuration
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS")

    # Retry configuration
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_BASE_DELAY: float = float(os.getenv("RETRY_BASE_DELAY", "1.0"))

    # History and Summarization configuration
    HISTORY_THRESHOLD_MESSAGES: int = int(
        os.getenv("HISTORY_THRESHOLD_MESSAGES", "30"))
    MESSAGES_TO_SUMMARIZE_COUNT: int = int(
        os.getenv("MESSAGES_TO_SUMMARIZE_COUNT", "20"))
    MAX_SUMMARIES: int = int(os.getenv("MAX_SUMMARIES", "3"))

    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        missing = []

        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")

        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")

        if not cls.FIREBASE_PROJECT_ID:
            missing.append("FIREBASE_PROJECT_ID")

        if not cls.GOOGLE_APPLICATION_CREDENTIALS:
            missing.append("GOOGLE_APPLICATION_CREDENTIALS")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}")

        return True


# Create a global instance of the config
config = Config()

# Export the config instance
__all__ = [
    "config"
]
