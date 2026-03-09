from __future__ import annotations

import re
from dataclasses import dataclass, field


# Patterns that indicate likely prompt injection or instruction hijacking attempts.
# Each entry is a (label, compiled pattern) pair.
_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "role_override",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b.{0,40}\b(above|previous|prior|earlier|all)\b.{0,40}\b(instructions?|prompt|context|rules?|constraints?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_leak",
        re.compile(
            r"\b(print|show|reveal|output|repeat|display|echo)\b.{0,40}\b(system\s*prompt|instructions?|context|rules?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "jailbreak_roleplay",
        re.compile(
            r"\b(pretend|act\s+as|you\s+are\s+now|from\s+now\s+on|imagine\s+you\s+are|you\s+must\s+now)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "instruction_injection_markers",
        re.compile(
            r"(###\s*(system|instruction|user|assistant)|<\s*/?system\s*>|<\s*/?instruction\s*>|\[INST\]|\[/INST\])",
            re.IGNORECASE,
        ),
    ),
    (
        "developer_mode_unlock",
        re.compile(
            r"\b(developer\s+mode|DAN|do\s+anything\s+now|jailbreak|unrestricted\s+mode)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "token_manipulation",
        re.compile(
            r"(\btoken\b.{0,20}\blimit\b|\bmax.{0,10}tokens?\b.{0,20}\bignore\b)",
            re.IGNORECASE,
        ),
    ),
]

# Hard upper bound on input length (characters).
_MAX_INPUT_LENGTH = 4000


@dataclass
class ValidationResult:
    is_valid: bool
    violations: list[str] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0


def validate_input(text: str) -> ValidationResult:
    """
    Check whether *text* is safe to forward to the model.

    Returns a :class:`ValidationResult` with ``is_valid=True`` when no
    injection patterns are detected, or ``is_valid=False`` with a list of
    human-readable violation descriptions.
    """
    violations: list[str] = []

    # --- structural checks ---
    if not text or not text.strip():
        violations.append("Input must not be empty or whitespace only.")

    if len(text) > _MAX_INPUT_LENGTH:
        violations.append(
            f"Input exceeds maximum allowed length of {_MAX_INPUT_LENGTH} characters."
        )

    # --- injection pattern checks ---
    for label, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            violations.append(f"Potential injection detected: {label}.")

    return ValidationResult(is_valid=len(violations) == 0, violations=violations)
