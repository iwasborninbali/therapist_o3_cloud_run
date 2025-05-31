"""
Tests for tool calling functionality - update_notes tool
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
    
    def test_update_notes_tool_success(self):
        """Test successful note update"""
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
        
        # Verify results
        assert len(results) == 1
        assert results[0] == "Note recorded successfully"
        
        # Verify Firestore was called correctly
        self.mock_firestore.add_note.assert_called_once()
        call_args = self.mock_firestore.add_note.call_args
        
        assert call_args[1]["user_id"] == self.test_user_id
        assert call_args[1]["content"] == "Test note content"
        assert call_args[1]["created_by"] == "therapist_ai"
        assert "timestamp" in call_args[1]
    
    def test_update_notes_empty_content(self):
        """Test note update with empty content"""
        tool_calls = [{
            "function": {
                "name": "update_notes", 
                "arguments": json.dumps({"note_content": ""})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Note content cannot be empty" in results[0]
        self.mock_firestore.add_note.assert_not_called()
    
    def test_update_notes_whitespace_content(self):
        """Test note update with whitespace-only content"""
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": json.dumps({"note_content": "   \n\t  "})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Note content cannot be empty" in results[0]
        self.mock_firestore.add_note.assert_not_called()
    
    def test_update_notes_firestore_error(self):
        """Test note update when Firestore fails"""
        # Mock Firestore failure
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
    
    def test_unknown_function_call(self):
        """Test handling of unknown function calls"""
        tool_calls = [{
            "function": {
                "name": "unknown_function",
                "arguments": json.dumps({"param": "value"})
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Unknown function: unknown_function" in results[0]
    
    def test_invalid_json_arguments(self):
        """Test handling of invalid JSON in arguments"""
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": "invalid json"
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        assert len(results) == 1
        assert "Error: Error executing tool call" in results[0]
    
    def test_multiple_tool_calls(self):
        """Test handling multiple tool calls in one request"""
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
        assert all("Note recorded successfully" in result for result in results)
        assert self.mock_firestore.add_note.call_count == 2
    
    def test_user_id_injection(self):
        """Test that user_id is properly injected and cannot be spoofed"""
        self.mock_firestore.add_note.return_value = True
        
        # Try to pass a different user_id in arguments (should be ignored)
        tool_calls = [{
            "function": {
                "name": "update_notes",
                "arguments": json.dumps({
                    "note_content": "Test note",
                    "user_id": "spoofed_user_id"  # This should be ignored
                })
            }
        }]
        
        results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
        
        # Verify the correct user_id was used (from dispatcher, not arguments)
        call_args = self.mock_firestore.add_note.call_args
        assert call_args[1]["user_id"] == self.test_user_id  # Not the spoofed one
    
    def test_timestamp_injection(self):
        """Test that timestamp is properly injected server-side"""
        self.mock_firestore.add_note.return_value = True
        
        with patch('bot.tools_manager.datetime') as mock_datetime:
            mock_now = datetime(2025, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            tool_calls = [{
                "function": {
                    "name": "update_notes",
                    "arguments": json.dumps({"note_content": "Test note"})
                }
            }]
            
            results = self.tools_manager.dispatch_tool_calls(tool_calls, self.test_user_id)
            
            # Verify timestamp was injected
            call_args = self.mock_firestore.add_note.call_args
            assert call_args[1]["timestamp"] == mock_now.isoformat()


class TestToolCallingIntegration:
    """Integration tests for tool calling with OpenAI client"""
    
    @patch('bot.openai_client.get_client')
    @patch('bot.tools_manager.ToolsManager')
    def test_openai_tool_calling_flow(self, mock_tools_manager_class, mock_get_client):
        """Test end-to-end tool calling flow with OpenAI client"""
        from bot.openai_client import get_response
        from config import Config
        
        # Mock OpenAI response with tool calls
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_message = Mock()
        mock_message.content = None
        
        # Create mock tool call object with proper attributes
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function = Mock()
        mock_tool_call.function.name = "update_notes"
        mock_tool_call.function.arguments = json.dumps({"note_content": "AI generated note"})
        
        mock_message.tool_calls = [mock_tool_call]
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        
        # Mock continue response
        mock_continue_message = Mock()
        mock_continue_message.content = "I've noted that you like coffee. How can I help you today?"
        mock_continue_response = Mock()
        mock_continue_response.choices = [Mock(message=mock_continue_message)]
        
        # Set up side effect for two calls
        mock_client.chat.completions.create.side_effect = [mock_response, mock_continue_response]
        
        # Mock tools manager
        mock_tools_manager = Mock()
        mock_tools_manager.get_tools_for_openai.return_value = [{"type": "function"}]
        mock_tools_manager.dispatch_tool_calls.return_value = ["Note recorded successfully"]
        
        # Test with tool calling enabled
        with patch.object(Config, 'ENABLE_TOOL_CALLING', True):
            messages = [{"role": "user", "content": "Remember that I like coffee"}]
            result = get_response(messages, tools_manager=mock_tools_manager, user_id="123")
            
            # Should return continued generation response
            assert result == "I've noted that you like coffee. How can I help you today?"
            
            # Verify tools were added to first request
            first_call_args = mock_client.chat.completions.create.call_args_list[0]
            assert "tools" in first_call_args[1]
            
            # Verify tool dispatch was called
            mock_tools_manager.dispatch_tool_calls.assert_called_once()
            
            # Verify two OpenAI calls were made (initial + continue)
            assert mock_client.chat.completions.create.call_count == 2
    
    @patch('bot.openai_client.get_client')
    def test_openai_without_tool_calling(self, mock_get_client):
        """Test OpenAI client without tool calling enabled"""
        from bot.openai_client import get_response
        from config import Config
        
        # Mock OpenAI response without tool calls
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_message = Mock()
        mock_message.content = "Regular AI response"
        mock_message.tool_calls = None
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test with tool calling disabled
        with patch.object(Config, 'ENABLE_TOOL_CALLING', False):
            messages = [{"role": "user", "content": "Hello"}]
            result = get_response(messages, tools_manager=None, user_id=None)
            
            # Should return regular response
            assert result == "Regular AI response"
            
            # Verify no tools were added to request
            call_args = mock_client.chat.completions.create.call_args
            assert "tools" not in call_args[1] 