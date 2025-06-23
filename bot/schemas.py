from typing import Literal, Optional, List
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


class AnalysisResult(BaseModel):
    """
    The complete analysis of a user's message, including a direct reply and any extracted facts.
    This is the required output format for the 'process_user_message' tool.
    """

    text_to_client: str = Field(
        ...,
        description="A supportive and empathetic response to send directly to the user in the chat.",
    )
    factology: Optional[List[Factology]] = Field(
        None,
        description="A list of structured fact objects. Must be null if no specific, meaningful fact is identified.",
    )


# This is the tool schema that will be passed to the OpenAI API
tools_schema = [{"type": "function", "function": AnalysisResult.model_json_schema()}]

# Rename the function for clarity in the schema
tools_schema[0]["function"]["name"] = "process_user_message"
tools_schema[0]["function"][
    "description"
] = "Processes the user's message to formulate a reply and extract key facts."
