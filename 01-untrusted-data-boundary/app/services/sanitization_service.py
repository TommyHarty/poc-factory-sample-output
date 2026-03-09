from __future__ import annotations

import html
import re
import unicodedata


# Characters or sequences that could be used to escape prompt context.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Collapse runs of whitespace (newlines, tabs, spaces) to a single space.
_WHITESPACE_RE = re.compile(r"\s+")

# Markdown-style fenced code blocks that could be used to smuggle instructions.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)

# Script/style blocks — remove the tag *and* its entire inner content.
_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)

# Remaining HTML/XML tags (strip tag but keep surrounding text).
_HTML_TAG_RE = re.compile(r"<[^>]{0,200}>")


def sanitize_input(text: str) -> str:
    """
    Return a sanitized copy of *text* safe for inclusion in a model prompt.

    Transformations applied (in order):
    1. Unicode normalization to NFC form.
    2. HTML-entity decoding (so ``&lt;script&gt;`` → ``<script>`` is visible
       before the next step strips it).
    3. Script/style block removal (tag + inner content).
    4. Remaining HTML/XML tag stripping.
    5. Removal of fenced code blocks (common injection vector).
    6. Control-character removal.
    7. Whitespace normalization (collapse to single spaces).
    8. Strip leading/trailing whitespace.
    """
    # 1. Normalize unicode
    text = unicodedata.normalize("NFC", text)

    # 2. Decode HTML entities so angle brackets become literal characters
    text = html.unescape(text)

    # 3. Remove script/style blocks including their content
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)

    # 4. Strip remaining HTML/XML tags
    text = _HTML_TAG_RE.sub("", text)

    # 5. Remove fenced code blocks
    text = _FENCED_CODE_RE.sub("[code block removed]", text)

    # 6. Remove control characters
    text = _CONTROL_CHAR_RE.sub("", text)

    # 7. Normalize whitespace
    text = _WHITESPACE_RE.sub(" ", text)

    # 8. Strip
    text = text.strip()

    return text
