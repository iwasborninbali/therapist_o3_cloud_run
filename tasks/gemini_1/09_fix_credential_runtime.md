# Task: Fix Credential Runtime Issues

**Status**: in-progress  
**Assignee**: gemini_1  
**Priority**: high  
**Type**: security-fix

## Description
Complete the credential cleanup by removing the leaked file, fixing config fallbacks, and ensuring FIREBASE_CRED_JSON is always passed to Cloud Run.

## Requirements
- Delete ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json from repo
- Remove hard-coded fallback path from config.py
- Always pass FIREBASE_CRED_JSON even with --skip-env-vars
- Update CI guards and documentation
- Ensure tests work with new credential system

## Sub-tasks
- [ ] Delete ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json from repo/history
- [ ] Update .gitignore/.dockerignore with *firebase*adminsdk*.json pattern
- [ ] Fix config.py to remove /app/firebase-service-account-key.json fallback
- [ ] Update scripts/local_deploy.sh to always pass FIREBASE_CRED_JSON
- [ ] Update CI guards in deploy.yml
- [ ] Update README & ADR-0002 credential handling documentation
- [ ] Fix tests/conftest.py for new credential system
- [ ] Run pytest + lint, self-review, commit

## Files to modify
- ales-f75a1-firebase-adminsdk-fbsvc-e008504e79.json (DELETE)
- .gitignore
- .dockerignore
- config.py
- scripts/local_deploy.sh
- .github/workflows/deploy.yml
- README.md
- docs/ADR-0002-security.md
- tests/conftest.py

## Acceptance Criteria
- No credential files in repository
- Config uses only FIREBASE_CRED_JSON or GOOGLE_APPLICATION_CREDENTIALS
- Deployment always passes FIREBASE_CRED_JSON
- All tests pass
- Bot can store/retrieve Firebase data
- CI guards prevent credential leaks 