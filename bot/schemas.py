from typing import Literal, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator

# The fixed list of categories is no longer needed.
# Priority = Literal["Critical", "High", "Mid", "Low"]
# Category = Literal["events", "emotions", "agreements", "therapy_dynamics", "health"]
Priority = Literal["Critical", "High", "Mid", "Low"]


class Factology(BaseModel):
    """
    A structured representation of a single, meaningful fact extracted from a user's message.
    """

    category: str = Field(
        ...,
        description="The high-level category of the fact (e.g., 'personal_history', 'emotions', 'life_events').",
    )
    content: Optional[str] = Field(
        default=None,
        description="A concise summary of the extracted fact, written in the third person (e.g., 'User is feeling anxious about work.').",
    )
    priority: Priority = Field(
        ...,
        description="The assessed priority of this fact for the therapist's attention.",
    )

    # The model sometimes hallucinates 'description', so we accept it as an alias for 'content'.
    description: Optional[str] = Field(default=None, description="Alias for 'content'.")

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: str) -> str:
        """The model sometimes returns lowercase or synonyms, so we fix them before validation."""
        if not isinstance(v, str):
            return v

        normalized_v = v.capitalize()
        if normalized_v == "Medium":
            return "Mid"

        return normalized_v

    @model_validator(mode="after")
    def consolidate_content(self):
        """Ensure 'content' is populated, using 'description' as a fallback."""
        if self.content is None and self.description is not None:
            self.content = self.description

        if self.content is None:
            raise ValueError(
                "Either 'content' or 'description' must be provided in factology."
            )

        # Clean up the model by removing the alias field
        self.description = None
        return self


class ResponseMode(str, Enum):
    VOICE = "voice"
    TEXT = "text"


class AnalysisResult(BaseModel):
    """Complete analysis of a user's message."""

    response: Optional[str] = Field(
        default=None,
        description="A supportive and empathetic reply for the user.",
    )
    text_to_client: Optional[str] = Field(default=None, description="Alias for 'response'.")
    response_mode: Optional[ResponseMode] = Field(
        default=None,
        description="Preferred delivery format (voice or text). Optional.",
    )
    factology: Optional[List[Factology]] = Field(
        None,
        description="A list of structured fact objects. Must be null if no specific, meaningful fact is identified.",
    )

    @model_validator(mode="after")
    def consolidate_response(self):
        """Ensure 'response' is populated, using 'text_to_client' as a fallback."""
        if self.response is None and self.text_to_client is not None:
            self.response = self.text_to_client

        if self.response is None:
            raise ValueError(
                "Either 'response' or 'text_to_client' must be provided."
            )

        # Clean up the model by removing the alias field
        self.text_to_client = None
        return self


# This is the tool schema that will be passed to the OpenAI API
tools_schema = [{"type": "function", "function": AnalysisResult.model_json_schema()}]

# Rename the function for clarity in the schema
tools_schema[0]["function"]["name"] = "process_user_message"
tools_schema[0]["function"][
    "description"
] = "Processes the user's message to formulate a reply and extract key facts."
