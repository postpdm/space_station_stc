from datetime import datetime, timezone
from sqlalchemy import Text, TypeDecorator

class SafeDateTime(TypeDecorator):
    """
    A custom type decorator that safely handles empty strings from the database.
    It inherits from Text to bypass strict DBAPI datetime parsers,
    then manually parses valid dates or converts empty/invalid records to None.
    """
    # Inherit from Text to receive raw string data from the DB driver
    impl = Text
    cache_ok = True

    def process_result_value(self, value, dialect):
        # Triggered when READING from the database
        if value is None:
            return None

        # Cast to string and clean it up
        str_val = str(value).strip()
        if str_val == '':
            return None

        try:
            # Handle typical database formats (ISO format)
            # Python's fromisoformat handles 'YYYY-MM-DD HH:MM:SS' and standard ISO formats
            return datetime.fromisoformat(str_val)
        except ValueError:
            # Fallback if the database contains corrupted or malformed data
            return None

    def process_bind_param(self, value, dialect):
        # Triggered when WRITING to the database via SQLAlchemy core
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
