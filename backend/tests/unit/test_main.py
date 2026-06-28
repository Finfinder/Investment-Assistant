"""Tests for main.py application factory - security and logging."""

import logging
from unittest.mock import patch

from app.core.config import get_settings
from app.core.logging_config import _SENSITIVE_KEYS, JSONFormatter, SensitiveFilter


class TestCreateAppLogging:
    """Verify create_app() does not expose sensitive data in logs."""

    def test_no_api_key_names_in_logs_when_keys_configured(self) -> None:
        """create_app() must not log API key names in clear text."""
        get_settings.cache_clear()
        with (
            patch.dict(
                "os.environ",
                {
                    "TWELVE_DATA_API_KEY": "test-key-12",
                    "FMP_API_KEY": "test-key-fmp",
                    "FRED_API_KEY": "test-key-fred",
                },
                clear=False,
            ),
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = mock_get_logger.return_value
            from app.main import create_app

            create_app()

            assert mock_logger.info.called
            log_call = mock_logger.info.call_args
            log_msg = log_call[0][0]
            log_args = log_call[0][1:] if len(log_call[0]) > 1 else ()
            assert "TWELVE_DATA_API_KEY" not in log_msg
            assert "FMP_API_KEY" not in log_msg
            assert "FRED_API_KEY" not in log_msg
            assert "API key(s)" in log_msg
            assert 3 in log_args
        get_settings.cache_clear()

    def test_logs_warning_when_no_keys_configured(self) -> None:
        """create_app() must log warning when no API keys are configured."""
        get_settings.cache_clear()
        with (
            patch.dict(
                "os.environ",
                {
                    "TWELVE_DATA_API_KEY": "",
                    "FMP_API_KEY": "",
                    "FRED_API_KEY": "",
                },
                clear=False,
            ),
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = mock_get_logger.return_value
            from app.main import create_app

            create_app()

            assert mock_logger.warning.called
            log_call = mock_logger.warning.call_args
            log_msg = log_call[0][0]
            assert "No optional API keys configured" in log_msg
            assert "TWELVE_DATA_API_KEY" not in log_msg
        get_settings.cache_clear()

    def test_partial_keys_logs_count(self) -> None:
        """create_app() must log correct count when only some keys are configured."""
        get_settings.cache_clear()
        with (
            patch.dict(
                "os.environ",
                {
                    "TWELVE_DATA_API_KEY": "test-key-12",
                    "FMP_API_KEY": "",
                    "FRED_API_KEY": "test-key-fred",
                },
                clear=False,
            ),
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = mock_get_logger.return_value
            from app.main import create_app

            create_app()

            assert mock_logger.info.called
            log_call = mock_logger.info.call_args
            log_msg = log_call[0][0]
            log_args = log_call[0][1:] if len(log_call[0]) > 1 else ()
            assert "API key(s)" in log_msg
            assert 2 in log_args
            assert "TWELVE_DATA_API_KEY" not in log_msg
            assert "FRED_API_KEY" not in log_msg
        get_settings.cache_clear()


class TestSensitiveFilter:
    """Verify SensitiveFilter redacts sensitive data in log messages."""

    def test_redacts_twelve_data_api_key(self) -> None:
        """SensitiveFilter must redact messages containing TWELVE_DATA_API_KEY."""
        formatter = SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Configured TWELVE_DATA_API_KEY provider",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "TWELVE_DATA_API_KEY" not in result
        assert "REDACTED" in result

    def test_redacts_fmp_api_key(self) -> None:
        """SensitiveFilter must redact messages containing FMP_API_KEY."""
        formatter = SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="FMP_API_KEY is set",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "FMP_API_KEY" not in result
        assert "REDACTED" in result

    def test_redacts_fred_api_key(self) -> None:
        """SensitiveFilter must redact messages containing FRED_API_KEY."""
        formatter = SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Using FRED_API_KEY for macro data",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "FRED_API_KEY" not in result
        assert "REDACTED" in result

    def test_redacts_redis_password(self) -> None:
        """SensitiveFilter must redact messages containing redis_password."""
        formatter = SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="redis_password is configured",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "redis_password" not in result
        assert "REDACTED" in result

    def test_passes_through_safe_message(self) -> None:
        """SensitiveFilter must not modify messages without sensitive data."""
        formatter = SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Application started successfully",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert result == "Application started successfully"


class TestJSONFormatter:
    """Verify JSONFormatter redacts sensitive data in JSON log output."""

    def test_redacts_twelve_data_api_key(self) -> None:
        """JSONFormatter must redact messages containing TWELVE_DATA_API_KEY."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Configured TWELVE_DATA_API_KEY provider",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "TWELVE_DATA_API_KEY" not in result
        assert "REDACTED" in result

    def test_redacts_fmp_api_key(self) -> None:
        """JSONFormatter must redact messages containing FMP_API_KEY."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="FMP_API_KEY is set",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "FMP_API_KEY" not in result
        assert "REDACTED" in result

    def test_redacts_fred_api_key(self) -> None:
        """JSONFormatter must redact messages containing FRED_API_KEY."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Using FRED_API_KEY for macro data",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "FRED_API_KEY" not in result
        assert "REDACTED" in result

    def test_passes_through_safe_message(self) -> None:
        """JSONFormatter must not modify messages without sensitive data."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Application started successfully",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Application started successfully" in result


class TestSensitiveKeysRegistry:
    """Verify _SENSITIVE_KEYS contains all required entries."""

    def test_contains_api_key_names(self) -> None:
        """_SENSITIVE_KEYS must include API key names used in the project."""
        expected = {
            "twelve_data_api_key",
            "fmp_api_key",
            "fred_api_key",
            "redis_password",
            "database_url",
        }
        assert expected.issubset(_SENSITIVE_KEYS)

    def test_contains_standard_keys(self) -> None:
        """_SENSITIVE_KEYS must include standard sensitive key names."""
        expected = {
            "password",
            "secret",
            "token",
            "api_key",
            "apikey",
            "authorization",
            "cookie",
            "credit_card",
        }
        assert expected.issubset(_SENSITIVE_KEYS)


class TestMixedCaseRedaction:
    """W2: Verify redaction works with mixed case key names."""

    def test_redacts_mixed_case_twelve_data(self) -> None:
        """SensitiveFilter must redact mixed case 'Twelve_Data_API_Key'."""
        formatter = SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Twelve_Data_API_Key is configured",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Twelve_Data_API_Key" not in result
        assert "REDACTED" in result

    def test_redacts_lowercase_api_key(self) -> None:
        """SensitiveFilter must redact lowercase 'twelve_data_api_key'."""
        formatter = SensitiveFilter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="twelve_data_api_key is set",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "twelve_data_api_key" not in result
        assert "REDACTED" in result

    def test_json_formatter_redacts_mixed_case(self) -> None:
        """JSONFormatter must redact mixed case key names."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Fmp_API_Key is configured",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Fmp_API_Key" not in result
        assert "REDACTED" in result


class TestApiKeyValuesNotLeaked:
    """W3: Verify API key values are not leaked in logs."""

    def test_api_key_value_not_in_logs(self) -> None:
        """create_app() must not log API key values."""
        get_settings.cache_clear()
        secret_value = "super-secret-api-key-12345"  # noqa: S105
        with (
            patch.dict(
                "os.environ",
                {
                    "TWELVE_DATA_API_KEY": secret_value,
                    "FMP_API_KEY": "",
                    "FRED_API_KEY": "",
                },
                clear=False,
            ),
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = mock_get_logger.return_value
            from app.main import create_app

            create_app()

            # Check all log calls for secret value leakage
            for call in mock_logger.info.call_args_list:
                args = call[0]
                for arg in args:
                    assert secret_value not in str(arg), f"API key value leaked in log: {arg}"
            for call in mock_logger.warning.call_args_list:
                args = call[0]
                for arg in args:
                    assert secret_value not in str(arg), f"API key value leaked in warning: {arg}"
        get_settings.cache_clear()

    def test_json_formatter_redacts_key_value_in_message(self) -> None:
        """JSONFormatter must redact message containing API key value near key name."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="api_key=secret12345 is invalid",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "secret12345" not in result
        assert "REDACTED" in result


class TestRecordArgsSanitization:
    """W5: Verify JSONFormatter sanitizes record.args."""

    def test_redacts_sensitive_data_in_args(self) -> None:
        """JSONFormatter must redact sensitive data in record.args."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Provider configured: %s",
            args=("TWELVE_DATA_API_KEY",),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "TWELVE_DATA_API_KEY" not in result
        assert "REDACTED" in result

    def test_safe_args_pass_through(self) -> None:
        """JSONFormatter must not modify safe args."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processed %d items",
            args=(42,),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "42" in result


class TestStackTraceSanitization:
    """W6: Verify JSONFormatter sanitizes stack traces."""

    def test_redacts_sensitive_data_in_exception(self) -> None:
        """JSONFormatter must redact sensitive data in exception traceback."""
        formatter = JSONFormatter()
        try:
            raise RuntimeError("api_key=secret12345 failed")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Request failed",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        assert "secret12345" not in result
        assert "REDACTED" in result

    def test_safe_exception_passes_through(self) -> None:
        """JSONFormatter must not modify safe exception messages."""
        formatter = JSONFormatter()
        try:
            raise RuntimeError("connection timeout")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Request failed",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        assert "connection timeout" in result
