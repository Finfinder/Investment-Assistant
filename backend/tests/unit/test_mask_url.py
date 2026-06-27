"""Tests for _mask_url() - password masking in Redis URLs for safe logging."""

from app.core.redis import _mask_url


class TestMaskUrl:
    """Verify _mask_url masks passwords in all Redis URL formats."""

    def test_url_with_user_and_password(self):
        """Standard format: redis://user:password@host:6379/0."""
        result = _mask_url("redis://admin:secret123@localhost:6379/0")
        assert result == "redis://admin:***@localhost:6379/0"

    def test_url_with_password_only(self):
        """Password-only format: redis://password@host:6379/0."""
        result = _mask_url("redis://secret123@localhost:6379/0")
        assert result == "redis://***@localhost:6379/0"

    def test_url_without_credentials(self):
        """No credentials: redis://localhost:6379/0."""
        result = _mask_url("redis://localhost:6379/0")
        assert result == "redis://localhost:6379/0"

    def test_url_with_empty_credentials(self):
        """Empty credentials: redis://@host."""
        result = _mask_url("redis://@localhost:6379")
        assert result == "redis://***@localhost:6379"

    def test_url_without_protocol_separator(self):
        """Plain string without :// - returned unchanged."""
        result = _mask_url("localhost:6379")
        assert result == "localhost:6379"

    def test_url_with_empty_string(self):
        """Empty string returned unchanged."""
        result = _mask_url("")
        assert result == ""

    def test_url_with_special_chars_in_password(self):
        """Password with special characters."""
        result = _mask_url("redis://user:p%40ss@host:6379")
        assert result == "redis://user:***@host:6379"

    def test_url_with_multiple_at_signs_in_password(self):
        """Password containing @ - rsplit handles correctly."""
        result = _mask_url("redis://user:p@ss@host:6379")
        assert result == "redis://user:***@host:6379"

    def test_url_with_db_number(self):
        """URL with database number."""
        result = _mask_url("redis://user:pass@host:6379/3")
        assert result == "redis://user:***@host:6379/3"

    def test_url_with_ipv4_host(self):
        """URL with IPv4 host."""
        result = _mask_url("redis://user:pass@192.168.1.100:6379/0")
        assert result == "redis://user:***@192.168.1.100:6379/0"

    def test_url_with_ssl_scheme(self):
        """rediss:// SSL scheme."""
        result = _mask_url("rediss://user:pass@host:6379/0")
        assert result == "rediss://user:***@host:6379/0"

    def test_url_with_long_password(self):
        """Long password is fully masked."""
        long_pass = "a" * 100
        result = _mask_url(f"redis://user:{long_pass}@host")
        assert result == "redis://user:***@host"
        assert "a" not in result.split("@")[0]
