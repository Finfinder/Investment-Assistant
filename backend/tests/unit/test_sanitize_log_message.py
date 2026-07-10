"""Tests for sanitize_log_message() - centralized log sanitization helper."""

import logging

from app.core.logging_config import sanitize_log_message


class TestUrlCredentialMasking:
    """Verify sanitize_log_message masks credentials embedded in URLs."""

    def test_redis_url_with_user_and_password(self):
        """redis://user:password@host -> redis://user:***@host."""
        result = sanitize_log_message("redis://admin:secret123@localhost:6379/0")
        assert result == "redis://admin:***@localhost:6379/0"

    def test_redis_url_password_only(self):
        """redis://password@host -> redis://***@host."""
        result = sanitize_log_message("redis://secret123@localhost:6379/0")
        assert result == "redis://***@localhost:6379/0"

    def test_redis_url_without_credentials(self):
        """No credentials: returned unchanged."""
        result = sanitize_log_message("redis://localhost:6379/0")
        assert result == "redis://localhost:6379/0"

    def test_redis_url_empty_credentials(self):
        """redis://@host -> redis://***@host."""
        result = sanitize_log_message("redis://@localhost:6379")
        assert result == "redis://***@localhost:6379"

    def test_url_without_protocol_separator(self):
        """Plain string without :// - returned unchanged."""
        result = sanitize_log_message("localhost:6379")
        assert result == "localhost:6379"

    def test_url_with_special_chars_in_password(self):
        """Password with special characters is masked."""
        result = sanitize_log_message("redis://user:p%40ss@host:6379")
        assert result == "redis://user:***@host:6379"

    def test_url_with_multiple_at_signs_in_password(self):
        """Password containing @ - rsplit handles correctly."""
        result = sanitize_log_message("redis://user:p@ss@host:6379")
        assert result == "redis://user:***@host:6379"

    def test_url_with_db_number(self):
        """URL with database number preserved."""
        result = sanitize_log_message("redis://user:pass@host:6379/3")
        assert result == "redis://user:***@host:6379/3"

    def test_url_with_ipv4_host(self):
        """URL with IPv4 host preserved."""
        result = sanitize_log_message("redis://user:pass@192.168.1.100:6379/0")
        assert result == "redis://user:***@192.168.1.100:6379/0"

    def test_rediss_scheme(self):
        """rediss:// SSL scheme preserved."""
        result = sanitize_log_message("rediss://user:pass@host:6379/0")
        assert result == "rediss://user:***@host:6379/0"

    def test_postgres_connection_string(self):
        """postgresql://user:pass@host/db -> postgresql://user:***@host/db."""
        result = sanitize_log_message("postgresql://app_user:s3cr3t@db.example.com:5432/investments")
        assert result == "postgresql://app_user:***@db.example.com:5432/investments"

    def test_http_url_with_credentials(self):
        """https://user:pass@host -> https://user:***@host."""
        result = sanitize_log_message("https://api_user:token123@api.example.com/v1")
        assert result == "https://api_user:***@api.example.com/v1"

    def test_long_password_fully_masked(self):
        """Long password is fully masked."""
        long_pass = "a" * 100
        result = sanitize_log_message(f"redis://user:{long_pass}@host")
        assert result == "redis://user:***@host"

    def test_password_with_slash_is_masked(self):
        """Password containing '/' must still be masked (CWE-532 regression guard)."""
        result = sanitize_log_message("redis://user:pa/ss@host")
        assert result == "redis://user:***@host"
        assert "pa/ss" not in result

    def test_postgres_password_with_slash_is_masked(self):
        """PostgreSQL password containing '/' is masked."""
        result = sanitize_log_message("postgresql://user:pa/ss@host/db")
        assert result == "postgresql://user:***@host/db"
        assert "pa/ss" not in result

    def test_mongodb_protocol_is_masked(self):
        """Non-listed protocol (mongodb) credentials are masked (protocol-agnostic)."""
        result = sanitize_log_message("mongodb://user:pass@host:27017/db")
        assert result == "mongodb://user:***@host:27017/db"
        assert "pass" not in result

    def test_mysql_protocol_is_masked(self):
        """Non-listed protocol (mysql) credentials are masked."""
        result = sanitize_log_message("mysql://user:pass@host/db")
        assert result == "mysql://user:***@host/db"
        assert "pass" not in result

    def test_mongodb_srv_protocol_is_masked(self):
        """mongodb+srv credentials are masked."""
        result = sanitize_log_message("mongodb+srv://user:pass@cluster.example.com/db")
        assert result == "mongodb+srv://user:***@cluster.example.com/db"
        assert "pass" not in result

    def test_uppercase_protocol_is_masked(self):
        """Uppercase protocol scheme is masked."""
        result = sanitize_log_message("REDIS://user:pass@host")
        assert result == "REDIS://user:***@host"
        assert "pass" not in result
        assert "a" not in result.split("@")[0]


class TestKeyValueMasking:
    """Verify sanitize_log_message masks key=value / key: value pairs."""

    def test_api_key_equals(self):
        """api_key=SECRET -> api_key=*** (value visible as masked)."""
        result = sanitize_log_message("request failed api_key=SUPER_SECRET")
        assert result == "request failed api_key=***"
        assert "SUPER_SECRET" not in result

    def test_api_key_in_url_query(self):
        """api_key in a URL query string is masked."""
        result = sanitize_log_message("https://api.stlouisfed.org/series?api_key=SUPER_SECRET&series_id=FEDFUNDS")
        assert "api_key=***" in result
        assert "SUPER_SECRET" not in result

    def test_password_equals(self):
        """password=secret -> password=***."""
        result = sanitize_log_message("login password=hunter2 ok")
        assert result == "login password=*** ok"
        assert "hunter2" not in result

    def test_token_colon(self):
        """token: secret -> token=*** (colon separator supported)."""
        result = sanitize_log_message("auth token: abcdef123456")
        assert result == "auth token=***"
        assert "abcdef123456" not in result

    def test_secret_equals(self):
        """secret=value -> secret=***."""
        result = sanitize_log_message("configured secret=topsecret")
        assert result == "configured secret=***"

    def test_authorization_colon(self):
        """authorization: Bearer t -> authorization=*** (token fully masked)."""
        result = sanitize_log_message("header authorization: Bearer eyJabc.def.ghi")
        assert result == "header authorization=***"
        assert "eyJabc" not in result

    def test_cookie_equals(self):
        """cookie=sessionid -> cookie=***."""
        result = sanitize_log_message("set cookie=sessionid123")
        assert result == "set cookie=***"

    def test_case_insensitive_key(self):
        """Sensitive key matching is case-insensitive."""
        result = sanitize_log_message("API_KEY=SUPER_SECRET")
        assert result == "API_KEY=***"

    def test_mixed_case_key(self):
        """Mixed-case key name is masked."""
        result = sanitize_log_message("Token=abc123")
        assert result == "Token=***"


class TestWholeMessageRedactionDelegatedToFormatters:
    """Whole-message redaction for project key names is done by the formatters.

    sanitize_log_message only value-masks; the JSONFormatter / SensitiveFilter
    apply whole-message redaction on top. These tests document that the helper
    itself does NOT redact key names (so the value-masked form stays visible,
    e.g. for api_key=***), and that the formatters perform the redaction.
    """

    def test_helper_keeps_key_name_visible(self):
        """Helper value-masks but does not whole-redact a key name message."""
        result = sanitize_log_message("Twelve_Data_API_Key is configured")
        assert result == "Twelve_Data_API_Key is configured"

    def test_json_formatter_redacts_key_name(self):
        """JSONFormatter whole-redacts a message naming a config key."""
        from app.core.logging_config import JSONFormatter as _JSONFormatter

        formatter = _JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Twelve_Data_API_Key is configured",
            args=(),
            exc_info=None,
        )
        assert "[REDACTED - contains sensitive key]" in formatter.format(record)

    def test_sensitive_filter_redacts_key_name(self):
        """SensitiveFilter whole-redacts a message naming a config key."""
        from app.core.logging_config import SensitiveFilter as _SensitiveFilter

        formatter = _SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="fmp_api_key is set",
            args=(),
            exc_info=None,
        )
        assert "[REDACTED - contains sensitive key]" in formatter.format(record)


class TestIdempotency:
    """Verify sanitize_log_message is idempotent."""

    def test_url_idempotent(self):
        """Double call on a URL yields same result as single call."""
        msg = "redis://admin:secret123@localhost:6379/0"
        assert sanitize_log_message(sanitize_log_message(msg)) == sanitize_log_message(msg)

    def test_key_value_idempotent(self):
        """Double call on key=value yields same result as single call."""
        msg = "api_key=SUPER_SECRET"
        assert sanitize_log_message(sanitize_log_message(msg)) == sanitize_log_message(msg)

    def test_whole_message_idempotent(self):
        """Double call on a redacted message yields same redaction marker."""
        msg = "Twelve_Data_API_Key is configured"
        assert sanitize_log_message(sanitize_log_message(msg)) == sanitize_log_message(msg)

    def test_no_sensitive_idempotent(self):
        """Double call on a safe message yields same safe message."""
        msg = "server started on port 8000"
        assert sanitize_log_message(sanitize_log_message(msg)) == sanitize_log_message(msg)


class TestEdgeCases:
    """Verify behavior on edge-case inputs."""

    def test_empty_string(self):
        """Empty string returned unchanged."""
        assert sanitize_log_message("") == ""

    def test_no_sensitive_data(self):
        """Message without sensitive data returned unchanged."""
        msg = "Fetched 42 observations for FEDFUNDS"
        assert sanitize_log_message(msg) == msg

    def test_api_key_masked_not_redacted(self):
        """api_key=*** remains visible (not whole-message redacted)."""
        result = sanitize_log_message("api_key=***")
        assert result == "api_key=***"
