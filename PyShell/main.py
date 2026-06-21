"""
PyShell — A Mini Operating System Simulator (CLI)
====================================================
Step 1: Shell skeleton — REPL loop, command parsing, dispatch table.

Future modules (filesystem.py, process.py, scheduler.py, memory.py) will
register their own commands into COMMAND_TABLE (defined in shell_core.py)
without needing to touch this file's core loop.
"""

import shlex
import sys

from shell_core import COMMAND_TABLE, register_command

# ----------------------------------------------------------------------
# Shell metadata
# ----------------------------------------------------------------------
SHELL_NAME = "PyShell"
SHELL_VERSION = "0.1"
PROMPT = "pyshell> "


# ----------------------------------------------------------------------
# Built-in commands (Step 1 baseline set)
# ----------------------------------------------------------------------

@register_command("help", "List all available commands")
def cmd_help(args):
    if args:
        # help <command> -> show detail for a single command
        name = args[0]
        if name in COMMAND_TABLE:
            _, help_text = COMMAND_TABLE[name]
            print(f"{name} - {help_text}")
        else:
            print(f"No such command: {name}")
        return

    print(f"{SHELL_NAME} v{SHELL_VERSION} — available commands:\n")
    for name in sorted(COMMAND_TABLE.keys()):
        _, help_text = COMMAND_TABLE[name]
        print(f"  {name:<12} {help_text}")


@register_command("clear", "Clear the terminal screen")
def cmd_clear(args):
    # ANSI escape sequence: clear screen + move cursor to top-left
    print("\033[2J\033[H", end="")


@register_command("exit", "Exit PyShell")
def cmd_exit(args):
    print("Shutting down PyShell kernel...")
    sys.exit(0)


@register_command("echo", "Print the given text back to the terminal")
def cmd_echo(args):
    print(" ".join(args))


# ----------------------------------------------------------------------
# Core REPL loop
# ----------------------------------------------------------------------

def parse_input(raw_line):
    """
    Splits a raw input line into (command, args_list).
    Uses shlex so quoted strings like:  touch "my file.txt"
    are handled correctly as a single argument.
    """
    try:
        tokens = shlex.split(raw_line)
    except ValueError as e:
        # Unbalanced quotes etc.
        print(f"PyShell: parse error: {e}")
        return None, []

    if not tokens:
        return None, []

    command = tokens[0]
    args = tokens[1:]
    return command, args


def dispatch(command, args):
    """
    Looks up the command in COMMAND_TABLE and runs it.
    Unknown commands print a friendly error instead of crashing.
    """
    if command in COMMAND_TABLE:
        func, _ = COMMAND_TABLE[command]
        try:
            func(args)
        except Exception as e:
            # Defensive: a bug in one command should never crash the whole shell
            print(f"PyShell: error while running '{command}': {e}")
    else:
        print(f"PyShell: command not found: {command}  (type 'help' to list commands)")


def run_shell():
    """Main REPL loop: Read -> Eval -> Print -> Loop."""
    print(f"{SHELL_NAME} v{SHELL_VERSION} — type 'help' for a list of commands, 'exit' to quit.\n")

    while True:
        try:
            raw_line = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D or Ctrl+C -> exit gracefully instead of an ugly traceback
            print("\nShutting down PyShell kernel...")
            break

        command, args = parse_input(raw_line)
        if command is None:
            continue  # empty line, just show the prompt again

        dispatch(command, args)


if __name__ == "__main__":
    # Import side-modules here (not at the top of the file) so that they
    # can safely do "from main import register_command" without hitting
    # a circular-import error. Each import below registers that module's
    # commands into COMMAND_TABLE as a side effect.
    import filesystem  # noqa: F401  (registers: pwd, ls, cd, mkdir, touch, cat, rm, tree)
    import process      # noqa: F401  (registers: spawn, ps, kill)
    import scheduler    # noqa: F401  (registers: schedule)
    import memory       # noqa: F401  (registers: meminfo, alloc, free, memreset)

    run_shell()
