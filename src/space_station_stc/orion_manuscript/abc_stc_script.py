# abc_stc_script.py

"""
Abstract base class for building concrete script interpreters.

This module provides a base class that uses the generic parser from
`interpreter.py` and dispatches commands to methods defined in subclasses.
Command names are normalized and mapped to method names by lowercasing,
replacing spaces with underscores, and prefixing with "cmd_".
"""

from abc import ABC, abstractmethod

from . import interpreter


class UnknownCommandError(Exception):
    """Raised when a command has no corresponding handler method."""
    pass


class ABC_STC_Script(ABC):
    """
    Base class for line-based command interpreters.

    Subclasses should implement command handlers as methods named
    `cmd_<normalized_command_name>`. For example:

        : print          ->  cmd_print
        : second command ->  cmd_second_command

    Unknown commands raise `UnknownCommandError` by default.
    This can be changed by overriding `unknown_command`.
    """

    async def interpret(self, text: str) -> None:
        """
        Parse the input text and execute each command block.

        Args:
            text: The full program text.
        """
        blocks = interpreter.parse_program(text)
        for command_name, args in blocks:
            method = self._get_command_method(command_name)
            if method is not None:
                await method(args)
            else:
                self.unknown_command(command_name, args)

    async def _get_command_method(self, command_name: str):
        """
        Return the bound method for the given normalized command name,
        or None if no such method exists.
        """
        # Command names are already normalized (lowercase, single spaces).
        # Replace spaces with underscores and add 'cmd_' prefix.
        method_name = "cmd_" + command_name.replace(" ", "_")
        return getattr(self, method_name, None)

    async def unknown_command(self, command_name: str, args: list) -> None:
        """
        Called when no handler method is found for a command.

        By default raises `UnknownCommandError`.
        Subclasses can override to customize behavior (e.g., ignore, log,
        or raise a different exception).
        """
        raise UnknownCommandError(f"Unknown command: {command_name}")