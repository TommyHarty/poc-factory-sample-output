from __future__ import annotations

import pytest

from app.services.encoder import html_encode


def test_no_special_characters():
    assert html_encode("hello world") == "hello world"


def test_ampersand():
    assert html_encode("rock & roll") == "rock &amp; roll"


def test_less_than():
    assert html_encode("<script>") == "&lt;script&gt;"


def test_greater_than():
    assert html_encode("x > y") == "x &gt; y"


def test_double_quote():
    assert html_encode('say "hello"') == "say &quot;hello&quot;"


def test_single_quote():
    assert html_encode("it's fine") == "it&#x27;s fine"


def test_full_xss_payload():
    raw = '<script>alert("XSS")</script>'
    encoded = html_encode(raw)
    assert "<script>" not in encoded
    assert "&lt;script&gt;" in encoded
    assert "&quot;" in encoded


def test_multiple_special_characters():
    raw = "<b>Hello & 'World'</b>"
    encoded = html_encode(raw)
    assert "&lt;" in encoded
    assert "&gt;" in encoded
    assert "&amp;" in encoded
    assert "&#x27;" in encoded


def test_empty_string():
    assert html_encode("") == ""


def test_already_safe_text():
    safe = "Just a plain sentence without special chars."
    assert html_encode(safe) == safe
