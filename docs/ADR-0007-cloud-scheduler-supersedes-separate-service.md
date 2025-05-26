# ADR-0007: Cloud Scheduler Supersedes Separate Service

**Status**: Accepted  
**Date**: 2025-05-26  
**Supersedes**: [ADR-0003](ADR-0003-scheduler-as-separate-service.md)

## Context

The initial implementation used a separate Cloud Run service (`therapist-scheduler`) running continuously with `min-instances=1` to handle proactive message scheduling. This approach had several drawbacks:

1. **Cost**: Always-on service incurred continuous charges even during idle periods
2. **Complexity**: Two services to maintain, deploy, and monitor
3. **Timing Precision**: Interval-based checking (every 5 minutes) could miss exact timing windows
4. **Resource Waste**: Dedicated container running 24/7 for periodic tasks

## Decision

We will replace the separate scheduler service with **Cloud Scheduler HTTP triggers** that call a dedicated endpoint on the main bot service.

### New Architecture

```
┌─────────────────────┐    ┌──────────────────────┐
│   therapist-o3      │    │  Cloud Scheduler     │
│   (Main Bot)        │◄───┤  (Proactive Triggers)│
├─────────────────────┤    ├──────────────────────┤
│ • FastAPI webhook   │    │ • 4 scheduled jobs   │
│ • /admin/send-      │    │ • 10:00 & 20:00      │
│   proactive endpoint│    │ • Bali & Moscow TZ   │
│ • Scales to zero    │    │ • HTTP POST triggers │
│ • 1GB RAM, 1 CPU    │    │ • OIDC authentication│
└─────────────────────┘    └──────────────────────┘
```

### Implementation Details

1. **HTTP Endpoint**: `POST /admin/send-proactive?timezone={tz}&slot={morning|evening}`
2. **Cloud Scheduler Jobs**: Four jobs for precise timing:
   - `bali-morning`: 10:00 Asia/Makassar
   - `bali-evening`: 20:00 Asia/Makassar  
   - `moscow-morning`: 10:00 Europe/Moscow
   - `moscow-evening`: 20:00 Europe/Moscow
3. **Authentication**: OIDC service account for secure communication
4. **Parallel Processing**: ThreadPoolExecutor for efficient message generation

## Consequences

### Positive

- **Cost Reduction**: No always-on service charges
- **Improved Precision**: Exact timing via Cloud Scheduler cron expressions
- **Simplified Architecture**: Single service to maintain
- **Better Performance**: Parallel processing vs sequential
- **Enhanced Reliability**: Google-managed scheduling vs custom interval logic
- **Easier Debugging**: Centralized logs in main service

### Negative

- **External Dependency**: Relies on Cloud Scheduler service availability
- **Setup Complexity**: Initial configuration of 4 scheduler jobs required

### Neutral

- **Functionality**: Same user experience and message delivery
- **Deduplication**: Continues using Firestore `proactive_meta` collection

## Implementation Status

- ✅ HTTP endpoint implemented and tested (11 test cases passing)
- ✅ Cloud Scheduler jobs created and active
- ✅ Separate scheduler service removed
- ✅ Documentation updated
- ✅ Production deployment completed

## Monitoring

Monitor Cloud Scheduler job execution via:
- Cloud Scheduler console for job status
- Cloud Run logs for endpoint execution
- Firestore `proactive_meta` for delivery tracking

## Related Documents

- [ADR-0003](ADR-0003-scheduler-as-separate-service.md) - Superseded approach
- [Task 14](../dev_helpers/tasks/gemini_1/14_proactive_http_endpoint.md) - HTTP endpoint implementation
- [Task 15](../dev_helpers/tasks/gemini_1/15_scheduler_cleanup.md) - Service cleanup 