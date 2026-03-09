from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import DataSubmission
from app.services.validator import contains_injection_patterns, validate_submission


def _valid() -> DataSubmission:
    return DataSubmission(user_id="user_42", action="read", content="Fetch profile data")


# ---------------------------------------------------------------------------
# contains_injection_patterns
# ---------------------------------------------------------------------------


class TestContainsInjectionPatterns:
    def test_clean_string_passes(self) -> None:
        assert not contains_injection_patterns("hello world")

    def test_sql_select_detected(self) -> None:
        assert contains_injection_patterns("SELECT * FROM users")

    def test_sql_drop_detected(self) -> None:
        assert contains_injection_patterns("DROP TABLE sessions")

    def test_sql_comment_detected(self) -> None:
        assert contains_injection_patterns("valid -- DROP TABLE users")

    def test_sql_union_detected(self) -> None:
        assert contains_injection_patterns("1 UNION SELECT password FROM users")

    def test_script_tag_detected(self) -> None:
        assert contains_injection_patterns("<script>alert(1)</script>")

    def test_javascript_uri_detected(self) -> None:
        assert contains_injection_patterns("javascript:void(0)")

    def test_mixed_case_sql_detected(self) -> None:
        assert contains_injection_patterns("sElEcT 1")


# ---------------------------------------------------------------------------
# validate_submission — semantic layer
# ---------------------------------------------------------------------------


class TestValidateSubmission:
    def test_valid_submission(self) -> None:
        ok, err = validate_submission(_valid())
        assert ok is True
        assert err is None

    def test_sql_in_content_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="write", content="DROP TABLE users")
        ok, err = validate_submission(s)
        assert ok is False
        assert err is not None

    def test_script_in_content_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="write", content="<script>xss</script>")
        ok, err = validate_submission(s)
        assert ok is False

    def test_invalid_tag_chars_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["UPPERCASE"])
        ok, err = validate_submission(s)
        assert ok is False
        assert err is not None

    def test_tag_with_spaces_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["bad tag"])
        ok, err = validate_submission(s)
        assert ok is False

    def test_tag_too_long_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["a" * 33])
        ok, err = validate_submission(s)
        assert ok is False

    def test_valid_tags_accepted(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["tag-1", "tag_2"])
        ok, err = validate_submission(s)
        assert ok is True

    def test_no_tags_is_valid(self) -> None:
        ok, err = validate_submission(_valid())
        assert ok is True


# ---------------------------------------------------------------------------
# DataSubmission schema — Pydantic structural enforcement
# ---------------------------------------------------------------------------


class TestDataSubmissionSchema:
    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="read", content="ok", extra_field="bad")  # type: ignore[call-arg]

    def test_user_id_with_spaces_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="bad user", action="read", content="ok")

    def test_user_id_with_special_chars_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1!", action="read", content="ok")

    def test_user_id_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="a" * 65, action="read", content="ok")

    def test_unknown_action_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="execute", content="ok")  # type: ignore[arg-type]

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="read", content="")

    def test_oversized_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="read", content="x" * 501)

    def test_valid_submission_accepted(self) -> None:
        s = _valid()
        assert s.user_id == "user_42"
        assert s.action == "read"

    def test_all_valid_actions_accepted(self) -> None:
        for action in ("read", "write", "delete"):
            s = DataSubmission(user_id="u1", action=action, content="ok")  # type: ignore[arg-type]
            assert s.action == action
