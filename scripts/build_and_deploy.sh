#!/bin/bash

# Build and deploy script for Cloud Run
# This script only builds and deploys the Docker image without updating environment variables

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="therapist-o3"
REGION="us-central1"
SERVICE_NAME="therapist-o3"
REGISTRY_REPO="cloud-run-source-deploy"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REGISTRY_REPO}/${SERVICE_NAME}"

echo -e "${BLUE}🔨 Starting build and deploy to Cloud Run${NC}"
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
docker build --platform linux/amd64 -t ${IMAGE_NAME}:latest .

# Push image to Artifact Registry
echo -e "${BLUE}📤 Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run (image only, preserving existing environment variables)
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME}:latest \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=0

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

echo -e "${GREEN}✅ Build and deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}📝 Environment variables preserved from previous deployment${NC}" 