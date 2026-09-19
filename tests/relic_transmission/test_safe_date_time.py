import datetime
from unittest.mock import Mock
import pytest

from space_station_stc.relic_transmission.validate_dt import SafeDateTime

@pytest.fixture
def mock_dialect():
    """Provide a mock dialect required by SQLAlchemy TypeDecorator methods."""
    return Mock()


@pytest.fixture
def safe_datetime_type():
    """Instantiate the custom SafeDateTime type decorator."""
    return SafeDateTime()


class TestSafeDateTimeProcessResultValue:
    """Tests for reading from the database (process_result_value)."""

    def test_returns_none_when_database_value_is_none(self, safe_datetime_type, mock_dialect):
        """
        GIVEN a database value that is None
        WHEN process_result_value is invoked
        THEN it should safely return None.
        """
        result = safe_datetime_type.process_result_value(None, mock_dialect)
        assert result is None

    @pytest.mark.parametrize("empty_input", ["", "   ", "\n", "\t"])
    def test_returns_none_when_database_value_is_empty_or_whitespace(
        self, safe_datetime_type, mock_dialect, empty_input
    ):
        """
        GIVEN a database value that is an empty string or contains only whitespaces
        WHEN process_result_value is invoked
        THEN it must be intercepted and converted to None.
        """
        result = safe_datetime_type.process_result_value(empty_input, mock_dialect)
        assert result is None

    @pytest.mark.parametrize(
        "valid_iso_str, expected_dt",
        [
            ("2026-09-19T18:30:00", datetime.datetime(2026, 9, 19, 18, 30, 0)),
            ("2026-09-19 18:30:00", datetime.datetime(2026, 9, 19, 18, 30, 0)),
            ("2026-09-19", datetime.datetime(2026, 9, 19, 0, 0, 0)),
        ],
    )
    def test_parses_valid_iso_strings_correctly(
        self, safe_datetime_type, mock_dialect, valid_iso_str, expected_dt
    ):
        """
        GIVEN a valid ISO-formatted date string from the database
        WHEN process_result_value is invoked
        THEN it should correctly parse it into a standard datetime object.
        """
        result = safe_datetime_type.process_result_value(valid_iso_str, mock_dialect)
        assert result == expected_dt

    @pytest.mark.parametrize("corrupted_input", ["invalid-date", "0000-00-00", "2026/09/19"])
    def test_returns_none_on_malformed_or_corrupted_strings(
        self, safe_datetime_type, mock_dialect, corrupted_input
    ):
        """
        GIVEN a corrupted or unsupported date format string from the database
        WHEN process_result_value catches a ValueError during parsing
        THEN it should gracefully fallback and return None instead of crashing.
        """
        result = safe_datetime_type.process_result_value(corrupted_input, mock_dialect)
        assert result is None


class TestSafeDateTimeProcessBindParam:
    """Tests for writing to the database (process_bind_param)."""

    def test_returns_none_when_python_value_is_none(self, safe_datetime_type, mock_dialect):
        """
        GIVEN a Python value that is None
        WHEN process_bind_param is invoked
        THEN it should bind a None value to the SQL parameter.
        """
        result = safe_datetime_type.process_bind_param(None, mock_dialect)
        assert result is None

    def test_converts_datetime_object_to_iso_string(self, safe_datetime_type, mock_dialect):
        """
        GIVEN a standard Python datetime object
        WHEN process_bind_param is invoked
        THEN it should serialize it into a valid ISO string for the Text database field.
        """
        dt_input = datetime.datetime(2026, 9, 19, 18, 30, 0)
        result = safe_datetime_type.process_bind_param(dt_input, mock_dialect)
        assert result == "2026-09-19T18:30:00"

    def test_falls_back_to_string_conversion_for_other_types(self, safe_datetime_type, mock_dialect):
        """
        GIVEN an unexpected non-datetime object or raw valid string representation
        WHEN process_bind_param is invoked
        THEN it should fall back to a generic string cast.
        """
        result = safe_datetime_type.process_bind_param("2026-09-19", mock_dialect)
        assert result == "2026-09-19"


    @pytest.mark.parametrize(
        "corrupted_input", 
        [
            "invalid-date",   # Raw text
            "0000-00-00",     # Invalid calendar date
            "2026/09/19",     # Unsupported separator
            "null",           # Literal string 'null' from broken JSON
            "undefined",      # JavaScript-style broken value
            "1234567890",     # Unix timestamp as string (fromisoformat will fail)
            "$$@#%!*",        # Special characters
            "📅",             # Emojis
        ]
    )
    def test_returns_none_on_malformed_or_corrupted_strings(
        self, safe_datetime_type, mock_dialect, corrupted_input
    ):
        """
        GIVEN a corrupted, random, or unsupported string from the database
        WHEN process_result_value catches a ValueError during parsing
        THEN it should gracefully fallback and return None instead of crashing.
        """
        result = safe_datetime_type.process_result_value(corrupted_input, mock_dialect)
        assert result is None
