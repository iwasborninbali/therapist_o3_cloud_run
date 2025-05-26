# ADR-0005: Defer Cloud Build Trigger; Keep Manual Deploy Scripts

## Status
Accepted

## Context
The therapist bot project requires deployment of two Cloud Run services:
1. `therapist-o3` - Main bot service (FastAPI webhook handler)
2. `therapist-scheduler` - Proactive message scheduler service

Initially, we considered implementing automated CI/CD via Cloud Build triggers to deploy both services automatically on git push to main branch. The existing `cloudbuild.yaml` already contains the necessary steps for building and deploying both services.

## Decision
We will defer implementing Cloud Build trigger automation and continue using manual deployment scripts for the following reasons:

### Options Considered
1. **GitHub Actions** - External CI/CD with workflow files in `.github/workflows/`
2. **Cloud Build Trigger** - Native GCP solution triggering on git push via `cloudbuild.yaml`
3. **Manual Deployment** - Current approach using `scripts/build_and_deploy*.sh`

### Rationale for Manual Deployment
- **Project Scale**: This is a small-scale project with infrequent releases
- **Complexity vs. Benefit**: Manual deployment provides sufficient control without additional infrastructure complexity
- **Previous Attempts**: Auto-deploy attempts have been unsuccessful, indicating setup complexity
- **Team Preference**: Development team prefers manual control over deployment timing
- **Resource Efficiency**: Avoids additional GCP service configuration and maintenance

## Consequences

### Positive
- **Lower Complexity**: No additional CI/CD infrastructure to maintain
- **Deployment Control**: Manual verification before each deployment
- **Cost Efficiency**: No Cloud Build trigger usage costs
- **Immediate Implementation**: No setup time required

### Negative
- **Manual Effort**: Requires manual execution of deployment scripts
- **Human Error Risk**: Potential for deployment mistakes or forgotten steps
- **No Automatic Testing**: No automated testing pipeline on code changes

### Mitigation
- Maintain comprehensive deployment scripts (`build_and_deploy.sh`, `build_and_deploy_scheduler.sh`)
- Document deployment procedures in README.md
- Consider revisiting automation when release frequency increases

## Implementation
- Continue using existing manual deployment scripts
- Update documentation to reflect manual deployment approach
- Cancel/close any open Cloud Build trigger tasks

## Review Criteria
This decision should be revisited when:
- Release frequency increases significantly (>1 deployment per week)
- Team size grows requiring more deployment coordination
- Deployment errors become frequent due to manual process
- Project complexity requires automated testing pipeline 