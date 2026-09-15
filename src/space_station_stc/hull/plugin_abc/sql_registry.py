"""Centralized registry of SQLAlchemy connections managed by the core."""
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from .sql_bundle import SQLConnectionBundle


class SQLConnectionRegistry:
    """
    Registry that maps arbitrary logical names (e.g. 'report_database')
    to concrete SQLAlchemy engines and sessionmakers.

    The registry does NOT create engines itself: DSNs and factory
    parameters are resolved elsewhere (see build_sqlalchemy_fab).
    Callers register already-built engines / sessionmakers here.
    """

    def __init__(self) -> None:
        self._connections: dict[str, SQLConnectionBundle] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_bundle(self, name: str, bundle: SQLConnectionBundle) -> None:
        """Register a fully-built engine/sessionmaker pair."""
        self._connections[name] = bundle

    def register_engine(
        self,
        name: str,
        engine: AsyncEngine,
        *,
        sessionmaker: async_sessionmaker | None = None,
        session_kwargs: dict | None = None,
    ) -> None:
        """
        Register an engine; build a sessionmaker for it unless one is given.
        Extra `session_kwargs` are merged into the default ones.
        """
        if sessionmaker is None:
            kwargs = {"expire_on_commit": False, **(session_kwargs or {})}
            sessionmaker = async_sessionmaker(engine, **kwargs)
        self._connections[name] = SQLConnectionBundle(engine, sessionmaker)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def has(self, name: str) -> bool:
        return name in self._connections

    def get(self, name: str) -> SQLConnectionBundle:
        return self._connections[name]

    def resolve(self, names: list[str]) -> dict[str, SQLConnectionBundle]:
        """Return only the requested connections; missing names are skipped."""
        return {n: self._connections[n] for n in names if n in self._connections}

    def all_names(self) -> list[str]:
        return list(self._connections.keys())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def dispose_all(self) -> None:
        """Gracefully dispose every engine; wire to Litestar on_shutdown."""
        for bundle in self._connections.values():
            await bundle.engine.dispose()