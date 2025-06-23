#!/bin/bash

# Simple streaming logs for Cloud Run service
set -e

# Colors for output
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ales-f75a1"
REGION="us-central1"
SERVICE_NAME="therapist-o3"

echo -e "${BLUE}🔴 STREAMING LOGS for ${SERVICE_NAME}${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}, Region: ${REGION}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Stream logs directly from Cloud Run service
gcloud beta run services logs tail ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} 