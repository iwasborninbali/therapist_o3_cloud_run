import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import Config
from bot.retry_utils import retry_sync

logger = logging.getLogger(__name__)

# OpenAI client will be initialized lazily
_client = None

def get_client():
    """Get OpenAI client, creating it if needed"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            timeout=120.0  # 2 minutes timeout for OpenAI requests
        )
    return _client


@retry_sync()
def get_response(messages, tools_manager=None, user_id=None):
    """
    Get a response from OpenAI based on the conversation messages
    
    Args:
        messages (list): List of message dictionaries with role and content
        tools_manager: ToolsManager instance for handling tool calls (optional)
        user_id (str): User ID for tool execution context (optional)

    Returns:
        str: The AI-generated response
    """
    try:
        logger.debug(f"Sending request to OpenAI with {len(messages)} messages")

        client = get_client()
        
        # Prepare request parameters
        request_params = {
            "model": Config.OPENAI_MODEL,
            "reasoning_effort": 'high',
            "messages": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ],
            "max_completion_tokens": 10000
        }
        
        # Add tools if enabled and available
        if Config.ENABLE_TOOL_CALLING and tools_manager and user_id:
            tools = tools_manager.get_tools_for_openai()
            if tools:
                request_params["tools"] = tools
                logger.debug(f"Added {len(tools)} tools to OpenAI request")

        response = client.chat.completions.create(**request_params)
        
        # Check if model wants to call tools
        message = response.choices[0].message
        
        if message.tool_calls and tools_manager and user_id:
            logger.info(f"Model requested {len(message.tool_calls)} tool calls")
            
            # Execute tool calls
            tool_results = tools_manager.dispatch_tool_calls(message.tool_calls, user_id)
            
            # Log tool execution results
            for i, result in enumerate(tool_results):
                logger.info(f"Tool call {i+1} result: {result}")
            
            # Add tool call results to conversation and continue generation
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function", 
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in message.tool_calls
                ]
            })
            
            # Add tool results
            for i, (tool_call, result) in enumerate(zip(message.tool_calls, tool_results)):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            # Continue generation with tool results
            continue_params = {
                "model": Config.OPENAI_MODEL,
                "reasoning_effort": 'high',
                "messages": messages,
                "max_completion_tokens": 10000
            }
            
            continue_response = client.chat.completions.create(**continue_params)
            continue_message = continue_response.choices[0].message
            
            return continue_message.content
        
        # Regular response without tool calls
        response_text = message.content
        logger.debug(f"Received response from OpenAI: {response_text[:50]}...")

        return response_text

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return "I'm sorry, I encountered an issue processing your request. " \
               "Please try again later."
