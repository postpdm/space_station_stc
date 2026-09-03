from abc import ABC
from uuid import UUID

from pathlib import Path

from litestar.plugins import InitPlugin
from litestar.config.app import AppConfig
from litestar.types import ControllerRouterHandler

class BasePlugin(InitPlugin, ABC):
    """
    Abstract plugin.
    Loader should skip it.
    """

    fplugin_id : UUID # global unique plugin ID
    fuser_title : str
    fuser_description : str

    """
    A plugin can fix a list of required static files. Static requirements can be shipped with the source code or collected after the plugin installation.
    Static files can be very large or may be unavailable for automatic download and installation due to security or other reasons
    fstatic_req contain a list of related paths of required static files.
    """
    fstatic_dir = Path() # path
    fstatic_req = []

    # installation error log for system administrative
    f_init_error_log : str

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
    def plugin_name(self) -> str:
        """Return class name."""
        return self.__class__.__name__

    @property
    def controllers(self) -> list[ControllerRouterHandler]:
        """
        List of controllers.
        Redefine it in ancestor.
        """
        return []

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """
        Base logic for controller's registration.
        You can redefine it in ancestors with super()).
        """
        self.f_init_error_log = ""

        if self.controllers:
            app_config.route_handlers.extend(self.controllers)

        # check for static        
        if self.fstatic_req:
            for sf in self.fstatic_req:
                if not Path( self.fstatic_dir / sf ).is_file():
                    self.f_init_error_log = self.f_init_error_log + f'Required static file "{sf}" is not found!'

        if self.f_init_error_log:
            print(f"🔌 Plugin [{self.plugin_name}] ([{self.fplugin_id}]) is plug with errors {self.f_init_error_log}.")
        else:
            print(f"🔌 Plugin [{self.plugin_name}] ([{self.fplugin_id}]) is plug successfully.")
        return app_config

#