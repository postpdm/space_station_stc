"""Tests for BasePlugin properties and default behaviour."""
from uuid import UUID

import pytest

from space_station_stc.hull.plugin_abc.abc_plugin import BasePlugin
from space_station_stc.hull.plugin_abc import abc_plugin, abc_controller


def test_base_plugin_is_abstract() -> None:
    """BasePlugin itself cannot be instantiated."""
    with pytest.raises(TypeError):
        BasePlugin()  # type: ignore[abstract]


def test_plugin_id_property(dummy_plugin) -> None:
    assert isinstance(dummy_plugin.ID, UUID)
    assert dummy_plugin.ID == dummy_plugin.fplugin_id


def test_plugin_name_is_class_name(dummy_plugin) -> None:
    assert dummy_plugin.plugin_name == "DummyPlugin"


def test_user_title_and_description(dummy_plugin) -> None:
    assert dummy_plugin.user_title == "Dummy"
    assert dummy_plugin.user_description == "Dummy plugin for tests"


def test_default_controllers_is_empty(dummy_plugin) -> None:
    assert dummy_plugin.controllers == []


def test_default_sql_connections_is_empty(dummy_plugin) -> None:
    assert dummy_plugin.fsql_connections == []


def test_default_fsql_provided_is_empty(dummy_plugin) -> None:
    assert dummy_plugin.fsql_provided == {}


def test_default_static_req_is_empty(dummy_plugin) -> None:
    assert dummy_plugin.fstatic_req == []


def test_plugin_id_is_class_level(dummy_plugin) -> None:
    """
    fplugin_id is declared as ClassVar, so two instances share the same value.
    This is important: the loader deduplicates by fplugin_id.
    """
    other = type(dummy_plugin)()
    assert other.fplugin_id == dummy_plugin.fplugin_id