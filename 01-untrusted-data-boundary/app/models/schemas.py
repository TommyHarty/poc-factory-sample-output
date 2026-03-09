from __future__ import annotations

from pydantic import BaseModel, Field


class ProcessInputRequest(BaseModel):
    user_input: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Raw user-supplied text to validate, sanitize, and process.",
    )


class ProcessInputResponse(BaseModel):
    sanitized_input: str = Field(
        ..., description="The cleaned version of the input that was sent to the model."
    )
    result: str = Field(..., description="The model's response to the sanitized input.")


class ValidationErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    detail: str
    violations: list[ValidationErrorDetail] = Field(default_factory=list)
