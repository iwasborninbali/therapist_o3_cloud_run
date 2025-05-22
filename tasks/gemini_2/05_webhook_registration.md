# Task: Webhook Auto-Registration Utility

## Objective
Create a script to automatically set or update the Telegram bot's webhook URL after deployment, and ensure the main application can respond to root path requests.

## Files to Modify/Create
- `scripts/set_webhook.py` (new) - CLI script to call Telegram's `setWebhook` API.
- `bot/main.py` - Added a handler for the root path (`/`).
- `README.md` - Documented the script usage and the overall one-click deployment process.

## Implementation Details

### `scripts/set_webhook.py`
- **CLI Arguments:**
    - `--token` (or `TELEGRAM_TOKEN` from env): The Telegram Bot Token. (Required)
    - `--url` (or `SERVICE_URL` from env): The HTTPS URL of the deployed bot service where Telegram should send updates. (Required)
    - `--secret-token` (or `TELEGRAM_SECRET_TOKEN` from env): Optional secret token for `X-Telegram-Bot-Api-Secret-Token` header.
- **Functionality:**
    - Constructed the `setWebhook` API URL.
    - Makes a POST request with a JSON payload: `{"url": "SERVICE_URL", "secret_token": "TELEGRAM_SECRET_TOKEN" (if provided)}`.
    - **Retry Logic:** Implemented retries (3 attempts with exponential backoff) for 5xx HTTP status codes from the Telegram API.
    - **Error Handling:** Prints clear error messages and exits with non-zero code on failure.
    - **Success Message:** Prints a success message.
    - Uses the `requests` library and `argparse`.

### `bot/main.py`
- Added a GET request handler for the root path (`/`) returning `{"status": "ok", "message": "Bot is active..."}`.

### `README.md`
- **Deployment Section Update:** Explained automatic call of `set_webhook.py` by CI/CD.
- **Manual Script Usage:** Provided instructions and examples for manual execution.
- Updated environment variable examples and project structure.

## Configuration
- Script relies on `TELEGRAM_BOT_TOKEN`, `SERVICE_URL`, and optionally `TELEGRAM_SECRET_TOKEN` via args or env vars.

## Status: done