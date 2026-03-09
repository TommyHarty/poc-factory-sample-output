from __future__ import annotations

import re

from app.models.schemas import DataSubmission

# Content-level patterns that indicate likely injection attempts.
# Pydantic handles structural enforcement (types, lengths, enums, extra fields).
# This layer catches semantic signals that structural types cannot express.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    # SQL terminators / comment sequences
    re.compile(r"(--|;|/\*|\*/)", re.IGNORECASE),
    # Common SQL DML/DDL keywords used in injection payloads
    re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|EXEC)\b", re.IGNORECASE),
]

# Tags must be lowercase alphanumeric with hyphens/underscores, max 32 chars.
_TAG_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


def contains_injection_patterns(value: str) -> bool:
    """Return True if *value* matches any known injection pattern."""
    return any(pattern.search(value) for pattern in _INJECTION_PATTERNS)


def validate_submission(submission: DataSubmission) -> tuple[bool, str | None]:
    """Perform semantic validation on top of Pydantic's structural checks.

    Returns ``(True, None)`` when the submission is clean, or
    ``(False, reason)`` when a semantic violation is detected.

    Pydantic already enforces field types, lengths, regex patterns for
    ``user_id``, the ``action`` allowlist, and the ``extra="forbid"``
    policy.  This function adds one more layer: content-level injection
    signal detection and tag format enforcement.
    """
    if contains_injection_patterns(submission.content):
        return False, "Content contains disallowed patterns"

    if submission.tags:
        for tag in submission.tags:
            if not _TAG_PATTERN.match(tag):
                return (
                    False,
                    f"Tag '{tag}' must be lowercase alphanumeric (hyphens/underscores "
                    "allowed) and at most 32 characters",
                )

    return True, None
