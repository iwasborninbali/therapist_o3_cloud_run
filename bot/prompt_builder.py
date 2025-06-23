"""
Prompt Builder for o4-mini and o3 models.

This module encapsulates the logic for creating payloads for both the o4-mini
pre-processing model and the main o3 therapist model.
"""

import logging
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid
import json
import datetime
from pathlib import Path

# Internal imports for payload generation
from bot.firestore_client import (
    get_system_prompt,
    set_system_prompt,
)
from config import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# --- Pydantic Schemas for o4-mini response validation ---


class ReorganisationAction(BaseModel):
    """
    Defines a single action to reorganise facts, such as merging.
    """

    model_config = ConfigDict(extra="ignore")

    action: str = Field(
        "merge",
        description="The action to perform, must be 'merge'.",
    )
    ids: List[int] = Field(..., description="A list of 2 or 3 fact IDs to be merged.")
    final_content: str = Field(
        ...,
        description="The new, combined content for the resulting fact.",
    )
    reason: str = Field(
        ..., description="A brief justification for why this merge is proposed."
    )

    @field_validator("action")
    @classmethod
    def action_to_lower(cls, v: str) -> str:
        """Converts the action to lowercase for consistent processing."""
        if v:
            return v.lower()
        return v


class FactSummaryResult(BaseModel):
    """
    The expected output from o4-mini, containing a summary and reorganisation plan.
    """

    summary: str = Field(
        ...,
        description="A summary of relevant facts and history to help the main model respond to the user query.",
    )
    references: List[int] = Field(
        default_factory=list,
        description="A list of IDs of the facts used to create the summary.",
    )
    reorganisation: Optional[List[ReorganisationAction]] = Field(
        None,
        description="An optional list of actions to reorganise facts, e.g., merging duplicates.",
    )


# --- Tool Schemas for o4-mini ---

o4_mini_tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "process_context_for_summary",
            "description": "Processes the provided context and returns a summary.",
            "parameters": FactSummaryResult.model_json_schema(),
        },
    }
]

# --- File path for the o4-mini prompt ---
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
O4_MINI_PROMPT_PATH = PROMPT_DIR / "o4_mini_system_prompt.txt"


def json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    # Handle Firestore DatetimeWithNanoseconds 
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

def load_o4_mini_prompt() -> str:
    """Loads the o4-mini system prompt from its file."""
    try:
        with open(O4_MINI_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(
            f"o4-mini system prompt not found at {O4_MINI_PROMPT_PATH}. Using a basic fallback."
        )
        return "You are a helpful assistant. Analyze the facts and the user message to provide a summary."


# --- Payload Builder for o4-mini ---


def build_o4_mini_payload(
    user_message: str, facts: List[Dict[str, Any]], history: List[Dict[str, Any]]
) -> Optional[List[Dict[str, str]]]:
    """Builds the payload for the o4-mini model to get a context summary."""
    messages = []

    # 1. System Prompt
    system_prompt = load_o4_mini_prompt()
    messages.append({"role": "system", "content": system_prompt})

    # Helper to create pseudo tool calls
    def create_pseudo_tool_call(name: str, content: str):
        tool_call_id = f"call_{uuid.uuid4().hex[:10]}_{name}"  # Shortened UUID
        return [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": content,
            },
        ]

    # 2. Factology
    factology_content = json.dumps(facts, ensure_ascii=False, indent=2, default=json_serializer)
    messages.extend(create_pseudo_tool_call("get_factology", factology_content))

    # 3. Recent History
    history_content = json.dumps(history, ensure_ascii=False, indent=2, default=json_serializer)
    messages.extend(create_pseudo_tool_call("get_recent_history", history_content))

    # 4. Current User Query
    messages.extend(create_pseudo_tool_call("get_current_user_query", user_message))

    return messages


# --- Payload Builder for o3-therapist ---


def build_payload(
    user_id: str,
    current_user_query: str,
    history: List[Dict[str, Any]],
    o4_mini_summary: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Builds the complete message payload for the OpenAI API call.
    Optionally includes a summary from the o4-mini model via a pseudo tool call.
    """
    messages = []

    # 1. System Prompt
    system_prompt = get_system_prompt(user_id)
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT
        set_system_prompt(user_id, system_prompt)
    messages.append({"role": "system", "content": system_prompt})

    # 2. Add summary from o4-mini as a pseudo tool call if available
    if o4_mini_summary:
        tool_call_id = f"call_{uuid.uuid4().hex}"
        messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": "get_co_therapist_help",
                            "arguments": "{}",
                        },
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": "get_co_therapist_help",
                "content": o4_mini_summary,
            }
        )

    # 3. Current UTC time and date (pseudo tool call)
    utc_time_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    time_tool_call_id = f"call_{uuid.uuid4().hex}"
    messages.append(
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": time_tool_call_id,
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "arguments": "{}",
                    },
                }
            ],
        }
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": time_tool_call_id,
            "name": "get_current_time",
            "content": f"Current UTC time is: {utc_time_str}. Use this for context if needed.",
        }
    )

    # 4. Last 6 messages from history
    if history:
        cleaned_history = []
        for msg in history:
            if msg.get("role") and msg.get("content"):
                cleaned_history.append({"role": msg["role"], "content": msg["content"]})
        messages.extend(cleaned_history)
        logger.info(f"Loaded {len(cleaned_history)} messages from history.")

    # 5. Current user query
    messages.append({"role": "user", "content": current_user_query})

    return messages
