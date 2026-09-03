from abc import ABC, abstractmethod
from litestar import Controller, get
from litestar.response import Template

class BasePluginController(Controller, ABC):
    """
    Abstract controller for plugins.
    2 obligatory get's.
    """

    @abstractmethod
    @get("/")
    async def user_homepage(self) -> Template:
        """User page."""

    @abstractmethod
    @get("/admin_panel")
    async def admin_panel(self) -> Template:
        """Admin page."""

    @abstractmethod
    async def plugin_health(self) -> bool:
        """Check plugin healths."""

#