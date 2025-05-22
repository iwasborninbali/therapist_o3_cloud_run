import os
import argparse
import requests
import time
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds


def set_telegram_webhook(bot_token: str, service_url: str, secret_token: str = None):
    """
    Sets the Telegram bot webhook.

    Args:
        bot_token (str): The Telegram Bot Token.
        service_url (str): The HTTPS URL of the deployed bot service.
        secret_token (str, optional): Secret token for X-Telegram-Bot-Api-Secret-Token header.

    Returns:
        bool: True if successful, False otherwise.
    """
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {"url": service_url}
    if secret_token:
        payload["secret_token"] = secret_token

    logger.info(
        f"Attempting to set webhook for bot token ending ...{bot_token[-6:]} "
        f"to URL: {service_url}")
    if secret_token:
        logger.info("Using a secret token.")

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                telegram_api_url, json=payload, timeout=10)  # 10 second timeout
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

            result = response.json()
            if result.get("ok") and result.get("result") is True:
                logger.info(
                    f"Successfully set webhook: {result.get('description', 'OK')}")
                return True
            else:
                logger.error(
                    f"Failed to set webhook. Telegram API response: {result}")
                return False  # Explicitly return False on non-ok result

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if 500 <= status_code < 600 and attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"Telegram API returned HTTP {status_code}. "
                    f"Retrying in {delay}s... (Attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Telegram API returned HTTP {status_code}. Error: {e}. No more retries.")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request failed: {e}. Attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
            else:
                logger.error(
                    "Failed after multiple retries due to request exceptions.")
                return False
        except Exception as e:  # Catch any other unexpected error during the process
            logger.error(
                f"An unexpected error occurred: {e}. Attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
            else:
                logger.error(
                    "Failed after multiple retries due to unexpected errors.")
                return False

    return False  # Should be unreachable if all attempts fail and return False inside loop


def main():
    parser = argparse.ArgumentParser(description="Set the Telegram bot webhook.")
    parser.add_argument(
        "--token",
        default=os.environ.get("TELEGRAM_BOT_TOKEN"),
        help=("Telegram Bot Token. Can also be set via "
              "TELEGRAM_BOT_TOKEN environment variable.")
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("SERVICE_URL"),
        help=("The HTTPS URL of your deployed bot service. Can also be set via "
              "SERVICE_URL environment variable.")
    )
    parser.add_argument(
        "--secret-token",
        default=os.environ.get("TELEGRAM_SECRET_TOKEN"),
        help=("Optional secret token for X-Telegram-Bot-Api-Secret-Token header. "
              "Can also be set via TELEGRAM_SECRET_TOKEN environment variable.")
    )

    args = parser.parse_args()

    if not args.token:
        logger.error(
            "Error: Telegram Bot Token is required. "
            "Provide --token or set TELEGRAM_BOT_TOKEN env var.")
        exit(1)

    if not args.url:
        logger.error(
            "Error: Service URL is required. "
            "Provide --url or set SERVICE_URL env var.")
        exit(1)

    if not args.url.startswith("https://"):
        logger.error(
            f"Error: Service URL must be HTTPS. Provided: {args.url}")
        exit(1)

    success = set_telegram_webhook(args.token, args.url, args.secret_token)
    if success:
        logger.info("Webhook setup process completed successfully.")
        exit(0)
    else:
        logger.error("Webhook setup process failed.")
        exit(1)


if __name__ == "__main__":
    main()
