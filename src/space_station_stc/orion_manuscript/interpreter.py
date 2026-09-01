# interpreter.py

async def strip_comment(line: str) -> str:
    """Remove comment starting with '#' from the line."""
    idx = line.find('#')
    if idx != -1:
        return line[:idx]
    return line


async def normalize_command_name(raw_name: str) -> str:
    """Normalize command name: lowercase and collapse extra whitespace."""
    return " ".join(raw_name.split()).lower()


async def parse_program(text: str) -> list:
    """
    Parse program text into a list of command blocks.
    Each block is a tuple (command_name, list_of_arguments).
    Command names are normalized (lowercase, single spaces).
    Commands start with ':' at the very beginning of the line (no leading spaces).
    Argument lines are preserved exactly as they appear (after comment removal),
    including any leading/trailing whitespace. Empty lines are ignored.
    """
    blocks = []
    current_command = None   # name of the current command
    current_args = []        # arguments collected for the current command

    for raw_line in text.splitlines():
        # 1. Remove comment
        line = await strip_comment(raw_line)
        # 2. Skip empty lines (no non-whitespace characters)
        if not line.strip():
            continue

        # 3. Check if the line is a command (first char is ':')
        if line[0] == ':':
            # Save previous command block if exists
            if current_command is not None:
                blocks.append((current_command, current_args))
            # Extract command name: everything after ':' until end of line, trimmed
            command_part = line[1:].strip()
            if command_part:               # ignore lines with just ':' (empty command)
                current_command = await normalize_command_name(command_part)
                current_args = []
            else:
                current_command = None
                current_args = []
        else:
            # Not a command -> argument for current command (if any)
            if current_command is not None:
                current_args.append(line)   # keep line as is (without comment)

    # Append the last block
    if current_command is not None:
        blocks.append((current_command, current_args))
    return blocks


async def run_program(blocks: list, command_dict: dict) -> None:
    """Execute commands sequentially, calling handlers from the dictionary."""
    for name, args in blocks:
        handler = command_dict.get(name)
        if handler:
            await handler(args)
        else:
            print(f"Unknown command: {name}")


async def interpret(text: str, command_dict: dict) -> None:
    """Full interpretation cycle: parsing and execution."""
    blocks = await parse_program(text)
    await run_program(blocks, command_dict)
