#!/bin/bash

# Build and deploy script for Cloud Run
# This script runs pre-deployment tests and then builds and deploys the Docker image

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
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REGISTRY_REPO}/therapist-bot"

echo -e "${BLUE}🚀 Starting deployment pipeline for Cloud Run${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}${NC}"
echo -e "${BLUE}Service: ${SERVICE_NAME}${NC}"
echo -e "${BLUE}Region: ${REGION}${NC}"
echo ""

# Step 1: Run pre-deployment validation
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}🧪 STEP 1: Pre-deployment validation${NC}"
echo -e "${BLUE}===========================================${NC}"

# Check if test script exists
if [ ! -f "scripts/test_before_deploy.sh" ]; then
    echo -e "${RED}❌ Pre-deployment test script not found: scripts/test_before_deploy.sh${NC}"
    exit 1
fi

# Run the pre-deployment tests
if ! ./scripts/test_before_deploy.sh; then
    echo -e "${RED}❌ Pre-deployment tests failed!${NC}"
    echo -e "${RED}🛑 Aborting deployment to prevent issues${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Pre-deployment validation passed!${NC}"
echo ""

# Step 2: Check gcloud prerequisites
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}⚙️  STEP 2: Checking Cloud prerequisites${NC}"
echo -e "${BLUE}===========================================${NC}"

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

echo -e "${GREEN}✅ Cloud prerequisites ready!${NC}"
echo ""

# Step 3: Build and push
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}🔨 STEP 3: Building and pushing image${NC}"
echo -e "${BLUE}===========================================${NC}"

# Build Docker image
echo -e "${BLUE}🔨 Building Docker image...${NC}"
docker build --platform linux/amd64 -t ${IMAGE_NAME}:latest .

# Push image to Artifact Registry
echo -e "${BLUE}📤 Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_NAME}:latest

echo -e "${GREEN}✅ Image built and pushed successfully!${NC}"
echo ""

# Step 4: Deploy to Cloud Run
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}🚀 STEP 4: Deploying to Cloud Run${NC}"
echo -e "${BLUE}===========================================${NC}"

# Deploy to Cloud Run (image only, preserving existing environment variables)
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME}:latest \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=80 \
    --memory=1Gi \
    --cpu=1

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""

# Step 5: Final summary
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}🎉 DEPLOYMENT SUMMARY${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}✅ Pre-deployment tests: PASSED${NC}"
echo -e "${GREEN}✅ Docker build: SUCCESS${NC}"
echo -e "${GREEN}✅ Image push: SUCCESS${NC}"
echo -e "${GREEN}✅ Cloud Run deploy: SUCCESS${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}📝 Environment variables: PRESERVED${NC}"
echo ""
echo -e "${BLUE}🔍 To check logs: ./scripts/check_logs.sh${NC}"
echo -e "${BLUE}🌐 Test webhook: curl ${SERVICE_URL}${NC}" 