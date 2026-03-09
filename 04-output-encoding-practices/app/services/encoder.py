from __future__ import annotations

import html


def html_encode(text: str) -> str:
    """Convert special characters to their HTML-safe equivalents.

    This prevents XSS by ensuring user-supplied strings cannot be interpreted
    as HTML or JavaScript when rendered in a browser context.

    Characters encoded: &, <, >, ", '
    """
    return html.escape(text, quote=True)
