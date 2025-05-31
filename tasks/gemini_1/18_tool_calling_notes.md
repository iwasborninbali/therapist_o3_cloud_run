# Task 18: Tool Calling Notes Implementation

**Status**: done  
**Priority**: high  
**Assigned**: gemini_1  
**Due**: immediate

## Objective
Implement dedicated ToolsManager module for AI function calling with therapist notes functionality, including proper validation, logging, and testing.

## Context
Need to enable AI to create therapist notes via function calling while maintaining security, validation, and proper architecture separation.

## Solution
Create dedicated bot/tools_manager.py module with:
- Tool registry and validation via pydantic
- Server-side context injection (user_id, timestamp)
- Integration with existing firestore_client.add_note()
- Feature flag gating and comprehensive testing

## Files to Modify
- bot/tools_manager.py (new)
- bot/openai_client.py
- bot/telegram_router.py
- config.py
- tests/test_tools_manager.py (new)
- tests/test_update_notes_tool.py (expand)
- project_manifest.json

## Sub-tasks
1. **config.py**: Add ENABLE_TOOL_CALLING (bool, default False)
2. **bot/tools_manager.py**: Create tool registry with "update_notes" tool
   - Schema: {note_content: str}
   - dispatch(name, args, ctx) with validation and enrichment
   - Server-side injection of user_id and UTC timestamp
   - Call firestore_client.add_note() with proper parameters
   - Standardized JSON result format
   - Comprehensive logging
3. **bot/openai_client.py**: Extend generate_response() for function calling
   - Handle finish_reason == "function_call"
   - Call tools_manager.dispatch() with user context
   - Append result to messages and re-invoke OpenAI
4. **bot/telegram_router.py**: Pass user_id context to OpenAI client
   - Enable tools only if Config.ENABLE_TOOL_CALLING is true
   - Pass context object with user_id
5. **tests/test_tools_manager.py**: Unit tests for tool registry
   - Test validation, dispatch, enrichment
   - Mock Firestore operations
6. **tests/test_update_notes_tool.py**: Integration tests
   - Success scenarios, validation errors, disabled flag
7. **project_manifest.json**: Add new module and config flag
8. Self-review, lint, pytest, commit

## Expected Outcome
- AI can create therapist notes via function calling
- Proper validation and security measures
- Feature flag allows safe rollout
- Comprehensive test coverage
- Clean architecture separation

## Testing Strategy
- Unit tests for ToolsManager components
- Integration tests with mock Firestore
- Validation error handling
- Feature flag behavior testing

## Security Considerations
- Pydantic validation for all inputs
- Server-side context injection prevents tampering
- Comprehensive logging for audit trail
- Feature flag for safe rollout

## Dependencies
- Existing firestore_client.add_note() function
- OpenAI function calling API
- Pydantic for validation 