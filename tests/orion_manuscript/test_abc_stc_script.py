# test_abc_stc_script.py

import pytest

from space_station_stc.orion_manuscript.abc_stc_script import ABC_STC_Script, UnknownCommandError


# --- Concrete test subclass ---

class SampleScript(ABC_STC_Script):
    """A concrete script with a few command handlers."""

    def __init__(self):
        self.calls = []  # record calls for assertions

    def cmd_print(self, args):
        self.calls.append(("print", args))

    def cmd_compute(self, args):
        self.calls.append(("compute", args))

    def cmd_second_command(self, args):
        self.calls.append(("second command", args))


# --- Tests ---

def test_basic_command_dispatch():
    script = SampleScript()
    program = ": print\nHello\nWorld\n: compute\n10\n20"
    script.interpret(program)

    assert script.calls == [
        ("print", ["Hello", "World"]),
        ("compute", ["10", "20"])
    ]


def test_command_name_normalization():
    script = SampleScript()
    program = ": PRINT\nA\n:   Second    Command   \nB"
    script.interpret(program)

    assert script.calls == [
        ("print", ["A"]),
        ("second command", ["B"])
    ]


def test_unknown_command_raises_exception():
    script = SampleScript()
    program = ": unknown\narg1"
    with pytest.raises(UnknownCommandError, match="Unknown command: unknown"):
        script.interpret(program)


def test_custom_unknown_command():
    class CustomScript(ABC_STC_Script):
        def __init__(self):
            self.unknown_calls = []

        def unknown_command(self, command_name, args):
            self.unknown_calls.append((command_name, args))

    script = CustomScript()
    program = ": mystery\nx\ny"
    script.interpret(program)
    assert script.unknown_calls == [("mystery", ["x", "y"])]


def test_argument_whitespace_preserved():
    script = SampleScript()
    program = ": print\n    indented\n\t tabbed"
    script.interpret(program)
    assert script.calls == [
        ("print", ["    indented", "\t tabbed"])
    ]