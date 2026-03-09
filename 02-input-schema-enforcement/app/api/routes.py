from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import DataSubmission, SubmissionResponse
from app.services.validator import validate_submission

router = APIRouter()


@router.post("/submit-data", response_model=SubmissionResponse)
async def submit_data(body: DataSubmission) -> SubmissionResponse:
    """Accept a strictly-typed data submission.

    FastAPI + Pydantic enforce structural constraints automatically:
    - Unknown fields are rejected (``extra="forbid"``).
    - ``user_id`` must match ``^[a-zA-Z0-9_-]+$``.
    - ``action`` must be one of ``read | write | delete``.
    - ``content`` is bounded to 1–500 characters.

    The validator service then applies semantic checks (injection patterns,
    tag format) that structural types cannot express.

    Returns 422 for schema violations (FastAPI default).
    Returns 400 for semantic violations detected by the validator.
    """
    is_valid, error_msg = validate_submission(body)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    return SubmissionResponse(
        status="accepted",
        message="Data passed schema enforcement checks",
        validated_action=body.action,
        user_id=body.user_id,
    )
