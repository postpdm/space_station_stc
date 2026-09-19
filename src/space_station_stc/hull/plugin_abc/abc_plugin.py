"""Abstract plugin interface for the Space Station application."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, get_type_hints, get_origin, get_args, Annotated
from uuid import UUID

from litestar.config.app import AppConfig
from litestar.di import Provide
from litestar.plugins import InitPlugin
from litestar.types import ControllerRouterHandler
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from space_station_stc.hull.plugin_abc.sql_bundle import SQLConnectionBundle

import inspect

from litestar.di import NamedDependency

class BasePlugin(InitPlugin, ABC):
    """
    Abstract plugin.
    The loader skips this class and instantiates only concrete subclasses.
    """

    @abstractmethod
    def health(self) -> bool :
        """Subclasses must declare their controllers. This tiny methods it's only need to make the BasePlugin abstract (PEP 3119 – Introducing Abstract Base Classes)."""
        ...

    # Global unique plugin identifier.
    fplugin_id: UUID
    fuser_title: str
    fuser_description: str

    # A plugin may require a set of static files shipped with the source
    # code or downloaded after installation.
    # fstatic_req holds relative paths of required static files.
    fstatic_dir: ClassVar[Path] = Path()
    fstatic_req: ClassVar[list[str]] = []

    # Installation error log for system administrators.
    f_init_error_log: str

    # --- SQLAlchemy connection requirements ---
    # Logical names of SQL connections managed by the core,
    # e.g. ["report_database", "audit_db"].
    fsql_connections: ClassVar[list[str]] = []

    # Filled by the loader before on_app_init is called:
    # {logical_name: SQLConnectionBundle}.
    fsql_provided: dict[str, SQLConnectionBundle] = {}

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------

    @property
    def ID(self) -> UUID:
        """Return ID."""
        return self.fplugin_id

    @property
    def init_error_log(self) -> str:
        """Return init error log."""
        return self.f_init_error_log

    @property
    def user_title(self) -> str:
        """Return user title."""
        return self.fuser_title

    @property
    def user_description(self) -> str:
        """Return user description."""
        return self.fuser_description

    @property
    def sql_connections(self) -> str:
        """Return declared sql input sources."""
        return self.fsql_connections

    @property
    def plugin_name(self) -> str:
        """Return class name."""
        return self.__class__.__name__

    @property
    def controllers(self) -> list[ControllerRouterHandler]:
        """
        List of controllers.
        Redefine it in subclasses.
        """
        return []

    # ------------------------------------------------------------------
    # Convenience helpers for accessing provided SQL connections
    # ------------------------------------------------------------------

    def sql_engine(self, name: str) -> AsyncEngine:
        """Return the AsyncEngine registered under the given logical name."""
        return self.fsql_provided[name].engine

    def sql_sessionmaker(self, name: str) -> async_sessionmaker:
        """Return the async_sessionmaker registered under the logical name."""
        return self.fsql_provided[name].sessionmaker

    def sql_dependencies(self) -> dict[str, Provide]:
        """
        Build lazy Litestar DI providers from `fsql_connections`.

        Providers are name-based: they do not read `fsql_provided` until
        first invocation. That allows the registry to be populated later,
        in Litestar on_startup, after reading the primary database.
        """
        plugin = self
        deps: dict[str, Provide] = {}

        for name in self.fsql_connections:
            def make_engine(
                resource_name: str = name,
                p: "BasePlugin" = plugin,
            ) -> AsyncEngine:
                return p.fsql_provided[resource_name].engine

            def make_session(
                resource_name: str = name,
                p: "BasePlugin" = plugin,
            ) -> async_sessionmaker:
                return p.fsql_provided[resource_name].sessionmaker

            deps[f"sql_{name}_engine"] = Provide(make_engine, sync_to_thread=False)
            deps[f"sql_{name}_session"] = Provide(make_session, sync_to_thread=False)

        return deps

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    # Set of valid DI key names this plugin exposes to Litestar.
    def _expected_di_names(self) -> set[str]:
        """Names produced by sql_dependencies(): sql_<name>_engine/_session."""
        names: set[str] = set()
        for name in self.fsql_connections:
            names.add(f"sql_{name}_engine")
            names.add(f"sql_{name}_session")
        return names


    def _collect_dependency_params(self, handler) -> set[str]:
        """
        Return names of handler parameters annotated with NamedDependency
        (or any Annotated[...] carrying a Dependency marker).
        """
        found: set[str] = set()
        fn = getattr(handler, "fn", handler)   # litestar handlers wrap the fn
        try:
            hints = get_type_hints(fn, include_extras=True)
        except Exception:
            # If hints cannot be resolved, skip - do not block the plugin.
            return found

        sig = inspect.signature(fn)
        for pname in sig.parameters:
            if pname in ("self", "cls"):
                continue
            hint = hints.get(pname)
            if hint is None:
                continue
            # Annotated[T, NamedDependency[...]] or Annotated[T, Dependency(...)]
            if get_origin(hint) is Annotated:
                for meta in get_args(hint)[1:]:
                    # NamedDependency is a class alias; isinstance works on
                    # instances of Dependency, but for NamedDependency it's a
                    # typing alias - detect by __class_getitem__ / name.
                    if meta is NamedDependency or meta.__class__.__name__ == "Dependency":
                        found.add(pname)
                        break
        return found


    def _validate_controller_dependencies(self, controllers) -> list[str]:
        """
        Return a list of human-readable problems: handler parameters that
        look like SQL dependencies but are not among the names this plugin
        actually declares in fsql_connections.
        """
        expected = self._expected_di_names()
        problems: list[str] = []

        for controller in controllers:
            handlers = getattr(controller, "__dict__", {})
            # Iterate only HTTP route handlers registered on the controller.
            for attr_name, attr in handlers.items():
                fn = getattr(attr, "fn", None)
                if fn is None:
                    continue
                for pname in self._collect_dependency_params(attr):
                    # Only check parameters that look like SQL deps.
                    if pname.startswith("sql_") and pname not in expected:
                        problems.append(
                            f"{controller.__name__}.{attr_name}: "
                            f"parameter '{pname}' is not declared in "
                            f"fsql_connections (available: {sorted(expected)})"
                        )
        return problems


    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        self.f_init_error_log = ""

        if self.controllers:
            problems = self._validate_controller_dependencies(self.controllers)
            if problems:
                msg = "SQL dependency mismatch: " + "; ".join(problems)
                self.f_init_error_log += msg + " "
                print(f"🔌 Plugin [{self.plugin_name}] ❌ ({self.fplugin_id}) skipped: {msg}")
                # Do NOT register the controllers -> Litestar never sees them.
            else:
                app_config.route_handlers.extend(self.controllers)

        if self.fstatic_req:
            for sf in self.fstatic_req:
                if not (self.fstatic_dir / sf).is_file():
                    self.f_init_error_log += f'Required static file "{sf}" is not found! '

        if self.f_init_error_log and "skipped" not in self.f_init_error_log:
            print(
                f"🔌 Plugin [{self.plugin_name}] ❌ ({self.fplugin_id}) "
                f"plugged with errors: {self.f_init_error_log}"
            )
        elif not self.f_init_error_log:
            print(
                f"🔌 Plugin [{self.plugin_name}] ({self.fplugin_id}) "
                f"plugged successfully."
            )
        return app_config
    
    def check_sql_connections(self) -> None:
        """
        Append a message to f_init_error_log for every requested SQL
        connection that was not provided by the core.
        Call this after the registry has been populated.
        """
        missing = [n for n in self.fsql_connections if n not in self.fsql_provided]
        if missing:
            msg = f'Missing SQL connections: {", ".join(missing)}! '
            self.f_init_error_log += msg
            print(
                f"🔌 Plugin [{self.plugin_name}] ({self.fplugin_id}) "
                f"SQL problem: {msg.strip()}"
            )

#