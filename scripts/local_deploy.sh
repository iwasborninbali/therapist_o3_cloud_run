#!/bin/bash

# Local deployment script for Cloud Run
# This script deploys the application directly from your local machine

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ales-f75a1"
REGION="us-central1"
SERVICE_NAME="therapist-o3"
REGISTRY_REPO="therapist-o3"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REGISTRY_REPO}/${SERVICE_NAME}"

echo -e "${BLUE}🚀 Starting local deployment to Cloud Run${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}${NC}"
echo -e "${BLUE}Service: ${SERVICE_NAME}${NC}"
echo -e "${BLUE}Region: ${REGION}${NC}"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  Not authenticated with gcloud. Running auth...${NC}"
    gcloud auth login
fi

# Set project
echo -e "${BLUE}📋 Setting project...${NC}"
gcloud config set project ${PROJECT_ID}

# Configure Docker for Artifact Registry
echo -e "${BLUE}🐳 Configuring Docker for Artifact Registry...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build Docker image
echo -e "${BLUE}🔨 Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:latest .

# Push image to Artifact Registry
echo -e "${BLUE}📤 Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME}:latest \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=0 \
    --set-env-vars="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}" \
    --set-env-vars="OPENAI_API_KEY=${OPENAI_API_KEY}" \
    --set-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY}" \
    --set-env-vars="FIREBASE_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars="FIREBASE_CRED_JSON=${FIREBASE_CRED_JSON}"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"

# Set webhook
if [ -n "${TELEGRAM_BOT_TOKEN}" ]; then
    echo -e "${BLUE}🔗 Setting Telegram webhook...${NC}"
    python3 scripts/set_webhook.py --token "${TELEGRAM_BOT_TOKEN}" --url "${SERVICE_URL}"
    echo -e "${GREEN}✅ Webhook configured!${NC}"
else
    echo -e "${YELLOW}⚠️  TELEGRAM_BOT_TOKEN not set. Skipping webhook configuration.${NC}"
fi

echo -e "${GREEN}🎉 Local deployment completed successfully!${NC}"
echo -e "${GREEN}📝 Service is running at: ${SERVICE_URL}${NC}" 