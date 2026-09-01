# Simple Line-Based Command Interpreter

A lightweight interpreter for a small, extensible command language. It parses text consisting of commands and their arguments, then executes them sequentially using user-supplied handler functions.

## Syntax

### Commands

- A command line **must start with a colon (`:`)** at the very first character of the line (no leading whitespace).
- After the colon, the command name extends to the end of the line.
- Command names are **case-insensitive**.
- Multiple spaces between words in a command name are collapsed to a single space.
- Example: `: print`, `: Compute Total`, `:   SECOND    COMMAND` all become `print`, `compute total`, `second command` after normalization.

### Arguments

- Any non-empty line that does **not** start with `:` is treated as an argument to the current command.
- Arguments are collected in order and passed to the command handler as a list of strings.
- Leading and trailing whitespace in argument lines is **preserved** exactly (except for comment removal).
- Empty lines (lines with only whitespace) are ignored.

### Comments

- The `#` character starts a comment. Everything from `#` to the end of the line is ignored.
- Comments can appear on their own lines or at the end of command or argument lines.
- Example: `: print # this is a comment` → command `print`; `Hello # world` → argument `Hello ` (note the trailing space before `#` is kept).

### Program Structure

A program is a sequence of one or more command blocks. Each block consists of:

1. A command line.
2. Zero or more argument lines.

Commands are executed in the order they appear.
Example:

```
: print
Hello, World!
This is a second line.

: compute
10
20.5
```

## Python API

### Module: `interpreter`

The interpreter is provided as a single module with three main functions.

#### `parse_program(text: str) -> list`

Parses the input text and returns a list of command blocks.
Each block is a tuple `(command_name, arguments)`, where `command_name` is a normalized string (lowercase, single spaces) and `arguments` is a list of strings.

#### `run_program(blocks: list, command_dict: dict) -> None`

Executes the parsed blocks. For each block, it looks up the command name in `command_dict` and calls the corresponding function with the list of arguments. If the command is not found, it prints `Unknown command: <name>`.

#### `interpret(text: str, command_dict: dict) -> None`

Convenience function that combines `parse_program` and `run_program`.

### Command Handlers

A command handler is a Python function that accepts one argument: a list of strings. It can perform any action, such as printing, computing, or modifying external state.

Example:

```python
async def cmd_print(args):
    for line in args:
        print(line)

async def cmd_compute(args):
    total = sum(float(a) for a in args)
    print(f"Sum: {total}")

commands = {
    "print": cmd_print,
    "compute": cmd_compute
}

import interpreter

program = """
: print
Hello
World

: compute
10
20.5
"""

await interpreter.interpret(program, commands)

```

Output:

```
Hello
World
Sum: 30.5
```

Testing

    pytest test_interpreter.py

The tests cover:

 - Comment stripping
 - Empty program and comment-only input
 - Single and multiple commands
 - Argument collection and preservation of whitespace
 - Command name normalization (case, extra spaces)
 - Execution with custom handlers
 - Unknown command handling

Extending the Language

To add a new command, simply define a handler function and add it to the command dictionary:

```
async def cmd_shout(args):
    for a in args:
        print(a.upper())

commands["shout"] = cmd_shout
```

No changes to the interpreter itself are needed.

Design Notes

- The interpreter uses only Python's standard library, no external dependencies.

- The parser is intentionally simple; it does not support nested blocks or special escape sequences.

- Leading whitespace in arguments is preserved to allow commands that interpret indentation (e.g., code blocks, configuration sections).


# Abstract Base Class Wrapper for Script Interpreters

## Overview

`ABC_STC_Script` is an abstract base class that simplifies the creation of custom script interpreters. It builds upon the generic line-based parser from `interpreter.py` and automatically dispatches commands to methods defined in the subclass. This design allows you to focus on implementing command logic rather than parsing details.

## Command‑to‑Method Mapping

Commands in the script text are normalized by the parser (lowercased, extra spaces collapsed) and then mapped to method names using the following rule:

- The command name is converted to lowercase and spaces are replaced with underscores.
- The string `cmd_` is prefixed to the result.

Examples:

| Script command      | Normalized command   | Method name         |
|---------------------|----------------------|---------------------|
| `: print`           | `print`              | `cmd_print`         |
| `: second command`  | `second command`     | `cmd_second_command`|
| `:   COMPUTE TOTAL` | `compute total`      | `cmd_compute_total` |

## Creating a Concrete Interpreter

1. Import the base class:
```python
    from abc_stc_script import ABC_STC_Script
```

2. Define a subclass and implement one method for each command you want to support. Each handler receives a list of argument strings.

```python
class MyScript(ABC_STC_Script):
    async def cmd_print(self, args):
        for line in args:
            print(line)

    async def cmd_compute(self, args):
        total = sum(float(a) for a in args)
        print(f"Sum: {total}")

```

3. Instantiate the subclass and call `interpret()` with the script text.

```python
script = MyScript()
async script.interpret("""
    : print
    Hello, World!
    : compute
    10
    20.5
""")

```

Output:

    Hello, World!
	Sum: 30.5

## Handling Unknown Commands

By default, if a command has no corresponding method, `ABC_STC_Script` raises an `UnknownCommandError`. This behaviour can be changed by overriding the `unknown_command` method.

## Customising Error Handling

To ignore unknown commands or log them, override `unknown_command`:

```python

class LenientScript(ABC_STC_Script):
    def unknown_command(self, command_name, args):
        print(f"Ignoring unknown command: {command_name}")
```

   unknown_command is sync!

If you prefer to raise a different exception, override the method and raise your own.

## Exception Class

`UnknownCommandError` is defined in `abc_stc_script.py` and can be imported:

```python
from abc_stc_script import UnknownCommandError
```

## Integration with the Parser

The base class uses the `interpreter.parse_program()` function to break the input into command blocks. You do not need to call the parser directly unless you require advanced customisation.

## Testing Your Interpreter

Subclasses can be easily tested with `pytest`. The repository includes a test file (`test_abc_stc_script.py`) that demonstrates typical tests, including dispatch, normalization, unknown commands, and whitespace preservation.

## Extending

To add a new command, simply add a new method to your subclass following the `cmd_` naming rule. No changes to the base class are required.

## Design Notes

 - The class is abstract (inherits from `abc.ABC`), but it does not enforce abstract methods; any command can be omitted.
 - Command names are case‑insensitive and extra spaces between words are ignored.
 - Argument lines are passed as a list of strings, preserving their original leading/trailing whitespace.
 