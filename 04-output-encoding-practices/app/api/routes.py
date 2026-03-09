from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import EncodeRequest, EncodeResponse
from app.services.encoder import html_encode

router = APIRouter()


@router.post("/encode", response_model=EncodeResponse)
def encode_text(payload: EncodeRequest) -> EncodeResponse:
    """Accept raw user text and return its HTML-encoded equivalent.

    This endpoint demonstrates output encoding as a defence against XSS:
    any special characters in the input are converted to HTML entities
    before the value is returned to the caller for use in rendered output.
    """
    return EncodeResponse(encoded_text=html_encode(payload.text))
