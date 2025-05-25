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

# Parse command line arguments
UPDATE_ENV_VARS=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-env-vars)
            UPDATE_ENV_VARS=false
            shift
            ;;
        *)
            echo "Unknown option $1"
            echo "Usage: $0 [--skip-env-vars]"
            echo "  --skip-env-vars: Only update the image, keep existing environment variables"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 Starting local deployment to Cloud Run${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}${NC}"
echo -e "${BLUE}Service: ${SERVICE_NAME}${NC}"
echo -e "${BLUE}Region: ${REGION}${NC}"

if [ "$UPDATE_ENV_VARS" = false ]; then
    echo -e "${YELLOW}⚠️  Skipping environment variables update (using existing values)${NC}"
fi

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
docker build --platform linux/amd64 -t ${IMAGE_NAME}:latest .

# Push image to Artifact Registry
echo -e "${BLUE}📤 Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
if [ "$UPDATE_ENV_VARS" = true ]; then
    # Check if FIREBASE_CRED_JSON is set
    if [ -z "${FIREBASE_CRED_JSON}" ]; then
        echo -e "${YELLOW}⚠️  FIREBASE_CRED_JSON not set, trying to read from file...${NC}"
        if [ -f "ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json" ]; then
            export FIREBASE_CRED_JSON=$(cat ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json | tr -d '\n')
            echo -e "${GREEN}✅ Loaded Firebase credentials from file${NC}"
        else
            echo -e "${RED}❌ Firebase credentials not found. Set FIREBASE_CRED_JSON or provide the JSON file.${NC}"
            exit 1
        fi
    fi
    
    # Create temporary env vars file
    cat > /tmp/env_vars.txt << EOF
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
OPENAI_API_KEY=${OPENAI_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
FIREBASE_PROJECT_ID=${PROJECT_ID}
FIREBASE_CRED_JSON=${FIREBASE_CRED_JSON}
EOF
    
    gcloud run deploy ${SERVICE_NAME} \
        --image=${IMAGE_NAME}:latest \
        --region=${REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --min-instances=0 \
        --env-vars-file=/tmp/env_vars.txt
    
    # Clean up temp file
    rm -f /tmp/env_vars.txt
else
    # Even when skipping env vars, always pass Firebase credentials
    if [ -z "${FIREBASE_CRED_JSON}" ]; then
        echo -e "${YELLOW}⚠️  FIREBASE_CRED_JSON not set, trying to read from file...${NC}"
        if [ -f "new-firebase-key.json" ]; then
            export FIREBASE_CRED_JSON=$(cat new-firebase-key.json | tr -d '\n')
            echo -e "${GREEN}✅ Loaded Firebase credentials from file${NC}"
        else
            echo -e "${RED}❌ Firebase credentials not found. Set FIREBASE_CRED_JSON environment variable.${NC}"
            exit 1
        fi
    fi
    
    # Deploy image only, then update Firebase credentials separately
    gcloud run deploy ${SERVICE_NAME} \
        --image=${IMAGE_NAME}:latest \
        --region=${REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --min-instances=0
    
    # Update Firebase credentials using update-env-vars
    echo -e "${BLUE}🔧 Updating Firebase credentials...${NC}"
    # Create temporary file for credentials
    echo "${FIREBASE_CRED_JSON}" > /tmp/firebase_creds.json
    gcloud run services update ${SERVICE_NAME} \
        --region=${REGION} \
        --update-env-vars="FIREBASE_CRED_JSON=$(cat /tmp/firebase_creds.json)"
    rm -f /tmp/firebase_creds.json
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"

# Set webhook
if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ "$UPDATE_ENV_VARS" = true ]; then
    echo -e "${BLUE}🔗 Setting Telegram webhook...${NC}"
    python3 scripts/set_webhook.py --token "${TELEGRAM_BOT_TOKEN}" --url "${SERVICE_URL}"
    echo -e "${GREEN}✅ Webhook configured!${NC}"
else
    if [ "$UPDATE_ENV_VARS" = false ]; then
        echo -e "${YELLOW}⚠️  Skipping webhook configuration (env vars not updated)${NC}"
    else
        echo -e "${YELLOW}⚠️  TELEGRAM_BOT_TOKEN not set. Skipping webhook configuration.${NC}"
    fi
fi

echo -e "${GREEN}🎉 Local deployment completed successfully!${NC}"
echo -e "${GREEN}📝 Service is running at: ${SERVICE_URL}${NC}" 