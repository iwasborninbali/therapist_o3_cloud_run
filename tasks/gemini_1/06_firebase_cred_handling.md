---
id: 06_firebase_cred_handling
title: Implement Firebase Credential Handling Hotfix
status: done
assignee: gemini_1
owns_files:
  - config.py
  - README.md
  - docs/ADR-0002-cloud-run-deploy.md
  - Dockerfile # (if needed)
  - tests/conftest.py
---

## Task Description

Implement a hotfix to handle Firebase credentials passed as a JSON string via the `FIREBASE_CRED_JSON` environment variable. This will allow the application to correctly initialize Firebase when deployed to Cloud Run, where credentials might be provided as a string rather than a file path.

## Sub-tasks

1.  **Modify `config.py`:**
    *   At the beginning of the script (e.g., before `load_dotenv` or where `GOOGLE_APPLICATION_CREDENTIALS` is first processed):
        *   Check if the `FIREBASE_CRED_JSON` environment variable is set and contains a non-empty string.
        *   Check if `GOOGLE_APPLICATION_CREDENTIALS` environment variable is *not* set or is empty.
        *   If both conditions are true:
            *   Define a temporary file path (e.g., `/tmp/firebase_service_account.json` for general environments, or consider `/workspace/firebase_service_account.json` if that's a known writable path in Cloud Run).
            *   Write the content of `FIREBASE_CRED_JSON` to this temporary file.
            *   Set `os.environ["GOOGLE_APPLICATION_CREDENTIALS"]` to this temporary file path.
            *   Log an informational message (e.g., `logging.info("Firebase credentials from FIREBASE_CRED_JSON written to /tmp/firebase_service_account.json and GOOGLE_APPLICATION_CREDENTIALS set.")`).
    *   Ensure that existing logic for `GOOGLE_APPLICATION_CREDENTIALS` (if it's already set to a valid file path) still works.
    *   The `validate()` function in `config.py` should still pass if `FIREBASE_CRED_JSON` is not set (as in tests).

2.  **Update `tests/conftest.py`:**
    *   In any relevant fixtures (or globally at the start of the test session if appropriate), ensure `FIREBASE_CRED_JSON` is explicitly set to an empty string (`""`) or unset. This ensures that during unit/integration tests, the credential writing logic in `config.py` is not triggered if tests rely on patching or mock credentials, preventing attempts to write to the filesystem during tests unless specifically intended.

3.  **Update `README.md`:**
    *   Document the new `FIREBASE_CRED_JSON` environment variable in the environment setup section.
    *   Briefly explain how it's used by the CI/CD pipeline for Cloud Run deployments.

4.  **Update `docs/ADR-0002-cloud-run-deploy.md`:**
    *   Mention the `FIREBASE_CRED_JSON` environment variable as the method for supplying Firebase credentials in the Cloud Run deployment.
    *   Clarify that the application (via `config.py`) will handle writing this to a temporary file path for the Firebase Admin SDK.

5.  **Review `Dockerfile` (if needed):**
    *   Determine if any changes are needed. Ideally, with the `config.py` modification, no Dockerfile changes related to credential handling should be necessary, as the runtime will handle it.

6.  **Testing and Linting:**
    *   Run `pytest` to ensure all tests pass.
    *   Run `flake8 .` to ensure no linting errors.

## Acceptance Criteria

*   `config.py` correctly writes `FIREBASE_CRED_JSON` content to a temp file and sets `GOOGLE_APPLICATION_CREDENTIALS` when appropriate.
*   The application initializes Firebase correctly when `FIREBASE_CRED_JSON` is provided (tested implicitly via deployment).
*   Tests pass with `FIREBASE_CRED_JSON` unset or empty.
*   `README.md` and `ADR-0002-cloud-run-deploy.md` are updated to reflect the new credential handling.
*   No linting errors.
*   The solution works in a standard Python environment and in the Cloud Run environment. 