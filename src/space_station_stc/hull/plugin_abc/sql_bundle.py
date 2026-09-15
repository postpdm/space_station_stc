"""SQLAlchemy connection bundle handed to plugins by the core."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


@dataclass(slots=True, frozen=True)
class SQLConnectionBundle:
    """A pair of engine + sessionmaker for a single named connection."""

    engine: AsyncEngine
    sessionmaker: async_sessionmaker