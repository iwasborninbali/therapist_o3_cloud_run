# ADR-0001: Initial Architecture for Telegram AI Assistant

## Status
Accepted

## Context
We are developing a Telegram bot that will interact with users, maintain conversation context, and use AI to generate responses. The bot needs to be containerized for deployment on Google Cloud Run and store user conversation history in Firebase Firestore. Previously, Firebase Cloud Functions were considered for the webhook, but we have decided to use Google Cloud Run exclusively for a unified deployment strategy.

## Decision
We will implement the following architecture:

1. **Telegram Integration**
   - Use the `python-telegram-bot` library to handle Telegram webhook integration
   - Implement a FastAPI application that will receive webhook events from Telegram
   - Process user messages and send AI-generated responses back to users

2. **Firebase Firestore Integration**
   - Store conversation history by user ID (Telegram user ID)
   - Maintain separate collections for:
     - `history`: Store full conversation messages with timestamps
     - `summaries`: Store summarized conversation parts when history gets too long
     - `system_prompts`: Store user-specific system prompts

3. **OpenAI Integration**
   - Use the OpenAI API with the 'o3' model to generate AI responses
   - Pass full conversation history to maintain context in conversations
   - Include system prompts and any summaries in the requests

4. **Gemini Integration**
   - Use the Gemini 2.5 Pro model for conversation summarization
   - Implement a rotating summary mechanism to prevent context overflow

5. **Containerization and Deployment**
   - Package the application in a Docker container
   - Deploy to Google Cloud Run for serverless operation
   - Expose a health check endpoint for monitoring

## Consequences
1. **Positive**
   - Serverless deployment minimizes operational overhead
   - Separation of concerns with modular design
   - Efficient handling of conversation history through summarization
   - User-specific system prompts allow for personalized interactions

2. **Negative**
   - Reliance on multiple third-party APIs (Telegram, OpenAI, Gemini)
   - Potential cost implications for high usage
   - Need to carefully manage API rate limits

## Implementation Notes

### Project Structure
```
/
├── bot/
│   ├── main.py              # FastAPI application and entry point
│   ├── telegram_router.py   # Telegram message handling
│   ├── openai_client.py     # OpenAI API integration
│   ├── firestore_client.py  # Firestore database operations
│   └── summarizer.py        # Conversation summarization with Gemini
├── config.py                # Environment and configuration management
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── .env.example             # Example environment variables
```

### Local Development and Testing
To build and run the application locally:

```bash
# Build the Docker image
docker build -t telegram-ai-assistant .

# Run the container locally
docker run -p 8080:8080 --env-file .env telegram-ai-assistant
```

### Code Style
For this internal project, strict adherence to line length and certain other cosmetic flake8 rules (E501, W291, W293, F401) is deprioritized to speed up development. These are ignored via `setup.cfg`. Critical security and functional checks remain enforced.

### Deployment to Google Cloud Run
The application will be deployed to Google Cloud Run using the following steps:

1. Build and push the Docker image to Google Container Registry or Artifact Registry.
2. Deploy the container to Cloud Run with appropriate environment variables.
3. Set up a Telegram webhook to point to the Cloud Run service URL. Firebase Cloud Functions will not be used for any part of the webhook or application logic; all related code and configuration have been removed. 