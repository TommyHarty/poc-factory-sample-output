from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import ExecuteQueryRequest, ExecuteQueryResponse, SeedResponse
from app.services.query_service import QueryError, QueryService, get_query_service

router = APIRouter(prefix="/api", tags=["queries"])


@router.post(
    "/execute-query",
    response_model=ExecuteQueryResponse,
    summary="Execute a parameterized SQL query",
    description=(
        "Accepts a SQL statement with ? placeholders and a list of positional "
        "parameter values. The values are bound by the SQLite driver — never via "
        "string interpolation — so SQL injection is structurally impossible."
    ),
)
def execute_query(
    body: ExecuteQueryRequest,
    service: QueryService = Depends(get_query_service),
) -> ExecuteQueryResponse:
    try:
        rows, rows_affected = service.execute(body.query, body.parameters)
        return ExecuteQueryResponse(
            success=True,
            rows=rows,
            rows_affected=rows_affected,
        )
    except QueryError as exc:
        # Return a structured error response rather than a 500.
        # The caller can inspect `success=False` and read the `error` field.
        return ExecuteQueryResponse(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/seed",
    response_model=SeedResponse,
    summary="Seed the demo database with sample users",
    description="Inserts a small set of demo rows so /execute-query has data to return.",
)
def seed(
    service: QueryService = Depends(get_query_service),
) -> SeedResponse:
    rows_inserted = service.seed_demo_data()
    return SeedResponse(
        message="Demo data seeded successfully.",
        rows_inserted=rows_inserted,
    )
