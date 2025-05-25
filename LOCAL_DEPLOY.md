# Local Deployment Guide

This guide explains how to deploy the application locally while GitHub Actions billing issues are resolved.

## Prerequisites

1. **Google Cloud CLI installed and configured:**
   ```bash
   # Install gcloud CLI if not already installed
   # https://cloud.google.com/sdk/docs/install
   
   # Authenticate with Google Cloud
   gcloud auth login
   
   # Set your project
   gcloud config set project ales-f75a1
   ```

2. **Docker installed and running**

3. **Environment variables set:**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   export OPENAI_API_KEY="your_openai_api_key"
   export GEMINI_API_KEY="your_gemini_api_key"
   export FIREBASE_CRED_JSON='{"type":"service_account",...}'
   ```

## Quick Deploy

1. **Set environment variables:**
   ```bash
   # Copy from your GitHub Secrets or .env file
   export TELEGRAM_BOT_TOKEN="your_token_here"
   export OPENAI_API_KEY="your_key_here"
   export GEMINI_API_KEY="your_key_here"
   export FIREBASE_CRED_JSON='your_firebase_json_here'
   ```

2. **Run deployment script:**
   ```bash
   ./scripts/local_deploy.sh
   ```

## What the script does:

1. ✅ Checks gcloud authentication
2. ✅ Builds Docker image
3. ✅ Pushes to Google Artifact Registry
4. ✅ Deploys to Cloud Run
5. ✅ Configures Telegram webhook
6. ✅ Outputs service URL

## Manual Steps (if script fails):

1. **Build and push image:**
   ```bash
   docker build -t us-central1-docker.pkg.dev/ales-f75a1/therapist-o3/therapist-o3:latest .
   docker push us-central1-docker.pkg.dev/ales-f75a1/therapist-o3/therapist-o3:latest
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy therapist-o3 \
     --image=us-central1-docker.pkg.dev/ales-f75a1/therapist-o3/therapist-o3:latest \
     --region=us-central1 \
     --platform=managed \
     --allow-unauthenticated \
     --set-env-vars="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}" \
     --set-env-vars="OPENAI_API_KEY=${OPENAI_API_KEY}" \
     --set-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY}" \
     --set-env-vars="FIREBASE_PROJECT_ID=ales-f75a1" \
     --set-env-vars="FIREBASE_CRED_JSON=${FIREBASE_CRED_JSON}"
   ```

3. **Set webhook:**
   ```bash
   python3 scripts/set_webhook.py --token "${TELEGRAM_BOT_TOKEN}" --url "https://your-service-url"
   ```

## Troubleshooting

- **Authentication issues:** Run `gcloud auth login`
- **Docker issues:** Make sure Docker is running
- **Permission issues:** Check your Google Cloud IAM permissions
- **Environment variables:** Make sure all required env vars are set

## GitHub Actions Status

Currently blocked due to GitHub account billing restrictions:
- Account is locked from purchases
- Need to contact GitHub Support: https://support.github.com
- Local deployment is the workaround until resolved 