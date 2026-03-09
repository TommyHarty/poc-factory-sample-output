from __future__ import annotations

import pytest

from app.services.sanitization_service import sanitize_input


def test_plain_text_unchanged():
    text = "What is the weather like today?"
    assert sanitize_input(text) == text


def test_strips_html_tags():
    result = sanitize_input("Hello <script>alert('xss')</script> world")
    assert "<script>" not in result
    assert "alert" not in result
    assert "Hello" in result
    assert "world" in result


def test_strips_html_entities():
    # &lt;script&gt; decodes to <script> which should then be stripped
    result = sanitize_input("Hello &lt;script&gt;evil()&lt;/script&gt; world")
    assert "<script>" not in result
    assert "evil" not in result


def test_removes_fenced_code_blocks():
    text = "Here is some code:\n```python\nprint('injected')\n```\nEnd."
    result = sanitize_input(text)
    assert "```" not in result
    assert "print" not in result
    assert "Here is some code:" in result
    assert "[code block removed]" in result


def test_removes_control_characters():
    text = "Hello\x00World\x1fTest"
    result = sanitize_input(text)
    assert "\x00" not in result
    assert "\x1f" not in result
    assert "HelloWorldTest" in result


def test_normalizes_whitespace():
    text = "Hello   \t  world\n\n\nfoo"
    result = sanitize_input(text)
    assert "  " not in result
    assert "\t" not in result


def test_strips_leading_trailing_whitespace():
    result = sanitize_input("  hello world  ")
    assert result == "hello world"


def test_empty_string_returns_empty():
    assert sanitize_input("") == ""


def test_unicode_normalization():
    # Two representations of the same accented character; NFC normalization
    # should collapse them to the same form.
    nfd = "caf\u0065\u0301"  # 'e' + combining acute accent
    nfc = "caf\u00e9"        # pre-composed é
    assert sanitize_input(nfd) == sanitize_input(nfc)


@pytest.mark.parametrize(
    "html_input,expected_absent",
    [
        ("<b>bold</b>", "<b>"),
        ("<img src=x onerror=alert(1)>", "<img"),
        ("<a href='javascript:evil()'>click</a>", "<a"),
    ],
)
def test_various_html_tags_stripped(html_input: str, expected_absent: str):
    result = sanitize_input(html_input)
    assert expected_absent not in result
