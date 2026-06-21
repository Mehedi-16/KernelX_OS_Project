"""
PyShell — memory.py
=========================
Step 5 (final module): Dynamic Memory Allocator.

Same core logic as KernelX's allocator.html (First/Best/Worst Fit with
proper block splitting so free space is never silently lost), rendered
as text here instead of as colored boxes.

Commands: meminfo, alloc, free
"""

from shell_core import register_command


# ----------------------------------------------------------------------
# Block data structure
# ----------------------------------------------------------------------

class Block:
    """A single contiguous region of RAM — either free, or owned by a pid."""

    def __init__(self, block_id, size, pid=None):
        self.id = block_id
        self.size = size
        self.pid = pid

    @property
    def allocated(self):
        return self.pid is not None


# ----------------------------------------------------------------------
# Memory state
# ----------------------------------------------------------------------

_block_id_seq = [0]


def _new_block(size, pid=None):
    block = Block(_block_id_seq[0], size, pid)
    _block_id_seq[0] += 1
    return block


def _initial_layout():
    """Same starting partitions as KernelX's allocator, in KB."""
    _block_id_seq[0] = 0
    return [_new_block(s) for s in (30, 100, 40, 200, 50)]


memory_blocks = _initial_layout()


def total_ram():
    return sum(b.size for b in memory_blocks)


def find_block_by_pid(pid):
    for b in memory_blocks:
        if b.pid == pid:
            return b
    return None


# ----------------------------------------------------------------------
# Allocation strategies
# Each returns the index of the chosen free block in memory_blocks, or -1
# if no block is big enough.
# ----------------------------------------------------------------------

def find_first_fit(size):
    for i, b in enumerate(memory_blocks):
        if not b.allocated and b.size >= size:
            return i
    return -1


def find_best_fit(size):
    best_index = -1
    best_size = None
    for i, b in enumerate(memory_blocks):
        if not b.allocated and b.size >= size:
            if best_size is None or b.size < best_size:
                best_size = b.size
                best_index = i
    return best_index


def find_worst_fit(size):
    worst_index = -1
    worst_size = -1
    for i, b in enumerate(memory_blocks):
        if not b.allocated and b.size >= size and b.size > worst_size:
            worst_size = b.size
            worst_index = i
    return worst_index


FIT_STRATEGIES = {
    "first": find_first_fit,
    "best": find_best_fit,
    "worst": find_worst_fit,
}


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------

@register_command("meminfo", "Show the current RAM layout and fragmentation stats")
def cmd_meminfo(args):
    if not memory_blocks:
        print("meminfo: no memory blocks defined")
        return

    header = f"{'BLOCK':<8} {'SIZE(KB)':<10} {'STATUS':<12} {'OWNER':<8}"
    print(header)
    print("-" * len(header))

    allocated_total = 0
    free_total = 0
    free_count = 0
    largest_free = 0

    for i, b in enumerate(memory_blocks):
        if b.allocated:
            status, owner = "OCCUPIED", b.pid
            allocated_total += b.size
        else:
            status, owner = "FREE", "-"
            free_total += b.size
            free_count += 1
            largest_free = max(largest_free, b.size)

        print(f"[{i}]".ljust(8) + f"{b.size:<10} {status:<12} {owner:<8}")

    external_frag = (free_total - largest_free) if free_count > 1 else 0

    print("-" * len(header))
    print(f"Total Memory:           {total_ram()} KB")
    print(f"Allocated:               {allocated_total} KB")
    print(f"Free:                    {free_total} KB  (across {free_count} hole(s))")
    print(f"External Fragmentation:  {external_frag} KB")


@register_command("alloc", "Allocate memory: alloc <pid> <size> [first|best|worst]")
def cmd_alloc(args):
    if len(args) < 2:
        print("alloc: usage: alloc <pid> <size_kb> [first|best|worst]")
        return

    pid = args[0]

    try:
        size = int(args[1])
    except ValueError:
        print(f"alloc: size must be an integer, got '{args[1]}'")
        return
    if size <= 0:
        print("alloc: size must be a positive integer")
        return

    strategy = args[2].lower() if len(args) >= 3 else "first"
    if strategy not in FIT_STRATEGIES:
        print(f"alloc: unknown strategy '{strategy}'. Choose from: first, best, worst")
        return

    if find_block_by_pid(pid) is not None:
        print(f"alloc: pid '{pid}' already holds a block. Free it first.")
        return

    index = FIT_STRATEGIES[strategy](size)
    if index == -1:
        print(f"alloc: out of memory — no free block >= {size} KB for '{pid}' ({strategy} fit)")
        return

    block = memory_blocks[index]
    leftover = block.size - size

    block.size = size
    block.pid = pid

    if leftover > 0:
        # Split: insert a new FREE block right after, holding the leftover.
        # This is the fix that keeps fragmentation honest — no KB vanishes.
        memory_blocks.insert(index + 1, _new_block(leftover))

    msg = f"Allocated {size} KB to '{pid}' in block [{index}] ({strategy} fit)"
    if leftover > 0:
        msg += f", {leftover} KB split off as a new free block"
    print(msg)


@register_command("free", "Release a process's memory block: free <pid>")
def cmd_free(args):
    if not args:
        print("free: usage: free <pid>")
        return

    pid = args[0]
    block = find_block_by_pid(pid)
    if block is None:
        print(f"free: no block currently owned by '{pid}'")
        return

    idx = memory_blocks.index(block)
    block.pid = None

    # Coalesce with the next block if it's also free
    if idx < len(memory_blocks) - 1 and not memory_blocks[idx + 1].allocated:
        memory_blocks[idx].size += memory_blocks[idx + 1].size
        del memory_blocks[idx + 1]

    # Coalesce with the previous block if it's also free
    if idx > 0 and not memory_blocks[idx - 1].allocated:
        memory_blocks[idx - 1].size += memory_blocks[idx].size
        del memory_blocks[idx]

    print(f"Freed block owned by '{pid}'. Adjacent free holes coalesced.")


@register_command("memreset", "Reset RAM to its initial partition layout")
def cmd_memreset(args):
    global memory_blocks
    memory_blocks = _initial_layout()
    print("Memory layout reset to initial partitions.")
