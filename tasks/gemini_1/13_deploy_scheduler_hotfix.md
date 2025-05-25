# Task: Deploy Scheduler Hotfix

## Status: in-progress

## Description
Deploy therapist-scheduler service as a hotfix to restore proactive messaging functionality.

## Requirements
- Create build_and_deploy_scheduler.sh script
- Use same service account as main bot
- Copy environment variables from therapist-o3 service
- Deploy with min-instances=1
- Update documentation

## Owned Files
- scripts/build_and_deploy_scheduler.sh
- README.md
- project_manifest.json

## Implementation Plan
1. Create deployment script that:
   - Builds Docker image from Dockerfile.scheduler
   - Copies env vars from therapist-o3 service
   - Deploys with proper service account and settings
2. Update README.md with scheduler deployment section
3. Update project_manifest.json with new script entry
4. Self-review and commit

## Acceptance Criteria
- therapist-scheduler service deployed and running
- Service uses same service account as main bot
- Environment variables properly configured
- Documentation updated
- Code passes linting 