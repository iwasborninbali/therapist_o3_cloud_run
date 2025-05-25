# Task 11: Fix Proactive Scheduling

**Status**: done  
**Assigned**: gemini_1  
**Priority**: critical

## Problem
Duplicate proactive pings happen because the scheduler Cloud Run service runs scripts/proactive_messages.py with hard-coded timezone loops. Users get messages for both Bali and Moscow timezones.

## Solution
Implement universal scheduler with per-user timezone checking and Firestore deduplication.

## Sub-tasks

### 1. Update firestore_client.py
- [x] Add `get_last_proactive_meta(user_id) → dict`
- [x] Add `set_last_proactive_meta(user_id, slot, date_iso)`

### 2. Rewrite scripts/proactive_messages.py  
- [x] Replace schedule library with while-True loop + PROACTIVE_CHECK_INTERVAL
- [x] Per-user timezone checking logic
- [x] Deduplication using last_sent metadata
- [x] Remove hard-coded Bali/Moscow loops
- [x] Add proper logging

### 3. Update Dockerfile.scheduler
- [x] Verify CMD ["python", "scripts/proactive_messages.py"]

### 4. Update README.md
- [x] Document scheduler service and dedup logic

### 5. Add tests
- [x] Create tests/test_proactive_schedule.py
- [x] Mock datetime and Firestore for dedup testing

### 6. Quality checks
- [x] Run pytest & lint
- [x] Self-review with ask
- [x] Centralize constants in config.py
- [ ] Deploy and test

## Files to modify
- scripts/proactive_messages.py
- bot/firestore_client.py  
- Dockerfile.scheduler
- README.md
- tests/test_proactive_schedule.py 