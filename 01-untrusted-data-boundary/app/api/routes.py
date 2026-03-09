from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ErrorResponse, ProcessInputRequest, ProcessInputResponse
from app.services.openai_service import process_sanitized_input
from app.services.sanitization_service import sanitize_input
from app.services.validation_service import validate_input

router = APIRouter()


@router.post(
    "/process-input",
    response_model=ProcessInputResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Input failed validation"},
    },
    summary="Validate, sanitize, and process user input",
    description=(
        "Enforces a strict trust boundary by validating and sanitizing the "
        "user-supplied text before forwarding it to the model. Requests that "
        "contain injection patterns are rejected before reaching the LLM."
    ),
)
async def process_input(request: ProcessInputRequest) -> ProcessInputResponse:
    # --- layer 1: structural + injection-pattern validation ---
    validation_result = validate_input(request.user_input)
    if not validation_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Input validation failed.",
                "violations": validation_result.violations,
            },
        )

    # --- layer 2: sanitize (strip tags, control chars, etc.) ---
    sanitized = sanitize_input(request.user_input)

    # --- layer 3: forward sanitized text to model via trusted prompt structure ---
    result = process_sanitized_input(sanitized)

    return ProcessInputResponse(sanitized_input=sanitized, result=result)
