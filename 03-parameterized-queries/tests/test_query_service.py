from __future__ import annotations

import pytest

from app.services.query_service import QueryError, QueryService


@pytest.fixture()
def svc() -> QueryService:
    """Fresh in-memory database for each test."""
    return QueryService(db_path=":memory:")


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------


def test_bootstrap_creates_users_table(svc: QueryService) -> None:
    rows, _ = svc.execute("SELECT name FROM sqlite_master WHERE type='table'", [])
    table_names = {r["name"] for r in rows}
    assert "users" in table_names


# ---------------------------------------------------------------------------
# Basic CRUD with parameterized binding
# ---------------------------------------------------------------------------


def test_insert_and_select(svc: QueryService) -> None:
    _, affected = svc.execute(
        "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
        ["alice", "alice@example.com", "admin"],
    )
    assert affected == 1

    rows, _ = svc.execute("SELECT username, role FROM users WHERE username = ?", ["alice"])
    assert len(rows) == 1
    assert rows[0]["username"] == "alice"
    assert rows[0]["role"] == "admin"


def test_update_with_parameters(svc: QueryService) -> None:
    svc.execute(
        "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
        ["bob", "bob@example.com", "user"],
    )
    _, affected = svc.execute(
        "UPDATE users SET role = ? WHERE username = ?",
        ["admin", "bob"],
    )
    assert affected == 1

    rows, _ = svc.execute("SELECT role FROM users WHERE username = ?", ["bob"])
    assert rows[0]["role"] == "admin"


def test_delete_with_parameters(svc: QueryService) -> None:
    svc.execute(
        "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
        ["carol", "carol@example.com", "user"],
    )
    _, affected = svc.execute("DELETE FROM users WHERE username = ?", ["carol"])
    assert affected == 1

    rows, _ = svc.execute("SELECT * FROM users WHERE username = ?", ["carol"])
    assert rows == []


# ---------------------------------------------------------------------------
# SQL injection prevention — the core demonstration
# ---------------------------------------------------------------------------


def test_classic_injection_attempt_is_neutralised(svc: QueryService) -> None:
    """A tautology injection payload must NOT return extra rows.

    With string interpolation the payload  ' OR '1'='1  would turn:
        SELECT * FROM users WHERE username = '<payload>'
    into a query that returns every row.  With parameterized binding the
    single-quoted string is treated as a literal value, so no rows match.
    """
    svc.seed_demo_data()

    injection_payload = "' OR '1'='1"
    rows, _ = svc.execute(
        "SELECT * FROM users WHERE username = ?",
        [injection_payload],
    )
    # No user has that literal username, so zero rows are returned.
    assert rows == [], (
        "SQL injection succeeded — parameterized binding is broken!"
    )


def test_union_injection_attempt_is_neutralised(svc: QueryService) -> None:
    """A UNION injection payload must not leak additional rows."""
    svc.seed_demo_data()

    # Without parameterized binding this would append a second SELECT.
    payload = "alice' UNION SELECT id, username, email, role FROM users --"
    rows, _ = svc.execute(
        "SELECT * FROM users WHERE username = ?",
        [payload],
    )
    assert rows == [], "UNION injection succeeded — parameterized binding is broken!"


def test_drop_table_injection_attempt_is_neutralised(svc: QueryService) -> None:
    """A DROP TABLE injection in a parameter value must not destroy the table."""
    svc.seed_demo_data()

    payload = "alice'; DROP TABLE users; --"
    rows, _ = svc.execute(
        "SELECT * FROM users WHERE username = ?",
        [payload],
    )
    # The payload is treated as a literal string — no rows match, table survives.
    assert rows == []

    # Verify the table still exists and has its original rows.
    all_rows, _ = svc.execute("SELECT * FROM users", [])
    assert len(all_rows) == 3


# ---------------------------------------------------------------------------
# Allowlist enforcement (defence in depth)
# ---------------------------------------------------------------------------


def test_ddl_statement_is_rejected(svc: QueryService) -> None:
    with pytest.raises(QueryError, match="not permitted"):
        svc.execute("DROP TABLE users", [])


def test_create_statement_is_rejected(svc: QueryService) -> None:
    with pytest.raises(QueryError, match="not permitted"):
        svc.execute("CREATE TABLE evil (id INTEGER)", [])


def test_empty_query_is_rejected(svc: QueryService) -> None:
    with pytest.raises(QueryError):
        svc.execute("   ", [])


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


def test_seed_inserts_demo_rows(svc: QueryService) -> None:
    count = svc.seed_demo_data()
    assert count == 3

    rows, _ = svc.execute("SELECT username FROM users ORDER BY username", [])
    usernames = [r["username"] for r in rows]
    assert usernames == ["alice", "bob", "carol"]


def test_seed_is_idempotent(svc: QueryService) -> None:
    svc.seed_demo_data()
    svc.seed_demo_data()  # second call must not raise or duplicate rows

    rows, _ = svc.execute("SELECT COUNT(*) AS cnt FROM users", [])
    assert rows[0]["cnt"] == 3
