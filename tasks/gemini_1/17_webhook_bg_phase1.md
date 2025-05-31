# Task 17: Webhook Background Processing (Phase 1)

**Status**: done  
**Priority**: high  
**Assigned**: gemini_1  
**Due**: immediate

## Objective
Implement immediate webhook acknowledgment with background processing and idempotency to eliminate Telegram timeout issues and duplicate messages.

## Context
Currently facing issues where tool calling takes 20-30 seconds, causing:
- Telegram webhook timeouts (expects response in 5-15 seconds)
- System retry sending 2-3 identical messages
- Poor user experience

## Solution
Phase 1: Background Tasks + Idempotency
- Change `/webhook` endpoint to return HTTP 200 immediately
- Process messages via FastAPI BackgroundTask  
- Add Firestore-backed deduplication using `update_id`

## Files to Modify
- bot/main.py
- bot/telegram_router.py
- bot/firestore_client.py
- tests/test_webhook_flow.py
- tests/test_webhook_dedup.py (new)
- config.py
- README.md
- project_manifest.json

## Sub-tasks
1. **bot/main.py**: Change `/webhook` handler to return HTTP 200 immediately and invoke `handle_update` via `BackgroundTask`
2. **bot/telegram_router.py**: Split out `handle_update(update)` that calls existing message logic
3. **bot/firestore_client.py**: Add `has_processed_update(update_id)` and `mark_update_processed(update_id)` using new `processed_updates` collection
4. **Background flow**: Skip if `has_processed_update`; else `mark_update_processed` then proceed
5. **tests/test_webhook_dedup.py**: Simulate duplicate `update_id` payloads → assert only first is handled
6. **tests/test_webhook_flow.py**: Update to expect 200 OK without delay
7. **config.py**: Document env var `IDEMPOTENCY_COLLECTION=processed_updates`
8. **README.md**: Update with new webhook architecture
9. Run lint and pytest

## Expected Outcome
- Webhook responds in ≤100ms
- No duplicate messages from Telegram retries
- Existing functionality preserved
- Clean test suite

## Testing Strategy
- Test duplicate update_id handling
- Test background processing works correctly
- Verify webhook response time
- Confirm no message loss

## Dependencies
None - standalone implementation

## Risk Mitigation
- Preserve existing message handling logic
- Add comprehensive tests before deployment
- Phase approach reduces complexity 