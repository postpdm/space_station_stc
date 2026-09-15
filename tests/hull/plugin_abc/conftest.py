"""Shared fixtures for plugin_abc tests."""
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from space_station_stc.hull.plugin_abc.sql_bundle import SQLConnectionBundle
from space_station_stc.hull.plugin_abc.sql_registry import SQLConnectionRegistry
from space_station_stc.hull.plugin_abc.abc_plugin import BasePlugin


# ----------------------------------------------------------------------
# Minimal concrete plugin used across tests.
# ----------------------------------------------------------------------
class DummyPlugin(BasePlugin):
    """A concrete plugin with no controllers, no SQL, no statics."""

    fplugin_id: ClassVar[UUID] = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    fuser_title: ClassVar[str] = "Dummy"
    fuser_description: ClassVar[str] = "Dummy plugin for tests"

    def health(self) -> bool :
        return True


@pytest.fixture
def dummy_plugin() -> DummyPlugin:
    return DummyPlugin()


@pytest.fixture
def fake_engine() -> MagicMock:
    """A fake AsyncEngine - only .dispose() is awaited in tests."""
    engine = MagicMock(spec=AsyncEngine)
    engine.dispose = AsyncMock()
    return engine


@pytest.fixture
def fake_sessionmaker() -> MagicMock:
    return MagicMock(spec=async_sessionmaker)


@pytest.fixture
def fake_bundle(fake_engine, fake_sessionmaker) -> SQLConnectionBundle:
    return SQLConnectionBundle(engine=fake_engine, sessionmaker=fake_sessionmaker)


@pytest.fixture
def sql_registry(fake_bundle) -> SQLConnectionRegistry:
    reg = SQLConnectionRegistry()
    reg.register_bundle("report_database", fake_bundle)
    return reg


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    """A temp directory pre-populated with one static file."""
    (tmp_path / "index.html").write_text("<html/>", encoding="utf-8")
    return tmp_path