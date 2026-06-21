"""
PyShell — filesystem.py
=========================
Step 2: Virtual File System (in-memory tree).

This module owns:
  - The Node / File / Directory data structures
  - Path resolution (absolute "/a/b/c" and relative "a/../b")
  - The commands: pwd, ls, cd, mkdir, touch, cat, rm

It registers its commands into main.py's COMMAND_TABLE via register_command,
so main.py never needs to know the details of how the file system works.
"""

from shell_core import register_command


# ----------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------

class Node:
    """Base class for anything that lives in the virtual file system."""

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent  # None only for the root directory

    def get_path(self):
        """Builds the full absolute path by walking up to the root."""
        if self.parent is None:
            return "/"
        parts = []
        node = self
        while node.parent is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))


class File(Node):
    """A leaf node holding text content."""

    def __init__(self, name, parent=None, content=""):
        super().__init__(name, parent)
        self.content = content


class Directory(Node):
    """A folder that can contain other Files and Directories."""

    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.children = {}  # name -> Node (File or Directory)

    def is_empty(self):
        return len(self.children) == 0


# ----------------------------------------------------------------------
# Filesystem state
# ----------------------------------------------------------------------

root = Directory("/")
cwd = root  # current working directory pointer; "cd" mutates this


# ----------------------------------------------------------------------
# Path resolution
# ----------------------------------------------------------------------

def resolve_path(path):
    """
    Resolves a path string (absolute or relative) to a Node, starting
    from root (if path starts with "/") or from cwd otherwise.

    Supports "." (here) and ".." (parent) segments, e.g.:
        "/a/b/../c"  ->  "/a/c"
        "../x"       ->  parent of cwd, then "x"

    Returns the Node, or None if the path doesn't exist.
    Raises ValueError if a path segment tries to descend into a File
    (e.g. "/somefile.txt/foo" — a file can't have children).
    """
    if path == "":
        return cwd

    if path.startswith("/"):
        current = root
    else:
        current = cwd

    segments = [seg for seg in path.split("/") if seg != ""]

    for seg in segments:
        if seg == ".":
            continue
        elif seg == "..":
            if current.parent is not None:
                current = current.parent
            # if already at root, ".." is a no-op (same as real shells)
        else:
            if not isinstance(current, Directory):
                raise ValueError(f"'{current.name}' is not a directory")
            if seg not in current.children:
                return None
            current = current.children[seg]

    return current


def resolve_parent_and_name(path):
    """
    Splits a path into (parent_directory_node, final_name_segment).
    Useful for commands like mkdir/touch/rm that need to know WHERE
    to create/remove something, not just resolve to it.

    Example: resolve_parent_and_name("/a/b/newfile.txt")
             -> (Directory "b", "newfile.txt")

    Returns (None, name) if the parent path doesn't exist.
    """
    if "/" not in path.rstrip("/"):
        # Simple relative name, e.g. "newfile.txt" -> parent is cwd
        return cwd, path

    parent_path, _, name = path.rstrip("/").rpartition("/")
    parent_node = resolve_path(parent_path if parent_path != "" else "/")
    return parent_node, name


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------

@register_command("pwd", "Print the current working directory")
def cmd_pwd(args):
    print(cwd.get_path())


@register_command("ls", "List contents of a directory (default: current directory)")
def cmd_ls(args):
    target = cwd
    if args:
        target = resolve_path(args[0])
        if target is None:
            print(f"ls: cannot access '{args[0]}': No such file or directory")
            return

    if isinstance(target, File):
        # "ls somefile.txt" -> just print its name, like real ls
        print(target.name)
        return

    if target.is_empty():
        return  # real ls prints nothing for an empty directory

    # Directories shown with a trailing slash so they're visually distinct
    names = []
    for name, node in sorted(target.children.items()):
        if isinstance(node, Directory):
            names.append(name + "/")
        else:
            names.append(name)
    print("  ".join(names))


@register_command("cd", "Change the current working directory")
def cmd_cd(args):
    global cwd
    path = args[0] if args else "/"

    target = resolve_path(path)
    if target is None:
        print(f"cd: no such file or directory: {path}")
        return
    if isinstance(target, File):
        print(f"cd: not a directory: {path}")
        return

    cwd = target


@register_command("mkdir", "Create a new directory")
def cmd_mkdir(args):
    if not args:
        print("mkdir: missing operand (usage: mkdir <name>)")
        return

    for path in args:
        parent, name = resolve_parent_and_name(path)
        if parent is None:
            print(f"mkdir: cannot create directory '{path}': No such parent directory")
            continue
        if not isinstance(parent, Directory):
            print(f"mkdir: cannot create directory '{path}': parent is not a directory")
            continue
        if name in parent.children:
            print(f"mkdir: cannot create directory '{name}': already exists")
            continue
        if name == "":
            print(f"mkdir: invalid directory name in '{path}'")
            continue

        parent.children[name] = Directory(name, parent=parent)


@register_command("touch", "Create a new empty file (or update if it already exists)")
def cmd_touch(args):
    if not args:
        print("touch: missing operand (usage: touch <name>)")
        return

    for path in args:
        parent, name = resolve_parent_and_name(path)
        if parent is None:
            print(f"touch: cannot touch '{path}': No such parent directory")
            continue
        if not isinstance(parent, Directory):
            print(f"touch: cannot touch '{path}': parent is not a directory")
            continue

        if name in parent.children:
            # Already exists — real `touch` just updates timestamps;
            # we have no timestamps yet, so this is effectively a no-op.
            continue

        parent.children[name] = File(name, parent=parent, content="")


@register_command("cat", "Print the contents of a file")
def cmd_cat(args):
    if not args:
        print("cat: missing operand (usage: cat <filename>)")
        return

    for path in args:
        node = resolve_path(path)
        if node is None:
            print(f"cat: {path}: No such file or directory")
            continue
        if isinstance(node, Directory):
            print(f"cat: {path}: Is a directory")
            continue
        print(node.content)


@register_command("rm", "Remove a file or directory (use -r to remove a non-empty directory)")
def cmd_rm(args):
    if not args:
        print("rm: missing operand (usage: rm [-r] <name>)")
        return

    recursive = "-r" in args
    targets = [a for a in args if a != "-r"]

    for path in targets:
        parent, name = resolve_parent_and_name(path)
        if parent is None or not isinstance(parent, Directory) or name not in parent.children:
            print(f"rm: cannot remove '{path}': No such file or directory")
            continue

        node = parent.children[name]
        if isinstance(node, Directory) and not node.is_empty() and not recursive:
            print(f"rm: cannot remove '{path}': Directory not empty (use -r to force)")
            continue

        del parent.children[name]


@register_command("tree", "Show the directory structure as a tree (debug helper)")
def cmd_tree(args):
    start = cwd
    if args:
        start = resolve_path(args[0])
        if start is None:
            print(f"tree: cannot access '{args[0]}': No such file or directory")
            return

    def _print_tree(node, prefix=""):
        if isinstance(node, Directory):
            items = sorted(node.children.items())
            for i, (name, child) in enumerate(items):
                connector = "└── " if i == len(items) - 1 else "├── "
                suffix = "/" if isinstance(child, Directory) else ""
                print(prefix + connector + name + suffix)
                extension = "    " if i == len(items) - 1 else "│   "
                _print_tree(child, prefix + extension)

    print(start.get_path())
    _print_tree(start)
