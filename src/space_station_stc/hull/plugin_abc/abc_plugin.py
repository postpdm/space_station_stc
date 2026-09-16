"""Abstract plugin interface for the Space Station application."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar
from uuid import UUID

from litestar.config.app import AppConfig
from litestar.di import Provide
from litestar.plugins import InitPlugin
from litestar.types import ControllerRouterHandler
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from space_station_stc.hull.plugin_abc.sql_bundle import SQLConnectionBundle


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

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        self.f_init_error_log = ""

        # NOTE: SQL availability is validated later, in on_startup,
        # because the registry is populated from the primary DB
        # asynchronously, after controllers are registered.

        if self.controllers:
            app_config.route_handlers.extend(self.controllers)

        if self.fstatic_req:
            for sf in self.fstatic_req:
                if not (self.fstatic_dir / sf).is_file():
                    self.f_init_error_log += (
                        f'Required static file "{sf}" is not found! '
                    )

        if self.f_init_error_log:
            print(
                f"🔌 Plugin [{self.plugin_name}] ({self.fplugin_id}) "
                f"plugged with errors: {self.f_init_error_log}"
            )
        else:
            print(
                f"🔌 Plugin [{self.plugin_name}] ({self.fplugin_id}) "
                f"plugged successfully."
            )
        return app_config