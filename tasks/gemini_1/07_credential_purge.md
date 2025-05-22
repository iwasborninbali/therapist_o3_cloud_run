---
id: 07_credential_purge
title: Purge Leaked Firebase Credentials and Implement Safeguards
status: done
assignee: gemini_1
owns_files:
  - ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json
  - firebase.json
  - functions/
  - .gitignore
  - README.md
  - docs/ADR-0001-initial-architecture.md
  - .github/workflows/deploy.yml
  - .github/workflows/ci.yml # If the check is added to CI as well
---

## Task Description

A Firebase service account key (`ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json`) has been identified in the repository. This is a critical security vulnerability. This task involves removing the key, preventing future occurrences, and updating documentation.

**IMPORTANT SECURITY NOTE:** The leaked service account key (`ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json`) **MUST be rotated/revoked in the Google Cloud Console immediately** by a project administrator. This task only removes it from the repository; it does not mitigate the risk of the compromised key being used.

## Sub-tasks

1.  **Delete Leaked Credential File:**
    *   Delete the file `ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json` from the repository.

2.  **Delete Firebase Functions Artifacts:**
    *   Delete `firebase.json` from the repository.
    *   Delete the entire `functions/` directory from the repository.

3.  **Update `.gitignore`:**
    *   Add a rule to `.gitignore` to prevent `*-firebase-adminsdk*.json` files from being committed.
    *   Consider adding a more general rule like `*-sa.json` or `*.private.*json` if other naming conventions for service accounts are anticipated.
    *   Add rules to `.gitignore` to prevent `firebase.json` and `functions/` from being committed.

4.  **Amend `docs/ADR-0001-initial-architecture.md` (previously ADR-0002):**
    *   Update to reflect that Google Cloud Run is the exclusive deployment target and Firebase Functions are not used. Mention removal of related code/artifacts.
    *   Reinforce that credentials (like `FIREBASE_CRED_JSON` and `GCP_SA_KEY`) must *only* be supplied via GitHub Secrets for the CI/CD pipeline.
    *   Explicitly state that service account key files should never be committed to the repository.

5.  **Amend `README.md`:**
    *   Update the environment setup or security section to strongly advise against committing service account files.
    *   Reiterate that credentials for deployment are managed via GitHub Secrets.
    *   Update project description/structure to reflect exclusive use of Cloud Run and removal of Firebase Functions code/artifacts.

6.  **Add CI/CD Check for Service Account and Firebase Functions Artifacts:**
    *   Modify the `deploy.yml` workflow (and potentially `ci.yml` for broader coverage):
        *   Add a step that checks for the presence of any files matching patterns like `*adminsdk*.json` or `*-sa.json` in the repository.
        *   Add a step that checks for the presence of `firebase.json` or the `functions/` directory.
        *   This can be done using simple shell commands (e.g., `grep`, `ls`, `test -f`, `test -d`).
        *   The commands should be configured to search the entire repository but exclude the `.git` directory and fail the build if such files/directories are found.

7.  **Commit Changes:**
    *   Commit the deletion of the key file, the `.gitignore` update, documentation changes, and workflow modifications.

8.  **Testing:**
    *   Run `pytest` (should still pass as no core logic is changed).
    *   Run `flake8 .` (should still pass or have only pre-existing errors from other files).
    *   Manually verify that the CI/CD check would fail if a dummy `*-adminsdk*.json` file were present.

## Acceptance Criteria

*   The file `ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json` is removed from the repository history (note: `git filter-repo` or BFG would be needed for true history purge, this task focuses on current state and prevention).
*   `.gitignore` prevents future commits of `*-firebase-adminsdk*.json` files, `firebase.json`, and the `functions/` directory.
*   `ADR-0001-initial-architecture.md` (updated from ADR-0002) and `README.md` are updated with stricter guidance on credential management and reflect the removal of Firebase Functions.
*   The CI/CD pipeline (`deploy.yml` and optionally `ci.yml`) includes a step that fails the build if service account key files, `firebase.json`, or the `functions/` directory are detected.
*   The **IMPORTANT SECURITY NOTE** about rotating the leaked key in GCP is acknowledged and understood to be an external manual step.