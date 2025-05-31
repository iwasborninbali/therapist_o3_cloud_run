# Task 16: Tool Calling Notes Implementation

**Status**: done  
**Assignee**: gemini_1  
**Created**: 2025-05-26  

## Objective
Implement tool calling functionality for therapist notes using a dedicated Tools Manager layer with safe user_id injection.

## Context
- User wants therapist AI to autonomously update notes per user
- o3 recommended thin "Tools Manager" layer outside core OpenAI wrapper
- User ID and timestamp injected server-side to prevent model manipulation
- Feature flag controlled (ENABLE_TOOL_CALLING) for safe rollout

## Architecture (per o3)
```
OpenAI Response → Tools Manager → Firestore
     ↓              ↓               ↓
tool_calls → dispatch() → add_note(user_id, content, ts)
```

## Files to Create/Modify

### 1. bot/tools_manager.py ✅
- Registry of tool specs for OpenAI
- Dispatcher logic with user_id & timestamp injection
- Register "update_notes" tool with schema {note_content: str}

### 2. bot/firestore_client.py ✅
- Add `add_note(user_id, content, ts, created_by="therapist_ai")`
- New collection `notes` operations

### 3. bot/openai_client.py ✅
- Extend `get_response()` to handle tool_calls
- Tools enabled only when `Config.ENABLE_TOOL_CALLING=true`
- Return "Noted." or original content after tool execution

### 4. bot/telegram_router.py ✅
- Pass `enable_tools` flag and `user_id` to OpenAI client
- Minimal changes to existing flow

### 5. config.py ✅
- Add `ENABLE_TOOL_CALLING` env var (default False)

### 6. tests/test_update_notes_tool.py ✅
- Unit test dispatcher injection logic
- Mock Firestore, assert correct fields added
- Test tool calling flow end-to-end

### 7. project_manifest.json ✅
- Add tools_manager module
- Add notes collection

## Firestore Schema
```json
{
  "user_id": "123456789",
  "content": "Therapist note content",
  "timestamp": "2025-05-26T10:00:00Z", 
  "created_by": "therapist_ai"
}
```

## Safety Measures
- **Feature Flag**: Disabled by default
- **User ID Injection**: Server-side, model cannot manipulate
- **Validation**: Input sanitization in dispatcher
- **Isolation**: New collection, separate module
- **Logging**: All tool executions logged

## Acceptance Criteria
- [x] Tools manager implemented with registry pattern
- [x] Firestore add_note function working
- [x] OpenAI client handles tool_calls properly
- [x] Feature flag controls tool availability
- [x] All tests passing (including new tool tests)
- [x] No impact on existing functionality when disabled
- [x] Code quality checks passing

## Testing Strategy
1. **Unit Tests**: Mock tool calls, test injection logic
2. **Integration Tests**: Real Firestore with test collection
3. **Manual Testing**: Enable flag, verify notes creation
4. **Rollback Plan**: Disable flag if issues arise

## Related
- Implements: Tool calling architecture per o3 consultation
- Prepares: For gemini_2 documentation task 09 