# ADR-0002: Automated Cloud Run Deployment with GitHub Actions

Date: 2024-07-25 <!-- Filled in current date -->

## Status

Proposed

## Context

To enable live testing and continuous delivery for the Telegram AI Assistant, we need an automated way to deploy the application to a production-like environment. Google Cloud Run is the chosen platform for hosting the containerized application. A CI/CD pipeline is required to build the Docker image, push it to an image repository, and deploy it to Cloud Run whenever changes are merged to the main branch.

## Decision

We will use GitHub Actions to implement the CI/CD pipeline for deploying the Telegram AI Assistant to Google Cloud Run.

The pipeline will consist of a single workflow (`deploy.yml`) triggered on pushes to the `main` branch. This workflow will perform the following steps:

1.  **Authenticate with Google Cloud:** Use a service account key stored in GitHub Secrets to authenticate with Google Cloud.
2.  **Configure Docker:** Configure Docker to authenticate with Google Artifact Registry.
3.  **Build Docker Image:** Build the Docker image using the `Dockerfile` in the repository. The image will be tagged with the GitHub SHA to ensure unique versioning.
4.  **Push Docker Image:** Push the built image to a specified Google Artifact Registry repository (e.g., `us-central1-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE_NAME:$GITHUB_SHA`).
5.  **Deploy to Cloud Run:** Deploy the image from Artifact Registry to the `TELEGRAM-AI` Cloud Run service.
    *   The service will be located in the `us-central1` region.
    *   `min-instances` will be set to `0` for cost-efficiency.
    *   Necessary environment variables (e.g., API keys, tokens) will be passed from GitHub Secrets to the Cloud Run service. Specifically for Firebase, the `FIREBASE_CRED_JSON` secret (containing the full service account JSON string) will be passed. The application's `config.py` will then handle writing this JSON string to a temporary file path and setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to it for the Firebase Admin SDK to use. **It is critical that raw service account key files are never committed to the repository; all such credentials must be managed exclusively through GitHub Secrets.**
6.  **Webhook Re-registration:** After a successful deployment, a script (`scripts/set_webhook.py`) will be invoked to update the Telegram bot's webhook URL to point to the newly deployed Cloud Run service URL.

## Consequences

### Positive

*   **Automation:** Fully automates the build, push, and deployment process.
*   **Consistency:** Ensures deployments are performed consistently using the same process.
*   **Speed:** Enables rapid deployment of new features and bug fixes to the live environment.
*   **Version Control:** Image versions are tied to Git commits (via `$GITHUB_SHA`).
*   **Integrated Workflow:** Leverages GitHub Actions, keeping CI/CD within the same platform as the codebase.
*   **Secrets Management:** Utilizes GitHub Secrets for securely managing sensitive credentials. **Service account key files or other raw secrets must never be committed to the repository.**
*   **Automatic Webhook Updates:** Ensures the Telegram bot always points to the latest active deployment.

### Neutral

*   Requires initial setup and configuration of GitHub Actions workflow, Google Cloud resources (Artifact Registry, Cloud Run), and GitHub Secrets.
*   The `TELEGRAM-AI` Cloud Run service name is hardcoded.

### Negative

*   Reliance on GitHub Actions as a service. Downtime or issues with GitHub Actions could impact deployments.
*   Increased complexity in the repository with the addition of workflow files.

## Alternatives Considered

1.  **Manual Deployment:** Manually building and deploying the Docker image.
    *   Pros: Simpler initial setup.
    *   Cons: Prone to human error, time-consuming, not scalable, lacks consistency.
2.  **Google Cloud Build:** Using Cloud Build triggers for CI/CD.
    *   Pros: Tightly integrated with Google Cloud services.
    *   Cons: Might involve a steeper learning curve for developers primarily familiar with GitHub Actions; managing CI/CD in a separate platform from the codebase.
3.  **Other CI/CD Platforms (e.g., Jenkins, GitLab CI):**
    *   Pros: Potentially more features or flexibility depending on the platform.
    *   Cons: Adds another tool to the stack, requires separate setup and maintenance.

GitHub Actions was chosen due to its good integration with GitHub repositories, sufficient feature set for our needs, and existing familiarity within the team (as evidenced by the `ci.yml` for testing).

## Follow-up

*   Human will need to create the required Google Cloud resources (Artifact Registry repository, Cloud Run service stub if not already present) and configure the necessary GitHub Secrets (including `TELEGRAM_TOKEN`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `FIREBASE_CRED_JSON`, `GCP_SA_KEY`, `GCP_PROJECT_ID`, `DOCKER_REGISTRY_REPO`, `CLOUD_RUN_SERVICE_NAME`, `CLOUD_RUN_REGION`).
*   The `scripts/set_webhook.py` script (to be developed by Gemini_2) needs to be robust and handle potential errors during the webhook update process.
*   The README.md will be updated to document this deployment process. 