# interpreter.py

def strip_comment(line: str) -> str:
    idx = line.find('#')
    if idx != -1:
        return line[:idx]
    return line

def normalize_command_name(raw_name: str) -> str:
    return " ".join(raw_name.split()).lower()

def parse_program(text: str) -> list:
    blocks = []
    current_command = None
    current_args = []

    for raw_line in text.splitlines():
        line = strip_comment(raw_line)
        if not line.strip():
            continue

        # Command must start with ':' at first character (no leading spaces)
        if line.startswith(':'):
            if current_command is not None:
                blocks.append((current_command, current_args))
            command_part = line[1:].strip()
            if command_part:
                current_command = normalize_command_name(command_part)
                current_args = []
            else:
                current_command = None
                current_args = []
        else:
            if current_command is not None:
                current_args.append(line)   # preserve all leading spaces

    if current_command is not None:
        blocks.append((current_command, current_args))
    return blocks

def run_program(blocks, command_dict):
    for name, args in blocks:
        handler = command_dict.get(name)
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {name}")

def interpret(text, command_dict):
    blocks = parse_program(text)
    run_program(blocks, command_dict)

