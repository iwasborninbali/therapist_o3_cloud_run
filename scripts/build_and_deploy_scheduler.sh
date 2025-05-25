#!/bin/bash

# Build and deploy therapist-scheduler service
# This script builds the scheduler Docker image and deploys it to Cloud Run
# with the same configuration as the main bot service

set -e

PROJECT_ID="therapist-o3"
REGION="us-central1"
SERVICE_NAME="therapist-scheduler"
MAIN_SERVICE="therapist-o3"
SERVICE_ACCOUNT="therapist-o3-service@therapist-o3.iam.gserviceaccount.com"
REPOSITORY="cloud-run-source-deploy"

echo "🚀 Starting therapist-scheduler deployment..."

# Generate unique tag
TAG=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:${TAG}"
LATEST_IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:latest"

echo "📦 Building Docker image..."
docker build --platform linux/amd64 -f Dockerfile.scheduler -t "${IMAGE_NAME}" -t "${LATEST_IMAGE}" .

echo "📤 Pushing image to Artifact Registry..."
docker push "${IMAGE_NAME}"
docker push "${LATEST_IMAGE}"

echo "🔧 Getting environment variables from main service..."
# Extract environment variables from the main service
ENV_VARS=$(gcloud run services describe ${MAIN_SERVICE} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(spec.template.spec.template.spec.containers[0].env[].name,spec.template.spec.template.spec.containers[0].env[].value)" \
  | paste -d= - - | tr '\n' ',' | sed 's/,$//')

echo "🚀 Deploying scheduler service..."
gcloud run deploy ${SERVICE_NAME} \
  --image="${IMAGE_NAME}" \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --service-account="${SERVICE_ACCOUNT}" \
  --min-instances=1 \
  --no-allow-unauthenticated \
  --set-env-vars="${ENV_VARS}"

echo "✅ Scheduler deployed successfully!"

# Get service URL (internal)
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(status.url)")

echo "📋 Service Details:"
echo "  Name: ${SERVICE_NAME}"
echo "  Image: ${IMAGE_NAME}"
echo "  URL: ${SERVICE_URL} (internal only)"
echo "  Service Account: ${SERVICE_ACCOUNT}"
echo "  Min Instances: 1"

echo "🎉 Deployment complete! Scheduler should start running within 1-2 minutes."
echo "📊 Check logs with: gcloud logs read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --project=${PROJECT_ID}" 