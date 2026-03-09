from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecuteQueryRequest(BaseModel):
    """Request model for the parameterized query endpoint.

    The caller supplies a SQL template with ? placeholders and a list of
    positional parameter values. The service substitutes the values safely
    via the DB driver — never via string interpolation.
    """

    query: str = Field(
        ...,
        description="SQL query with ? placeholders for parameters.",
        examples=["SELECT * FROM users WHERE username = ?"],
    )
    parameters: list[Any] = Field(
        default_factory=list,
        description="Positional parameter values that map to each ? placeholder.",
        examples=[["alice"]],
    )


class ExecuteQueryResponse(BaseModel):
    """Response model returned after executing a parameterized query."""

    success: bool
    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Rows returned by the query (empty for non-SELECT statements).",
    )
    rows_affected: int = Field(
        default=0,
        description="Number of rows affected (INSERT / UPDATE / DELETE).",
    )
    error: str | None = Field(
        default=None,
        description="Error message when success is False.",
    )


class SeedResponse(BaseModel):
    """Response returned by the seed endpoint."""

    message: str
    rows_inserted: int
