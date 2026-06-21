"""
PyShell — shell_core.py
=========================
Holds the shared command registry (COMMAND_TABLE) and the register_command
decorator. Both main.py and every feature module (filesystem.py, process.py,
scheduler.py, memory.py, ...) import FROM HERE instead of from main.py.

Why this file exists:
    If feature modules did "from main import register_command", running
    `python main.py` loads main.py as "__main__", but the import statement
    re-imports it AGAIN under the name "main" — creating two separate
    copies of COMMAND_TABLE. Commands would register into one copy while
    the shell loop reads from the other, and nothing would ever be found.
    Keeping the shared state in its own small module sidesteps that
    entirely, since shell_core.py is only ever loaded once either way.

Also holds run_command_captured(), used by the Flask web backend (app.py)
to call a command and get back whatever it printed as a plain string —
without changing a single line in filesystem.py / process.py / scheduler.py
/ memory.py. Those files keep using plain print() for CLI mode; the capture
just temporarily redirects stdout while the command runs.
"""

import io
import contextlib

COMMAND_TABLE = {}


def register_command(name, help_text):
    """
    Decorator to register a function as a shell command.
    Usage:
        @register_command("hello", "prints a greeting")
        def cmd_hello(args):
            print("hi!")
    """
    def decorator(func):
        COMMAND_TABLE[name] = (func, help_text)
        return func
    return decorator


def run_command_captured(command, args):
    """
    Runs a registered command and returns (output_text, error_text).

    output_text: everything the command printed (joined as one string),
                 or a "command not found" message if it doesn't exist.
    error_text:  None normally; set to a message if the command raised
                 an exception (mirrors main.py's dispatch() behaviour).

    This does NOT touch filesystem.py/process.py/scheduler.py/memory.py —
    they still just call print() like always. We simply swap out stdout
    for a buffer while the function runs, then swap it back.
    """
    if command not in COMMAND_TABLE:
        return f"PyShell: command not found: {command}  (type 'help' to list commands)", None

    func, _ = COMMAND_TABLE[command]
    buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(buffer):
            func(args)
    except Exception as e:
        return buffer.getvalue(), f"PyShell: error while running '{command}': {e}"

    return buffer.getvalue(), None
