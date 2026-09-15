"""Tests for BasePlugin.on_app_init: statics, controllers, error log."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from litestar.config.app import AppConfig

from space_station_stc.hull.plugin_abc.abc_plugin import BasePlugin

def _make_app_config() -> AppConfig:
    """Build a minimal AppConfig with empty route_handlers."""
    return AppConfig(route_handlers=[])


# ----------------------------------------------------------------------
# Success path
# ----------------------------------------------------------------------
def test_on_app_init_clean(dummy_plugin, capsys) -> None:
    cfg = _make_app_config()
    returned = dummy_plugin.on_app_init(cfg)

    assert returned is cfg
    assert dummy_plugin.f_init_error_log == ""
    assert "plugged successfully" in capsys.readouterr().out


# ----------------------------------------------------------------------
# Controllers registration
# ----------------------------------------------------------------------
def test_on_app_init_registers_controllers(dummy_plugin) -> None:
    sentinel = object()

    # Patch the `controllers` property on the instance.
    type(dummy_plugin).controllers = property(lambda self: [sentinel])  # type: ignore[assignment]
    try:
        cfg = _make_app_config()
        dummy_plugin.on_app_init(cfg)
        assert sentinel in cfg.route_handlers
    finally:
        # Restore the original property so other tests are not affected.
        type(dummy_plugin).controllers = BasePlugin.controllers  # type: ignore[assignment]


# ----------------------------------------------------------------------
# Missing SQL connection
# ----------------------------------------------------------------------
def test_on_app_init_reports_missing_sql(dummy_plugin, capsys) -> None:
    dummy_plugin.fsql_connections = ["report_database", "audit_db"]
    # Provide only one of the two.
    dummy_plugin.fsql_provided = {"report_database": MagicMock()}

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)

    assert "Missing SQL connections" in dummy_plugin.f_init_error_log
    assert "audit_db" in dummy_plugin.f_init_error_log
    assert "report_database" not in dummy_plugin.f_init_error_log.split(":")[1]


def test_on_app_init_no_error_when_all_sql_present(dummy_plugin) -> None:
    dummy_plugin.fsql_connections = ["report_database"]
    dummy_plugin.fsql_provided = {"report_database": MagicMock()}

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)

    assert dummy_plugin.f_init_error_log == ""


# ----------------------------------------------------------------------
# Static files
# ----------------------------------------------------------------------
def test_on_app_init_static_file_present(dummy_plugin, static_dir: Path) -> None:
    dummy_plugin.fstatic_dir = static_dir
    dummy_plugin.fstatic_req = ["index.html"]

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)

    assert dummy_plugin.f_init_error_log == ""


def test_on_app_init_static_file_missing(dummy_plugin, static_dir: Path) -> None:
    dummy_plugin.fstatic_dir = static_dir
    dummy_plugin.fstatic_req = ["missing.css"]

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)

    assert 'Required static file "missing.css"' in dummy_plugin.f_init_error_log


def test_on_app_init_static_and_sql_errors_are_combined(
    dummy_plugin, static_dir: Path
) -> None:
    dummy_plugin.fstatic_dir = static_dir
    dummy_plugin.fstatic_req = ["missing.css"]
    dummy_plugin.fsql_connections = ["audit_db"]
    dummy_plugin.fsql_provided = {}

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)

    log = dummy_plugin.f_init_error_log
    assert "audit_db" in log
    assert "missing.css" in log


# ----------------------------------------------------------------------
# Error log is reset on each call
# ----------------------------------------------------------------------
def test_on_app_init_resets_error_log(dummy_plugin, static_dir: Path) -> None:
    dummy_plugin.fstatic_dir = static_dir
    dummy_plugin.fstatic_req = ["missing.css"]

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)
    assert dummy_plugin.f_init_error_log != ""

    # Second call with a valid static file must clear the previous error.
    dummy_plugin.fstatic_req = ["index.html"]
    dummy_plugin.on_app_init(cfg)
    assert dummy_plugin.f_init_error_log == ""