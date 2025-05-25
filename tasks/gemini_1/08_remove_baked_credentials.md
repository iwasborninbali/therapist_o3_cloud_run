# Task: Remove Baked Credentials from Docker Image

**Status**: in-progress  
**Assignee**: gemini_1  
**Priority**: high  
**Type**: security-fix

## Description
Remove Firebase service account credentials from Docker image and ensure they are only provided through environment variables at runtime, maintaining security ADRs.

## Requirements
- Remove any COPY of firebase-service-account-key.json from Dockerfiles
- Ensure image relies purely on env vars (no key artifacts)
- Update .dockerignore and .gitignore to block service account files
- Make FIREBASE_CRED_JSON mandatory in config.py
- Update deployment scripts to use env vars only
- Add CI guards to prevent credential files in build context

## Sub-tasks
- [ ] Dockerfile & Dockerfile.scheduler: Remove COPY of firebase-service-account-key.json
- [ ] .dockerignore & .gitignore: Add rules to block *service-account*key.json
- [ ] config.py: Make FIREBASE_CRED_JSON mandatory, remove baked file fallback
- [ ] scripts/local_deploy.sh: Always pass FIREBASE_CRED_JSON env var
- [ ] CI guard (deploy.yml): Fail if build context contains private_key in JSON
- [ ] README + ADR-0002: Document credential handling policy
- [ ] Run pytest to ensure no credential artifacts
- [ ] Self-review and commit changes

## Files to modify
- Dockerfile
- Dockerfile.scheduler  
- .dockerignore
- .gitignore
- config.py
- scripts/local_deploy.sh
- .github/workflows/deploy.yml
- README.md
- docs/ADR-0002-security.md

## Acceptance Criteria
- No Firebase credentials in Docker image layers
- Credentials only provided via FIREBASE_CRED_JSON environment variable
- CI fails if credentials detected in build context
- All tests pass
- Bot functions correctly with env-only credentials 