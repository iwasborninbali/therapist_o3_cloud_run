#!/bin/bash

# Script to check Cloud Run logs for troubleshooting
set -e

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

echo -e "${BLUE}📋 Checking Cloud Run logs for service: ${SERVICE_NAME}${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}, Region: ${REGION}${NC}"

# Set project
gcloud config set project ${PROJECT_ID}

# Get logs for the last hour
echo -e "${BLUE}🔍 Getting logs for the last 4 hours...${NC}"
echo -e "${YELLOW}==================== LAST HOUR LOGS ====================${NC}"

FOUR_HOURS_AGO=$(date -u -v-4H '+%Y-%m-%dT%H:%M:%SZ')

gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND resource.labels.location=${REGION} AND timestamp>=\"${FOUR_HOURS_AGO}\"" \
--limit=50 \
--format="table(timestamp,severity,textPayload)" \
--project=${PROJECT_ID}

echo -e "${YELLOW}==================== ERROR LOGS ====================${NC}"

# Get error logs specifically
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND resource.labels.location=${REGION} AND severity>=ERROR AND timestamp>=\"${FOUR_HOURS_AGO}\"" \
--limit=20 \
--format="table(timestamp,severity,textPayload)" \
--project=${PROJECT_ID}

echo -e "${YELLOW}==================== WEBHOOK LOGS ====================${NC}"

# Get webhook-related logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND resource.labels.location=${REGION} AND textPayload:webhook AND timestamp>=\"${FOUR_HOURS_AGO}\"" \
--limit=20 \
--format="table(timestamp,severity,textPayload)" \
--project=${PROJECT_ID}

echo -e "${YELLOW}==================== TOOL CALLING LOGS ====================${NC}"

# Get tool calling logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND resource.labels.location=${REGION} AND (textPayload:tool OR textPayload:Tool) AND timestamp>=\"${FOUR_HOURS_AGO}\"" \
--limit=20 \
--format="table(timestamp,severity,textPayload)" \
--project=${PROJECT_ID}

echo -e "${GREEN}✅ Log check completed${NC}" 