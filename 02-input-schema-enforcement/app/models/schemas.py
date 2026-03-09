from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataSubmission(BaseModel):
    """Strictly typed request body for /submit-data.

    ``extra="forbid"`` rejects any unrecognised fields, closing a common
    vector where attackers sneak additional keys into a JSON payload hoping
    the application processes them without validation.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Alphanumeric user identifier — no spaces or special chars",
    )
    action: Literal["read", "write", "delete"] = Field(
        ...,
        description="Whitelisted action type — only these three values are accepted",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Payload content; bounded to prevent oversized input attacks",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Optional list of lowercase tags",
    )


class SubmissionResponse(BaseModel):
    """Response model for a successful data submission."""

    status: str
    message: str
    validated_action: str
    user_id: str
