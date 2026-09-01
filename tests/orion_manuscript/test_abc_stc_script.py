# test_abc_stc_script.py

import pytest

from space_station_stc.orion_manuscript.abc_stc_script import ABC_STC_Script, UnknownCommandError


# --- Concrete test subclass ---

class SampleScript(ABC_STC_Script):
    """A concrete script with a few command handlers."""

    def __init__(self):
        self.calls = []  # record calls for assertions

    async def cmd_print(self, args):
        self.calls.append(("print", args))

    async def cmd_compute(self, args):
        self.calls.append(("compute", args))

    async def cmd_second_command(self, args):
        self.calls.append(("second command", args))


# --- Tests ---

@pytest.mark.asyncio
async def test_basic_command_dispatch():
    script = SampleScript()
    program = ": print\nHello\nWorld\n: compute\n10\n20"
    await script.interpret(program)

    assert script.calls == [
        ("print", ["Hello", "World"]),
        ("compute", ["10", "20"])
    ]


@pytest.mark.asyncio
async def test_command_name_normalization():
    script = SampleScript()
    program = ": PRINT\nA\n:   Second    Command   \nB"
    await script.interpret(program)

    assert script.calls == [
        ("print", ["A"]),
        ("second command", ["B"])
    ]


@pytest.mark.asyncio
async def test_unknown_command_raises_exception():
    script = SampleScript()
    program = ": unknown\narg1"
    with pytest.raises(UnknownCommandError, match="Unknown command: unknown"):
        await script.interpret(program)

@pytest.mark.asyncio
async def test_custom_unknown_command():
    class CustomScript(ABC_STC_Script):
        def __init__(self):
            self.unknown_calls = []

        def unknown_command(self, command_name, args):
            self.unknown_calls.append((command_name, args))

    script = CustomScript()
    program = ": mystery\nx\ny"
    await script.interpret(program)
    assert script.unknown_calls == [("mystery", ["x", "y"])]

@pytest.mark.asyncio
async def test_argument_whitespace_preserved():
    script = SampleScript()
    program = ": print\n    indented\n\t tabbed"
    await script.interpret(program)
    assert script.calls == [
        ("print", ["    indented", "\t tabbed"])
    ]
