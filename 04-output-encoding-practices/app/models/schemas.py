from __future__ import annotations

from pydantic import BaseModel


class EncodeRequest(BaseModel):
    text: str


class EncodeResponse(BaseModel):
    encoded_text: str
