"""
Unit tests for ToolsManager module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json

from bot.tools_manager import ToolsManager


class TestToolsManager:
    """Test ToolsManager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_firestore = Mock()
        self.tools_manager = ToolsManager(self.mock_firestore)
        self.test_user_id = "123456789"
    
    def test_tools_manager_initialization(self):
        """Test ToolsManager initializes correctly"""
        assert self.tools_manager.firestore_client == self.mock_firestore
        assert "update_notes" in self.tools_manager._tools_registry
        assert "update_notes" in self.tools_manager._function_handlers
    
    def test_get_tools_for_openai(self):
        """Test getting tools specification for OpenAI"""
        tools = self.tools_manager.get_tools_for_openai()
        
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "update_notes"
        assert tools[0]["function"]["strict"] is True
        assert "note_content" in tools[0]["function"]["parameters"]["properties"]
        assert tools[0]["function"]["parameters"]["required"] == ["note_content"]
    
    def test_dispatch_tool_calls_success(self):
        """Test successful tool call dispatch"""
        # Mock successful Firestore operation
        self.mock_firestore.add_note.return_value = True
        
        # Test tool call
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": json.dumps({"note_content": "Test note content"})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert results[0] == "Note recorded successfully"
        
        # Verify Firestore was called correctly
        self.mock_firestore.add_note.assert_called_once()
        call_args = self.mock_firestore.add_note.call_args
        assert call_args[1]["user_id"] == self.test_user_id
        assert call_args[1]["content"] == "Test note content"
        assert call_args[1]["created_by"] == "therapist_ai"
        assert "timestamp" in call_args[1]
    
    def test_dispatch_tool_calls_empty_content(self):
        """Test tool call with empty content"""
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": json.dumps({"note_content": ""})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Note content cannot be empty" in results[0]
        
        # Verify Firestore was not called
        self.mock_firestore.add_note.assert_not_called()
    
    def test_dispatch_tool_calls_firestore_error(self):
        """Test tool call with Firestore error"""
        # Mock Firestore error
        self.mock_firestore.add_note.side_effect = Exception("Firestore error")
        
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": json.dumps({"note_content": "Test note"})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Failed to save note" in results[0]
    
    def test_dispatch_tool_calls_unknown_function(self):
        """Test tool call with unknown function"""
        tool_calls = [{
            "function": {
                "name": "unknown_function",
                "arguments": json.dumps({"param": "value"})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Unknown function: unknown_function" in results[0]
    
    def test_dispatch_tool_calls_invalid_json(self):
        """Test tool call with invalid JSON arguments"""
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": "invalid json"
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Error executing tool call" in results[0]
    
    def test_dispatch_tool_calls_openai_object_format(self):
        """Test tool call with OpenAI object format"""
        # Mock successful Firestore operation
        self.mock_firestore.add_note.return_value = True
        
        # Create mock OpenAI tool call object
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "update_notes"
        mock_tool_call.function.arguments = json.dumps({"note_content": "Test note"})
        
        results = self.tools_manager.dispatch_tool_calls([mock_tool_call], self.test_user_id)
        
        assert len(results) == 1
        assert results[0] == "Note recorded successfully"
    
    def test_dispatch_multiple_tool_calls(self):
        """Test dispatching multiple tool calls"""
        # Mock successful Firestore operation
        self.mock_firestore.add_note.return_value = True
        
        tool_calls = [
            {
                "function": {
                    "name": "update_notes",
                    "arguments": json.dumps({"note_content": "First note"})
                }
            },
            {
                "function": {
                    "name": "update_notes",
                    "arguments": json.dumps({"note_content": "Second note"})
                }
            }
        ]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 2
        assert all(result == "Note recorded successfully" for result in results)
        assert self.mock_firestore.add_note.call_count == 2
    
    def test_handle_update_notes_strips_whitespace(self):
        """Test that note content is stripped of whitespace"""
        # Mock successful Firestore operation
        self.mock_firestore.add_note.return_value = True
        
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": json.dumps({"note_content": "  Test note with spaces  "})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert results[0] == "Note recorded successfully"
        
        # Verify content was stripped
        call_args = self.mock_firestore.add_note.call_args
        assert call_args[1]["content"] == "Test note with spaces"
    
    def test_user_id_injection_security(self):
        """Test that user_id cannot be overridden via arguments"""
        # Mock successful Firestore operation
        self.mock_firestore.add_note.return_value = True
        
        # Try to inject different user_id via arguments
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": json.dumps({
                    "note_content": "Test note",
                    "user_id": "malicious_user_id"
                })
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert results[0] == "Note recorded successfully"
        
        # Verify correct user_id was used (not the malicious one)
        call_args = self.mock_firestore.add_note.call_args
        assert call_args[1]["user_id"] == self.test_user_id
        assert call_args[1]["user_id"] != "malicious_user_id" 
