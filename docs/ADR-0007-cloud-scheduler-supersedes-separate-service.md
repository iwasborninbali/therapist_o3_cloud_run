# ADR-0007: Cloud Scheduler Supersedes Separate Service

## Status
Accepted

## Supersedes
ADR-0003: Keep Proactive Scheduler in a Dedicated Cloud Run Service

## Context
The proactive message system was initially implemented as a separate always-on Cloud Run service (`therapist-scheduler`) that continuously checked for users needing messages every 5 minutes. While functional, this approach had several drawbacks:

- **Resource Waste**: Always-on service with min-instances=1 consuming resources 24/7
- **Timing Imprecision**: 5-minute check intervals meant messages could be sent at 10:03 or 20:07 instead of exactly 10:00/20:00
- **Complexity**: Separate service requiring independent deployment and monitoring
- **Cost**: Continuous CPU/memory usage for infrequent operations (2 messages per user per day)

## Decision
We will transition to Cloud Scheduler HTTP triggers calling an endpoint on the main bot service.

### Options Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Always-on Service** (current) | Simple deployment, self-contained | Resource waste, timing imprecision, higher cost | ❌ Superseded |
| **Cloud Run Job** | Pay-per-execution, precise timing | Additional service type, more complex setup | ⚠️ Considered |
| **Cloud Scheduler HTTP** (chosen) | Precise timing, cost-efficient, simple | Requires endpoint implementation | ✅ **Adopted** |

### Implementation
- **HTTP Endpoint**: `/admin/send-proactive/{timezone}/{slot}` in main bot service
- **Cloud Scheduler Jobs**: 4 jobs targeting specific timezone/slot combinations:
  - `bali-morning`: 10:00 Asia/Makassar → `/admin/send-proactive/Asia/Makassar/morning`
  - `bali-evening`: 20:00 Asia/Makassar → `/admin/send-proactive/Asia/Makassar/evening`
  - `moscow-morning`: 10:00 Europe/Moscow → `/admin/send-proactive/Europe/Moscow/morning`
  - `moscow-evening`: 20:00 Europe/Moscow → `/admin/send-proactive/Europe/Moscow/evening`

## Consequences

### Positive
- **Precision**: Exact 10:00/20:00 timing instead of approximate
- **Cost Efficiency**: Pay-per-execution vs always-on service
- **Simplicity**: Single service architecture, fewer moving parts
- **Reliability**: Cloud Scheduler guarantees execution
- **Scalability**: Easy to add new timezones by creating additional jobs

### Negative
- **External Dependency**: Relies on Cloud Scheduler service
- **Setup Complexity**: Initial configuration of 4 scheduler jobs
- **Debugging**: Distributed execution across multiple scheduler jobs

### Mitigation
- **Monitoring**: Cloud Scheduler provides built-in monitoring and alerting
- **Idempotency**: Endpoint design prevents duplicate sends via Firestore deduplication
- **Fallback**: Manual endpoint invocation possible for testing/recovery

## Implementation Details

### Cloud Scheduler Configuration
```bash
# Create scheduler jobs
gcloud scheduler jobs create http bali-morning \
  --schedule="0 10 * * *" --time-zone="Asia/Makassar" \
  --uri="$BOT_URL/admin/send-proactive/Asia/Makassar/morning" \
  --oidc-service-account-email=therapist-o3-service@therapist-o3.iam.gserviceaccount.com

gcloud scheduler jobs create http bali-evening \
  --schedule="0 20 * * *" --time-zone="Asia/Makassar" \
  --uri="$BOT_URL/admin/send-proactive/Asia/Makassar/evening" \
  --oidc-service-account-email=therapist-o3-service@therapist-o3.iam.gserviceaccount.com

gcloud scheduler jobs create http moscow-morning \
  --schedule="0 10 * * *" --time-zone="Europe/Moscow" \
  --uri="$BOT_URL/admin/send-proactive/Europe/Moscow/morning" \
  --oidc-service-account-email=therapist-o3-service@therapist-o3.iam.gserviceaccount.com

gcloud scheduler jobs create http moscow-evening \
  --schedule="0 20 * * *" --time-zone="Europe/Moscow" \
  --uri="$BOT_URL/admin/send-proactive/Europe/Moscow/evening" \
  --oidc-service-account-email=therapist-o3-service@therapist-o3.iam.gserviceaccount.com
```

### Endpoint Response Format
```json
{
  "sent": 3,
  "skipped": 1,
  "timezone": "Asia/Makassar",
  "slot": "morning",
  "timestamp": "2025-05-25T10:00:00Z"
}
```

## Migration Plan
1. ✅ Implement HTTP endpoint in main service
2. ✅ Deploy updated main service
3. ✅ Create Cloud Scheduler jobs
4. ✅ Test one complete cycle (morning + evening)
5. ✅ Delete separate scheduler service
6. ✅ Remove obsolete files and documentation

## Review Criteria
This decision should be revisited if:
- Cloud Scheduler reliability becomes an issue
- Need for more complex scheduling logic emerges
- Cost of Cloud Scheduler jobs exceeds always-on service cost
- Additional timezone support requires >10 scheduler jobs 