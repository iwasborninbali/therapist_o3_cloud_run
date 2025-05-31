"""
Tools Manager for OpenAI Function Calling

Provides a registry of available tools and dispatcher for safe execution
with server-side user_id and timestamp injection.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Callable, Optional

logger = logging.getLogger(__name__)


class ToolsManager:
    """Manages tool registration and execution for OpenAI function calling"""
    
    def __init__(self, firestore_client):
        self.firestore_client = firestore_client
        self._tools_registry: Dict[str, Dict[str, Any]] = {}
        self._function_handlers: Dict[str, Callable] = {}
        
        # Register available tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools with their schemas and handlers"""
        self._register_update_notes_tool()
    
    def _register_update_notes_tool(self):
        """Register the update_notes tool for therapist notes"""
        tool_spec = {
            "type": "function",
            "function": {
                "name": "update_notes",
                "description": "Записать заметку ДЛЯ СЕБЯ о клиенте. Этот инструмент позволяет тебе сохранять важную информацию о клиенте, которую ты будешь видеть при каждом следующем разговоре. Используй только для записи НОВОЙ или ОБНОВЛЕННОЙ информации. НЕ дублируй уже существующие заметки. Записывай: ключевые инсайты, прогресс терапии, важные жизненные события, цели клиента, паттерны поведения.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_content": {
                            "type": "string",
                            "description": "Содержание заметки для записи. Должно быть уникальным и не дублировать уже существующие заметки. Записывай только новую или обновленную информацию о клиенте."
                        }
                    },
                    "required": ["note_content"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
        
        self._tools_registry["update_notes"] = tool_spec
        self._function_handlers["update_notes"] = self._handle_update_notes
        
        logger.info("Registered update_notes tool")
    
    def get_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Get list of tool specifications for OpenAI API"""
        return list(self._tools_registry.values())
    
    def dispatch_tool_calls(self, tool_calls: List[Dict[str, Any]], user_id: str) -> List[str]:
        """
        Execute tool calls with server-side user_id injection
        
        Args:
            tool_calls: List of tool calls from OpenAI response
            user_id: User ID to inject into tool execution
            
        Returns:
            List of execution results
        """
        results = []
        
        for tool_call in tool_calls:
            try:
                # Handle both OpenAI objects and dict formats (for tests)
                if hasattr(tool_call, 'function'):
                    # OpenAI object format
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                else:
                    # Dict format (for tests)
                    function_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                
                logger.info(f"Executing tool call: {function_name} for user {user_id}")
                
                if function_name not in self._function_handlers:
                    error_msg = f"Unknown function: {function_name}"
                    logger.error(error_msg)
                    results.append(f"Error: {error_msg}")
                    continue
                
                # Execute function with injected user_id
                # Remove user_id from arguments if present to prevent conflicts
                filtered_arguments = {k: v for k, v in arguments.items() if k != 'user_id'}
                handler = self._function_handlers[function_name]
                result = handler(user_id=user_id, **filtered_arguments)
                results.append(result)
                
                logger.info(f"Tool call {function_name} executed successfully")
                
            except Exception as e:
                error_msg = f"Error executing tool call: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results.append(f"Error: {error_msg}")
        
        return results
    
    def _handle_update_notes(self, user_id: str, note_content: str) -> str:
        """
        Handle update_notes tool call with server-side injection
        
        Args:
            user_id: User ID (injected by dispatcher)
            note_content: Note content from model
            
        Returns:
            Success message
        """
        # Validate input
        if not note_content or not note_content.strip():
            return "Error: Note content cannot be empty"
        
        # Server-side injection of timestamp and metadata
        timestamp = datetime.now(timezone.utc).isoformat()
        created_by = "therapist_ai"
        
        try:
            # Store note in Firestore
            self.firestore_client.add_note(
                user_id=user_id,
                content=note_content.strip(),
                timestamp=timestamp,
                created_by=created_by
            )
            
            logger.info(f"Note added for user {user_id}: {note_content[:50]}...")
            return "Note recorded successfully"
            
        except Exception as e:
            error_msg = f"Failed to save note: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"
