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
    from space_station_stc.hull.plugin_abc.abc_plugin import BasePlugin

    sentinel = object()
    type(dummy_plugin).controllers = property(lambda self: [sentinel])  # type: ignore[assignment]
    try:
        cfg = _make_app_config()
        dummy_plugin.on_app_init(cfg)
        assert sentinel in cfg.route_handlers
    finally:
        type(dummy_plugin).controllers = BasePlugin.controllers  # type: ignore[assignment]


# ----------------------------------------------------------------------
# Missing SQL connection -> now reported by check_sql_connections,
# not by on_app_init.
# ----------------------------------------------------------------------
def test_check_sql_connections_reports_missing(dummy_plugin, capsys) -> None:
    dummy_plugin.f_init_error_log = ""
    dummy_plugin.fsql_connections = ["report_database", "audit_db"]
    dummy_plugin.fsql_provided = {"report_database": MagicMock()}

    dummy_plugin.check_sql_connections()

    assert "Missing SQL connections" in dummy_plugin.f_init_error_log
    assert "audit_db" in dummy_plugin.f_init_error_log
    # Provided connection must not be reported as missing.
    assert "report_database" not in dummy_plugin.f_init_error_log.split(":", 1)[-1]
    # Console output mirrors the plugin log.
    assert "audit_db" in capsys.readouterr().out


def test_check_sql_connections_no_error_when_all_present(
    dummy_plugin, capsys
) -> None:
    dummy_plugin.f_init_error_log = ""
    dummy_plugin.fsql_connections = ["report_database"]
    dummy_plugin.fsql_provided = {"report_database": MagicMock()}

    dummy_plugin.check_sql_connections()

    assert dummy_plugin.f_init_error_log == ""
    # No "SQL problem" line on success.
    assert "SQL problem" not in capsys.readouterr().out


# ----------------------------------------------------------------------
# Static files (on_app_init)
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


# ----------------------------------------------------------------------
# Combined: static errors from on_app_init + SQL errors from
# check_sql_connections end up in the same f_init_error_log.
# ----------------------------------------------------------------------
def test_on_app_init_static_and_sql_errors_are_combined(
    dummy_plugin, static_dir: Path
) -> None:
    dummy_plugin.fstatic_dir = static_dir
    dummy_plugin.fstatic_req = ["missing.css"]
    dummy_plugin.fsql_connections = ["audit_db"]
    dummy_plugin.fsql_provided = {}

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)          # writes static error
    dummy_plugin.check_sql_connections()   # writes SQL error

    log = dummy_plugin.f_init_error_log
    assert "missing.css" in log
    assert "audit_db" in log


# ----------------------------------------------------------------------
# Error log is reset on each on_app_init call
# ----------------------------------------------------------------------
def test_on_app_init_resets_error_log(dummy_plugin, static_dir: Path) -> None:
    dummy_plugin.fstatic_dir = static_dir
    dummy_plugin.fstatic_req = ["missing.css"]

    cfg = _make_app_config()
    dummy_plugin.on_app_init(cfg)
    assert dummy_plugin.f_init_error_log != ""

    dummy_plugin.fstatic_req = ["index.html"]
    dummy_plugin.on_app_init(cfg)
    assert dummy_plugin.f_init_error_log == ""