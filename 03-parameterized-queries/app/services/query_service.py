from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Generator

# Allowlist of permitted SQL statement prefixes.
# This restricts the surface area available through the demo endpoint so the
# POC cannot be misused to execute arbitrary DDL or admin statements.
ALLOWED_PREFIXES: frozenset[str] = frozenset({"SELECT", "INSERT", "UPDATE", "DELETE"})


class QueryError(Exception):
    """Raised when a query cannot be executed safely."""


class QueryService:
    """Executes SQL statements against an in-process SQLite database using
    parameterized queries to prevent SQL injection.

    The database is created in memory by default, which makes the service
    self-contained and easy to test without any filesystem side effects.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        # Use check_same_thread=False because FastAPI may dispatch requests
        # across threads.  For a demo/POC an in-memory DB is sufficient.
        self._conn: sqlite3.Connection = sqlite3.connect(
            db_path, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._bootstrap()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(
        self, query: str, parameters: list[Any]
    ) -> tuple[list[dict[str, Any]], int]:
        """Execute *query* with *parameters* using the DB driver's parameterized
        binding — never via string formatting.

        Returns a tuple of:
          - rows: list of dicts (non-empty for SELECT statements)
          - rows_affected: number of rows changed (INSERT / UPDATE / DELETE)

        Raises QueryError for disallowed or malformed statements.
        """
        self._validate_statement(query)

        try:
            cursor = self._conn.execute(query, parameters)
            self._conn.commit()
        except sqlite3.Error as exc:
            # Roll back any partial changes so the DB stays consistent.
            self._conn.rollback()
            raise QueryError(str(exc)) from exc

        rows: list[dict[str, Any]] = [dict(row) for row in cursor.fetchall()]
        rows_affected: int = cursor.rowcount if cursor.rowcount >= 0 else 0
        return rows, rows_affected

    def seed_demo_data(self) -> int:
        """Insert a small set of demo users so the API has data to query.

        Returns the number of rows inserted.
        """
        users = [
            ("alice", "alice@example.com", "admin"),
            ("bob", "bob@example.com", "user"),
            ("carol", "carol@example.com", "user"),
        ]
        # Use executemany with parameterized placeholders — still safe.
        self._conn.executemany(
            "INSERT OR IGNORE INTO users (username, email, role) VALUES (?, ?, ?)",
            users,
        )
        self._conn.commit()
        return len(users)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _bootstrap(self) -> None:
        """Create the demo schema on first use."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                email    TEXT    NOT NULL,
                role     TEXT    NOT NULL DEFAULT 'user'
            )
            """
        )
        self._conn.commit()

    def _validate_statement(self, query: str) -> None:
        """Reject statements whose first token is not in the allowlist.

        This is a defence-in-depth measure on top of parameterized binding.
        It prevents callers from executing DDL (DROP TABLE, ALTER TABLE …)
        or multi-statement injections through the demo endpoint.
        """
        first_token = query.strip().split()[0].upper() if query.strip() else ""
        if first_token not in ALLOWED_PREFIXES:
            raise QueryError(
                f"Statement type '{first_token}' is not permitted. "
                f"Allowed: {sorted(ALLOWED_PREFIXES)}"
            )


# Module-level singleton — created once when the module is first imported.
# Tests can override this by patching or by constructing their own instance.
_default_service: QueryService | None = None


def get_query_service() -> QueryService:
    """Return the module-level QueryService singleton."""
    global _default_service
    if _default_service is None:
        _default_service = QueryService()
    return _default_service
