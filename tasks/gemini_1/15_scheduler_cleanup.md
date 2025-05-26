# Task 15: Scheduler Service Cleanup

**Status**: in-progress  
**Assignee**: gemini_1  
**Created**: 2025-05-26  

## Objective
Remove obsolete separate scheduler service and related files after successful implementation of HTTP endpoint approach for proactive messages.

## Context
- ✅ Successfully implemented `/admin/send-proactive` endpoint in main service
- ✅ HTTP endpoint + Cloud Scheduler approach proven effective
- ❌ Separate `therapist-scheduler` service now redundant and costly

## Files to Delete
1. `scripts/proactive_messages.py` - old scheduler logic
2. `scripts/proactive_messages_with_server.py` - replaced by `bot/proactive.py`
3. `Dockerfile.scheduler` - no longer needed
4. `scripts/build_and_deploy_scheduler.sh` - no longer needed
5. `tests/test_proactive_schedule.py` - logic covered by endpoint tests

## Files to Update
1. `project_manifest.json` - remove scheduler modules
2. `README.md` - remove dual-service references
3. `.dockerignore` - remove Dockerfile.scheduler entry if present

## Acceptance Criteria
- [x] All obsolete files deleted
- [x] Project manifest updated
- [x] README updated to reflect single-service architecture
- [x] All tests passing (pytest) - 20/20 passed
- [x] Code quality checks passing (flake8) - no new issues
- [ ] Changes committed

## Benefits
- **Simplicity**: Single service instead of dual services
- **Cost**: No min-instances=1 always-on service
- **Maintenance**: Fewer moving parts
- **Precision**: Cloud Scheduler → HTTP endpoint more reliable

## Related
- Supersedes: ADR-0003 (separate scheduler service)
- Implements: HTTP endpoint approach from task 14 