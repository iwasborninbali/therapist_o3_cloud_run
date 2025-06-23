#!/bin/bash

# Script to set environment variables for Cloud Run service
# This script only updates environment variables without rebuilding/redeploying the image

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

echo -e "${BLUE}🔧 Setting environment variables for Cloud Run service${NC}"
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

# Check if Firebase credentials are available
if [ -z "${FIREBASE_CRED_JSON}" ]; then
    echo -e "${YELLOW}⚠️  FIREBASE_CRED_JSON not set, trying to read from file...${NC}"
    if [ -f "ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json" ]; then
        export FIREBASE_CRED_JSON=$(cat ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json | tr -d '\n' | sed 's/"/\\"/g')
        echo -e "${GREEN}✅ Loaded Firebase credentials from file${NC}"
    else
        echo -e "${RED}❌ Firebase credentials not found. Set FIREBASE_CRED_JSON or provide the JSON file.${NC}"
        exit 1
    fi
fi

# Check required environment variables
echo -e "${BLUE}🔍 Checking required environment variables...${NC}"

MISSING_VARS=()

if [ -z "${TELEGRAM_BOT_TOKEN}" ]; then
    MISSING_VARS+=("TELEGRAM_BOT_TOKEN")
fi

if [ -z "${OPENAI_API_KEY}" ]; then
    MISSING_VARS+=("OPENAI_API_KEY")
fi



if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "${RED}   - ${var}${NC}"
    done
    echo -e "${YELLOW}Please set these variables and run the script again.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required environment variables are set${NC}"

# Update environment variables
echo -e "${BLUE}🔧 Updating environment variables in Cloud Run...${NC}"

gcloud run services update ${SERVICE_NAME} \
    --region=${REGION} \
    --update-env-vars="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}" \
    --update-env-vars="OPENAI_API_KEY=${OPENAI_API_KEY}" \
    --update-env-vars="FIREBASE_PROJECT_ID=ales-f75a1"

echo -e "${GREEN}✅ Environment variables updated successfully!${NC}"

# Get service URL for webhook setup
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

# Set webhook
if [ -n "${TELEGRAM_BOT_TOKEN}" ]; then
    echo -e "${BLUE}🔗 Setting Telegram webhook...${NC}"
    python3 scripts/set_webhook.py --token "${TELEGRAM_BOT_TOKEN}" --url "${SERVICE_URL}"
    echo -e "${GREEN}✅ Webhook configured!${NC}"
else
    echo -e "${YELLOW}⚠️  TELEGRAM_BOT_TOKEN not set. Skipping webhook configuration.${NC}"
fi

echo -e "${GREEN}🎉 Environment variables setup completed!${NC}"
echo -e "${GREEN}📝 Service URL: ${SERVICE_URL}${NC}" 