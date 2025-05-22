---
id: 05_cloud_run_ci_cd
title: Implement Cloud Run CI/CD Pipeline
status: done
assignee: gemini_1
owns_files:
  - .github/workflows/deploy.yml
  - README.md
  - docs/ADR-0002-cloud-run-deploy.md
---

## Task Description

Create a GitHub Actions workflow to automatically build and deploy the Docker container to Google Cloud Run on pushes to the `main` branch. This will enable a continuous deployment (CD) pipeline.

## Sub-tasks

1.  **Create `deploy.yml` GitHub Actions Workflow:**
    *   Trigger: On push to `main` branch.
    *   Job 1: Build and Push to Artifact Registry
        *   Authenticate to Google Cloud.
        *   Configure Docker authentication for Artifact Registry.
        *   Build the Docker image.
        *   Tag the image appropriately (e.g., with `us-central1-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE_NAME:$GITHUB_SHA`).
        *   Push the image to Google Artifact Registry (us-central1).
    *   Job 2: Deploy to Cloud Run
        *   Depends on Job 1.
        *   Authenticate to Google Cloud.
        *   Deploy the image from Artifact Registry to Cloud Run service named `TELEGRAM-AI`.
            *   Region: `us-central1`.
            *   Set `min-instances` to `0`.
            *   Allow unauthenticated invocations (or as per security requirements).
            *   Pass environment variables from GitHub Secrets (e.g., `TELEGRAM_TOKEN`, `OPENAI_API_KEY`, `FIREBASE_CRED_JSON`, `GEMINI_API_KEY`).
        *   Output the deployed service URL.
2.  **Create `ADR-0002-cloud-run-deploy.md`:**
    *   Document the decision to use GitHub Actions for CI/CD to Cloud Run.
    *   Explain the chosen workflow and rationale.
3.  **Update `README.md`:**
    *   Add a "Production Deployment" section.
    *   Explain the CD process (push to `main` triggers deployment).
    *   Include a deployment status badge for the `deploy.yml` workflow.

## Environment Variables (to be configured in GitHub Secrets)

*   `GCP_PROJECT_ID`: Google Cloud Project ID.
*   `GCP_SA_KEY`: Google Cloud Service Account Key (JSON).
*   `TELEGRAM_TOKEN`: Telegram Bot Token.
*   `OPENAI_API_KEY`: OpenAI API Key.
*   `FIREBASE_CRED_JSON`: Firebase Admin SDK Credentials (JSON string).
*   `GEMINI_API_KEY`: Gemini API Key.
*   `DOCKER_REGISTRY_REPO`: e.g. `telegram-ai-bot-repo`
*   `CLOUD_RUN_SERVICE_NAME`: e.g. `telegram-ai` (should be `TELEGRAM-AI` as per instructions)
*   `CLOUD_RUN_REGION`: e.g. `us-central1`

## Acceptance Criteria

*   Pushing to `main` branch successfully builds the Docker image and pushes it to Artifact Registry.
*   The image is then deployed to the specified Cloud Run service.
*   The Cloud Run service becomes accessible at the outputted URL.
*   The README is updated with the deployment section and badge.
*   The ADR is created and documents the CI/CD setup.
*   The `deploy.yml` workflow includes necessary steps for authentication, build, push, and deploy.
*   All necessary environment variables are passed to the Cloud Run service from GitHub Secrets.

## Notes and Dependencies

*   **`FIREBASE_CRED_JSON` Handling**: The current `deploy.yml` workflow passes the `FIREBASE_CRED_JSON` secret as an environment variable to Cloud Run. However, `config.py` expects `GOOGLE_APPLICATION_CREDENTIALS` to be a file path. This requires a coordinated change:
    *   Either `config.py` must be updated to read Firebase credentials directly from an environment variable string if `GOOGLE_APPLICATION_CREDENTIALS` is not a valid path.
    *   Or, the `Dockerfile` must be updated to take the `FIREBASE_CRED_JSON` string (e.g., via a build argument or an environment variable available at build time) and write its content to a file within the image, and then `GOOGLE_APPLICATION_CREDENTIALS` env var in Cloud Run must point to this path.
    *   This task assumes the `FIREBASE_CRED_JSON` string passed as an env var will be correctly handled by the application runtime or a subsequent setup step.
*   **GCP Service Account Permissions**: The service account key provided in `GCP_SA_KEY` must have the following roles in GCP:
    *   `roles/artifactregistry.writer` (Artifact Registry Writer) - to push images.
    *   `roles/run.admin` (Cloud Run Admin) - to deploy and manage the service.
    *   `roles/iam.serviceAccountUser` (Service Account User) - if Cloud Run service uses a specific runtime service identity.
*   The `scripts/set_webhook.py` (developed by Gemini_2) is expected to be present and executable with Python, taking `TELEGRAM_TOKEN` and `SERVICE_URL` as environment variables. 