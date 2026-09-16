"""Tests for BasePlugin.sql_dependencies / sql_engine / sql_sessionmaker."""
from unittest.mock import MagicMock

import pytest
from litestar.di import Provide


def test_sql_engine_returns_engine(dummy_plugin, fake_bundle) -> None:
    dummy_plugin.fsql_provided = {"report_database": fake_bundle}
    assert dummy_plugin.sql_engine("report_database") is fake_bundle.engine


def test_sql_sessionmaker_returns_sessionmaker(dummy_plugin, fake_bundle) -> None:
    dummy_plugin.fsql_provided = {"report_database": fake_bundle}
    assert (
        dummy_plugin.sql_sessionmaker("report_database")
        is fake_bundle.sessionmaker
    )


def test_sql_engine_unknown_name_raises(dummy_plugin) -> None:
    dummy_plugin.fsql_provided = {}
    with pytest.raises(KeyError):
        dummy_plugin.sql_engine("nope")


def test_sql_dependencies_empty_when_nothing_declared(dummy_plugin) -> None:
    dummy_plugin.fsql_connections = []
    dummy_plugin.fsql_provided = {}
    assert dummy_plugin.sql_dependencies() == {}


def test_sql_dependencies_keys_and_types(dummy_plugin) -> None:
    """
    Providers are built from fsql_connections (names), independent of
    whether fsql_provided is populated yet.
    """
    dummy_plugin.fsql_connections = ["report_database"]
    dummy_plugin.fsql_provided = {}   # not yet populated

    deps = dummy_plugin.sql_dependencies()

    assert set(deps.keys()) == {
        "sql_report_database_engine",
        "sql_report_database_session",
    }
    for provider in deps.values():
        assert isinstance(provider, Provide)


@pytest.mark.asyncio
async def test_sql_dependencies_providers_return_same_objects(
    dummy_plugin, fake_bundle
) -> None:
    """
    Providers read fsql_provided lazily, so they can be built before
    the registry is populated (e.g. before on_startup).
    """
    dummy_plugin.fsql_connections = ["report_database"]
    dummy_plugin.fsql_provided = {"report_database": fake_bundle}

    deps = dummy_plugin.sql_dependencies()

    assert await deps["sql_report_database_engine"]() is fake_bundle.engine
    assert await deps["sql_report_database_session"]() is fake_bundle.sessionmaker


@pytest.mark.asyncio
async def test_sql_dependencies_multiple_connections(
    dummy_plugin, fake_engine, fake_sessionmaker
) -> None:
    from space_station_stc.hull.plugin_abc.sql_bundle import SQLConnectionBundle

    bundle_a = SQLConnectionBundle(fake_engine, fake_sessionmaker)
    bundle_b = SQLConnectionBundle(MagicMock(), MagicMock())

    dummy_plugin.fsql_connections = ["a", "b"]
    dummy_plugin.fsql_provided = {"a": bundle_a, "b": bundle_b}

    deps = dummy_plugin.sql_dependencies()

    assert set(deps.keys()) == {
        "sql_a_engine",
        "sql_a_session",
        "sql_b_engine",
        "sql_b_session",
    }
    assert await deps["sql_a_engine"]() is bundle_a.engine
    assert await deps["sql_b_engine"]() is bundle_b.engine
    assert await deps["sql_a_session"]() is bundle_a.sessionmaker
    assert await deps["sql_b_session"]() is bundle_b.sessionmaker


@pytest.mark.asyncio
async def test_sql_dependencies_does_not_leak_last_bundle(
    dummy_plugin, fake_engine, fake_sessionmaker
) -> None:
    """
    Regression test: naive closures in loops capture the last bundle.
    Default-argument capture must avoid that trap.
    """
    from space_station_stc.hull.plugin_abc.sql_registry import SQLConnectionBundle

    bundles = {
        "first": SQLConnectionBundle(fake_engine, fake_sessionmaker),
        "second": SQLConnectionBundle(MagicMock(), MagicMock()),
    }
    dummy_plugin.fsql_connections = ["first", "second"]
    dummy_plugin.fsql_provided = bundles

    deps = dummy_plugin.sql_dependencies()

    assert await deps["sql_first_engine"]() is bundles["first"].engine
    assert await deps["sql_second_engine"]() is bundles["second"].engine
    assert await deps["sql_first_engine"]() is not bundles["second"].engine
    assert await deps["sql_second_engine"]() is not bundles["first"].engine


@pytest.mark.asyncio
async def test_sql_dependencies_raises_key_error_if_bundle_missing(
    dummy_plugin
) -> None:
    """
    If a plugin declared a connection but the registry never provided it,
    the lazy provider raises KeyError only at call time, not at build time.
    """
    dummy_plugin.fsql_connections = ["ghost_db"]
    dummy_plugin.fsql_provided = {}

    deps = dummy_plugin.sql_dependencies()
    # Building the providers does not raise.
    assert "sql_ghost_db_engine" in deps

    with pytest.raises(KeyError, match="ghost_db"):
        await deps["sql_ghost_db_engine"]()
