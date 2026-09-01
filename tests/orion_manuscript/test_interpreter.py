# test_interpreter.py

import pytest
from space_station_stc.orion_manuscript import interpreter

# --- Test strip_comment ---

@pytest.mark.asyncio
async def test_strip_comment_removes_after_hash():
    res = await interpreter.strip_comment("hello # comment")
    assert res == "hello "

@pytest.mark.asyncio
async def test_strip_comment_no_comment():
    res = await interpreter.strip_comment("no comment here")
    assert res == "no comment here"

@pytest.mark.asyncio
async def test_strip_comment_only_comment():
    res = await interpreter.strip_comment("# only comment")
    assert res == ""

# --- Test parse_program ---

@pytest.mark.asyncio
async def test_parse_empty_program():
    res = await interpreter.parse_program("")
    assert res == []

@pytest.mark.asyncio
async def test_parse_only_comments_and_empty_lines():
    text = "# just a comment\n\n   \n# another comment"
    res = await interpreter.parse_program(text)
    assert res == []

@pytest.mark.asyncio
async def test_parse_single_command_no_args():
    text = ": print"
    expected = [("print", [])]
    res = await interpreter.parse_program(text)
    assert res == expected

@pytest.mark.asyncio
async def test_parse_single_command_with_args():
    text = ": print\nline1\nline2"
    expected = [("print", ["line1", "line2"])]
    res = await interpreter.parse_program(text)
    assert res == expected

@pytest.mark.asyncio
async def test_parse_multiple_commands():
    text = ": first\narg1\n: second command\narg2\narg3\n: third"
    expected = [
        ("first", ["arg1"]),
        ("second command", ["arg2", "arg3"]),
        ("third", [])
    ]
    assert interpreter.parse_program(text) == expected

@pytest.mark.asyncio
async def test_parse_ignores_comment_lines_and_comment_in_args():
    text = ": cmd\narg with # comment\n# full comment line\nanother arg"
    expected = [("cmd", ["arg with ", "another arg"])]
    assert interpreter.parse_program(text) == expected

@pytest.mark.asyncio
async def test_parse_command_without_leading_spaces():
    # command must start at column 0; leading spaces make it an argument
    text = ": cmd\n   not a command"
    expected = [("cmd", ["   not a command"])]
    assert interpreter.parse_program(text) == expected

@pytest.mark.asyncio
async def test_parse_command_leading_spaces_ignored_if_no_current_command():
    text = "   : cmd\narg"
    # no current command, so this line is treated as orphan argument and ignored
    assert interpreter.parse_program(text) == []

@pytest.mark.asyncio
async def test_parse_empty_command_ignored():
    text = ":\n: real_command\narg"
    expected = [("real_command", ["arg"])]
    assert interpreter.parse_program(text) == expected

@pytest.mark.asyncio
async def test_command_name_case_insensitive():
    text = ": Print\nHello"
    expected = [("print", ["Hello"])]
    assert interpreter.parse_program(text) == expected

@pytest.mark.asyncio
async def test_command_name_multiple_spaces_normalized():
    text = ": second   command\narg"
    expected = [("second command", ["arg"])]
    assert interpreter.parse_program(text) == expected

@pytest.mark.asyncio
async def test_command_name_uppercase_with_spaces():
    text = ":   SECOND    COMMAND   \narg"
    expected = [("second command", ["arg"])]
    assert interpreter.parse_program(text) == expected

# --- Test preservation of argument whitespace ---

@pytest.mark.asyncio
async def test_argument_whitespace_is_preserved():
    text = ": cmd\n    indented line\n\t\ttabbed line\n  two spaces"
    expected = [("cmd", ["    indented line", "\t\ttabbed line", "  two spaces"])]
    assert interpreter.parse_program(text) == expected

# --- Test run_program ---

@pytest.mark.asyncio
async def test_run_program_calls_handlers(capsys):
    calls = []
    def handler1(args):
        calls.append(("handler1", args))
    def handler2(args):
        calls.append(("handler2", args))

    commands = {
        "cmd1": handler1,
        "cmd2": handler2
    }
    blocks = [
        ("cmd1", ["a", "b"]),
        ("cmd2", []),
        ("unknown", ["x"])
    ]
    await interpreter.run_program(blocks, commands)
    captured = capsys.readouterr()
    assert calls == [
        ("handler1", ["a", "b"]),
        ("handler2", [])
    ]
    assert captured.out == "Unknown command: unknown\n"

# --- Test interpret end-to-end ---

@pytest.mark.asyncio
async def test_interpret_with_custom_commands(capsys):
    def cmd_print(args):
        for a in args:
            print(a)
    def cmd_compute(args):
        total = sum(float(a) for a in args)
        print(f"Sum: {total}")

    commands = {
        "print": cmd_print,
        "compute": cmd_compute
    }
    program = (
        "# start\n"
        ": Print\n"
        "Hello\n"
        "World # with comment\n"
        "\n"
        ":   COMPUTE\n"
        "10\n"
        "20.5\n"
        "\n"
        ": missing\n"
        "x\n"
    )
    await interpreter.interpret(program, commands)
    captured = capsys.readouterr()
    expected_output = "Hello\nWorld \nSum: 30.5\nUnknown command: missing\n"
    assert captured.out == expected_output