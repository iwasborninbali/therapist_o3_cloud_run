# Telegram AI Assistant

[![CI](https://github.com/USERNAME/REPO_NAME/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/REPO_NAME/actions/workflows/ci.yml)
<!-- Add Production Deploy Badge once Gemini_1 sets it up -->

A containerized Telegram bot that integrates with OpenAI's API to provide AI-assisted conversations, with data storage in Firebase Firestore. The application is deployed on Google Cloud Run.

## Architecture Overview

The application consists of two Cloud Run services:

```
┌─────────────────────┐    ┌──────────────────────┐
│   therapist-o3      │    │ therapist-scheduler  │
│   (Main Bot)        │    │ (Proactive Messages) │
├─────────────────────┤    ├──────────────────────┤
│ • FastAPI webhook   │    │ • Python scheduler   │
│ • Public endpoint   │    │ • Private service    │
│ • Scales 0-10       │    │ • Always-on (min=1)  │
│ • 1GB RAM, 1 CPU    │    │ • 512MB RAM, 0.5 CPU │
└─────────────────────┘    └──────────────────────┘
           │                           │
           └───────────┬───────────────┘
                       │
                ┌─────────────┐
                │  Firestore  │
                │  Database   │
                └─────────────┘
```

## Features

- Conversation history management with Firebase Firestore
- Context-aware AI responses using OpenAI
- Automatic summarization of long conversations using Gemini
- User-specific system prompts
- Automated conversation length management with history trimming and summarization
- **Universal proactive message scheduler** with per-user timezone support and deduplication
- Robust error handling and retry mechanisms for external API calls
- **Automated CI/CD pipeline** with auto-deploy to Google Cloud Run

## Environment Setup

1. Copy the example environment file to create your own:
   ```
   cp .env.example .env
   ```

2. Edit the `.env` file and fill in your actual credentials:
   ```
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_SECRET_TOKEN=optional_secret_for_webhook # Optional: if you want to use X-Telegram-Bot-Api-Secret-Token

   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=o3

   # Gemini Configuration
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-2.5-pro-preview-05-06 # Or your preferred Gemini model for summarization

   # Firebase Configuration
   FIREBASE_PROJECT_ID=your_firebase_project_id # Replace with your Firebase Project ID
   # IMPORTANT: For local development, GOOGLE_APPLICATION_CREDENTIALS should point to the *path* of your service account JSON file.
   # NEVER commit the actual service account JSON file to the repository. Ensure it's in your .gitignore.
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/firebase/credentials.json 
   # OR, for environments like Cloud Run where file paths are inconvenient for secrets (managed via GitHub Secrets):
   FIREBASE_CRED_JSON='{"type": "service_account", ...}' # Paste the full JSON content of your service account key here. 
                                                     # This is intended for CI/CD pipelines using GitHub Secrets. config.py will write this to a temporary file.

   # Application Configuration
   LOG_LEVEL=INFO
   SERVICE_URL=your_deployed_service_url # Required by set_webhook.py if not passed as arg; will be set by CD
   
   # Resilience Configuration
   RETRY_ATTEMPTS=3
   RETRY_BASE_DELAY=1.0 # In seconds

   # History and Summarization Configuration
   HISTORY_THRESHOLD_MESSAGES=50 # Number of messages before triggering summarization (25 pairs)
   MESSAGES_TO_SUMMARIZE_COUNT=30 # Number of oldest messages to summarize (15 pairs)
   MAX_SUMMARIES=5 # Maximum number of stored summaries per user (FIFO)
   ```

## Security Considerations

**NEVER COMMIT SERVICE ACCOUNT KEYS OR OTHER SENSITIVE CREDENTIALS TO THE REPOSITORY.**

- All sensitive information (API keys, service account JSON, tokens) for deployed environments (like Cloud Run) **must** be managed via GitHub Secrets.
- For local development, if you use a service account JSON file (`GOOGLE_APPLICATION_CREDENTIALS`), ensure the file path is listed in your `.env` file, but the JSON file itself **must** be covered by `.gitignore` (e.g., `*-firebase-adminsdk*.json`, `*-sa.json`, `*.private.*json`) and never committed.
- The CI/CD pipeline includes checks to prevent accidental commits of known credential file patterns.
- If a credential is ever accidentally committed, it must be considered compromised: revoke it immediately in the relevant cloud console and rotate to a new credential.

## Conversation Length Management

To ensure efficient processing and manage context windows for the AI model, the bot implements automatic history rotation and summarization:

- **Threshold:** When the number of complete user-assistant message pairs exceeds 25 pairs (50 total messages), the oldest portion of the conversation is summarized. This is controlled by `HISTORY_THRESHOLD_MESSAGES` (default: 50).
- **Summarization:** The oldest 15 message pairs (30 messages total) are passed to Gemini 2.5 Pro to generate a concise summary in no more than 5 sentences, focusing on all important topics. This is controlled by `MESSAGES_TO_SUMMARIZE_COUNT` (default: 30).
- **Storage:** This summary is then stored in Firestore. Up to `MAX_SUMMARIES` (default: 5) are kept per user, with older summaries being replaced in a First-In, First-Out (FIFO) manner.
- **Contextual Prompting:** Stored summaries are prepended to the conversation history (after the system prompt) when making new requests to OpenAI, providing the AI with context from older parts of the conversation without exceeding token limits.
- **Trimming:** The messages that were summarized are then removed from the active conversation history in Firestore to keep the main history log manageable.

This process helps maintain long-term context for extended conversations while keeping the operational cost and API request sizes optimized.

## Proactive Message Scheduler

The bot includes a universal proactive message scheduler that sends automated check-ins to users at 10:00 AM and 8:00 PM in their local timezone.

### How It Works

- **Per-User Timezone Support**: Each user can set their timezone via the `/timezone` command (Bali or Moscow currently supported)
- **Universal Scheduler**: A single Cloud Run service (`Dockerfile.scheduler`) runs `scripts/proactive_messages.py` continuously
- **Deduplication**: Uses Firestore `proactive_meta` collection to track when messages were last sent, preventing duplicates
- **Smart Timing**: Checks every 5 minutes (configurable via `PROACTIVE_CHECK_INTERVAL`) and only sends messages during the exact hour (10:00 or 20:00)

### Configuration

```bash
# Environment variables for scheduler
PROACTIVE_CHECK_INTERVAL=300  # Check interval in seconds (default: 5 minutes)
```

### Firestore Collections

The scheduler uses these Firestore collections:

- `user_settings`: Stores user timezone preferences
- `proactive_meta`: Tracks last sent dates per user and time slot to prevent duplicates
  ```json
  {
    "morning": "2025-05-25",    // Last date morning message was sent
    "evening": "2025-05-25",    // Last date evening message was sent
    "updated_at": "timestamp"
  }
  ```

### Deployment

The scheduler runs as a separate Cloud Run service built from `Dockerfile.scheduler`. It operates independently from the main bot service and continuously monitors all users for proactive message opportunities.

#### Scheduler Hot-fix Deploy

To deploy the scheduler service manually:

```bash
# Deploy scheduler with same configuration as main bot
./scripts/build_and_deploy_scheduler.sh
```

This script:
- Builds Docker image from `Dockerfile.scheduler`
- Copies environment variables from the main `therapist-o3` service
- Deploys with `min-instances=1` for continuous operation
- Uses the same service account for Firebase authentication

## Local Development & Testing

### Local Smoke Test

You can run a quick automated test to verify that core functionality is working without needing to set up Docker or webhook integrations:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the tests (excluding container tests)
pytest
```

All tests should pass, confirming that:
- The application starts correctly
- The health endpoint and root endpoint return "ok"
- The webhook can process Telegram updates (mocked)
- Messages are properly formatted for OpenAI
- The conversation history storage and rotation is working as expected (mocked Firestore)

This provides a simple verification that the core components are functioning without requiring any external services or complex setup.

### Container Testing

The project includes Docker container tests that verify the application works correctly when containerized:

```bash
# Ensure Docker is running
# Install development dependencies (if not already done)
pip install -r requirements.txt 

# Run container tests (requires Docker and permissions)
pytest tests/test_container.py
```

To skip container tests (useful in environments without Docker):

```bash
SKIP_CONTAINER_TESTS=True pytest
```

The container tests verify:
- The Docker image builds successfully
- The container starts and exposes the expected endpoints
- The health check endpoint returns 200 OK
- The webhook endpoint processes Telegram updates correctly (mocked Telegram interaction with running container)

**Requirements:**
- Docker must be installed and running
- Python docker package (`docker==7.0.0`)
- User must have permissions to build and run Docker containers

### Running Locally with Docker

To build and run the application locally using Docker:

```bash
# Build the Docker image
docker build -t telegram-ai-assistant .

# Run the container locally, mapping port 8080 and using your .env file
docker run -p 8080:8080 --env-file .env telegram-ai-assistant
```

## CI/CD and Deployment

### Continuous Integration (CI)

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that automatically runs tests on every push and pull request:

- Builds the application in an Ubuntu environment.
- Installs all dependencies from `requirements.txt`.
- Runs the full test suite, including unit, integration, and container tests (if Docker is available).
- Verifies code quality and functionality.
- The status badge at the top of this README shows the current build status of the `main` branch.

### Code Style

We ignore cosmetic flake8 warnings by default (e.g., E501 line length, F401 unused imports); see `setup.cfg` for the current configuration. The primary focus is on security checks and functional tests passing in CI.

### Manual Deployment

Deployment is manual via `scripts/build_and_deploy*.sh` scripts. This approach provides deployment control and simplicity for this small-scale project.

**Deploy Main Bot Service:**
```bash
./scripts/build_and_deploy.sh
```

**Deploy Scheduler Service:**
```bash
./scripts/build_and_deploy_scheduler.sh
```

Both scripts handle:
1. Building the Docker image
2. Pushing to Google Container Registry
3. Deploying to Cloud Run with appropriate configuration
4. Preserving environment variables and service account settings

After deployment, manually register the webhook using `scripts/set_webhook.py` if needed.

### Manual Webhook Management

If you need to set or update the Telegram webhook manually (e.g., during local development with a tool like ngrok, or if the automated process fails), you can use the `scripts/set_webhook.py` script.

**Usage:**
```bash
python scripts/set_webhook.py --token YOUR_TELEGRAM_BOT_TOKEN --url YOUR_HTTPS_SERVICE_URL [--secret-token YOUR_SECRET]
```

- `--token`: Your Telegram Bot Token.
- `--url`: The full HTTPS URL where your bot is listening for updates (e.g., `https://your-cloud-run-url.a.run.app/webhook` or your ngrok URL).
- `--secret-token` (optional): A secret token that Telegram will send in the `X-Telegram-Bot-Api-Secret-Token` header with every update. Your bot should verify this token if you set it.

The script also supports reading these values from environment variables: `TELEGRAM_BOT_TOKEN`, `SERVICE_URL`, and `TELEGRAM_SECRET_TOKEN`.

## Project Structure

```
/
├── .github/                 # GitHub Actions workflows (CI, CD)
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml         # (To be added by Gemini_1)
├── bot/                     # Core bot application logic
│   ├── main.py                # FastAPI application and entry point (/, /webhook, /health)
│   ├── telegram_router.py     # Telegram message handling & command routing
│   ├── openai_client.py       # OpenAI API integration
│   ├── firestore_client.py    # Firebase Firestore database operations
│   ├── summarizer.py          # Conversation summarization with Gemini
│   ├── history_manager.py     # Manages history trimming and summarization
│   ├── error_middleware.py    # Global error handling middleware
│   └── retry_utils.py         # Utilities for API call retries
├── scripts/                   # Utility scripts
│   ├── set_webhook.py         # Script to register Telegram webhook
│   └── proactive_messages.py  # Universal proactive message scheduler
├── tests/                     # Automated tests
│   ├── test_health.py
│   ├── test_webhook_flow.py
│   ├── test_history_rotation.py
│   ├── test_proactive_schedule.py  # Proactive scheduler tests
│   └── test_container.py      # Docker container tests
├── config.py                  # Environment and configuration management
├── Dockerfile                 # Container definition for main bot service
├── Dockerfile.scheduler       # Container definition for proactive scheduler
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment variables template
└── .env                       # Actual environment variables (not committed)
```

## Deprecated Features

### Firebase Cloud Functions

Previously, Firebase Cloud Functions were considered for hosting the webhook. However, the project now exclusively uses Google Cloud Run for deployment, which provides a stable HTTPS endpoint. All Firebase Functions related code and configuration have been removed from the repository.

## Operational Monitoring

### Cloud Run Logging

The application uses structured JSON logging to enhance observability in Cloud Run:

- Error logs are formatted as JSON objects with detailed context
- Includes path, request method, exception type, and stack traces
- All failed operations with retries are logged with appropriate severity levels

### Recommended Alerts

For production deployments, consider setting up the following alerts:

1. **Error Rate Alert**
   - Trigger when log entries with severity=ERROR exceed 5 per minute
   - Indicates potential issues with API integrations or database operations

2. **5xx Response Alert**
   - Trigger when HTTP 5xx responses exceed 1% of total requests
   - Identifies potential application failures

3. **Retry Rate Alert**
   - Monitor for high volumes of retry attempts
   - Alert if successful operations after retries exceed 10% of total operations

### Resilience Features

The application includes several resilience mechanisms:

- Exponential backoff retries for all external API calls (Telegram, OpenAI, Firestore)
- Default retry configuration: 3 attempts with 1s, 2s, and 4s delays
- Global error middleware to ensure graceful failure handling
- Standardized error responses that maintain compatibility with Telegram's API 

<!-- Trigger CI/CD --> # Test deploy with all secrets configured
# Deploy test after billing fix - Sun May 25 14:10:55 WITA 2025
# Deploy test with  Actions budget - Sun May 25 14:13:03 WITA 2025
