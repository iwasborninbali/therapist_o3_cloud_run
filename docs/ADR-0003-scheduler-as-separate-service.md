# ADR-0003: Keep Proactive Scheduler in a Dedicated Cloud Run Service

**Status**: Superseded by ADR-0007  
**Date**: 2025-05-25  
**Deciders**: o3, gemini_1

> **Note**: This ADR has been superseded by ADR-0007: Cloud Scheduler Supersedes Separate Service. The separate scheduler service approach was replaced with Cloud Scheduler HTTP triggers for better cost efficiency and timing precision.  

## Context

The therapist bot needs to send proactive messages twice daily (morning/evening) based on user timezones. We evaluated several architectural options for implementing this scheduling functionality.

## Decision

We will keep the proactive message scheduler as a **separate Cloud Run service** (`therapist-scheduler`) rather than integrating it into the main webhook service or using external scheduling services.

## Options Considered

### Option 1: Single Container (Background Thread in FastAPI)
- **Pros**: Simpler deployment, single service to manage
- **Cons**: 
  - **Critical flaw**: Horizontal scaling creates multiple scheduler instances
  - Each new webhook container instance would start its own scheduler loop
  - Results in duplicate proactive messages to users
  - No resource isolation between webhook and scheduler workloads

### Option 2: Cloud Scheduler + Cloud Functions
- **Pros**: No always-on costs, serverless scaling
- **Cons**: 
  - Adds complexity with two additional GCP services
  - Cold start delays for time-sensitive messages
  - More complex IAM configuration
  - Still requires per-user timezone logic in Functions
  - Less control over execution environment

### Option 3: Separate Cloud Run Service (CHOSEN)
- **Pros**: 
  - **Prevents duplication**: Single always-on instance (min instances = 1)
  - **Resource isolation**: Custom CPU/RAM allocation for scheduler
  - **Scaling independence**: Webhook service can scale to zero when idle
  - **Simplicity**: Direct container deployment, no external dependencies
  - **Cost predictable**: Small always-on footprint (512MB RAM, 0.5 CPU)
- **Cons**: 
  - Small always-on cost (~$10-15/month)
  - Two services to manage instead of one

## Consequences

### Positive
- **No duplicate messages**: Guaranteed single scheduler instance
- **Optimal resource usage**: Webhook scales with demand, scheduler runs consistently
- **Clear separation of concerns**: Message handling vs. proactive scheduling
- **Easier debugging**: Isolated logs and metrics per service

### Negative
- **Always-on cost**: Small but constant resource consumption
- **Deployment complexity**: Two services in CI/CD pipeline

### Neutral
- **Monitoring**: Need to track health of both services
- **Configuration**: Environment variables managed per service

## Implementation Details

- **Main Service**: `therapist-o3` (FastAPI webhook handler)
  - Public endpoint, scales 0-10 instances
  - 1GB RAM, 1 CPU per instance
  
- **Scheduler Service**: `therapist-scheduler` (Python script)
  - Private service, min 1 instance always running
  - 512MB RAM, 0.5 CPU
  - Checks every 5 minutes via `PROACTIVE_CHECK_INTERVAL`

## Future Considerations

If proactive message traffic proves minimal, we can revisit Cloud Scheduler + Cloud Functions to eliminate always-on costs. However, the current solution provides the best balance of reliability, simplicity, and cost for our expected usage patterns. 