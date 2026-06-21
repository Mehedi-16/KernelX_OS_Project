"""
PyShell — process.py
=========================
Step 3: Process Manager — the PCB (Process Control Block) list that the
Scheduler module (Step 4) will later operate on.

Commands: spawn, ps, kill
"""

from shell_core import register_command


# ----------------------------------------------------------------------
# Process states (mirrors the classic OS process state diagram)
# ----------------------------------------------------------------------
NEW = "NEW"
READY = "READY"
RUNNING = "RUNNING"
WAITING = "WAITING"
TERMINATED = "TERMINATED"


class PCB:
    """Process Control Block — everything the kernel needs to know about a process."""

    def __init__(self, pid, name, burst_time, priority, arrival_time):
        self.pid = pid
        self.name = name
        self.burst_time = burst_time      # total CPU time this process needs
        self.remaining_time = burst_time  # used later by the scheduler (e.g. Round Robin)
        self.priority = priority
        self.arrival_time = arrival_time
        self.state = NEW

        # Filled in once a scheduling algorithm actually runs this process:
        self.completion_time = None
        self.turnaround_time = None
        self.waiting_time = None

    def __repr__(self):
        return f"PCB(pid={self.pid}, name={self.name}, state={self.state})"


# ----------------------------------------------------------------------
# Process table (shared kernel state)
# ----------------------------------------------------------------------
process_table = {}   # pid -> PCB
_next_pid = [1]       # mutable container so helper funcs can bump it
_clock = [0]           # simulated system clock, advances once per spawn


def get_all_processes():
    """Returns all PCBs as a list, ordered by PID. Used by scheduler.py later."""
    return [process_table[pid] for pid in sorted(process_table.keys())]


def get_process(pid):
    """Returns the PCB for a given pid, or None if it doesn't exist."""
    return process_table.get(pid)


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------

@register_command("spawn", "Create a new process: spawn <name> <burst_time> [priority]")
def cmd_spawn(args):
    if len(args) < 2:
        print("spawn: usage: spawn <name> <burst_time> [priority]")
        return

    name = args[0]

    try:
        burst_time = int(args[1])
    except ValueError:
        print(f"spawn: burst_time must be an integer, got '{args[1]}'")
        return

    if burst_time <= 0:
        print("spawn: burst_time must be a positive integer")
        return

    priority = 1  # default priority if not given (1 = highest, like nice values)
    if len(args) >= 3:
        try:
            priority = int(args[2])
        except ValueError:
            print(f"spawn: priority must be an integer, got '{args[2]}'")
            return

    pid = _next_pid[0]
    _next_pid[0] += 1

    pcb = PCB(pid, name, burst_time, priority, arrival_time=_clock[0])
    pcb.state = READY  # a freshly spawned process goes straight to the ready queue
    process_table[pid] = pcb

    _clock[0] += 1  # advance the simulated clock so arrival_time has meaning

    print(f"Process spawned: PID={pid}  name={name}  burst={burst_time}  priority={priority}")


@register_command("ps", "List all processes (like a mini 'top')")
def cmd_ps(args):
    if not process_table:
        print("No active processes. Use 'spawn <name> <burst_time>' to create one.")
        return

    header = f"{'PID':<5} {'NAME':<12} {'STATE':<12} {'BURST':<7} {'PRIO':<6} {'ARRIVAL':<8}"
    print(header)
    print("-" * len(header))

    for pcb in get_all_processes():
        print(
            f"{pcb.pid:<5} {pcb.name:<12} {pcb.state:<12} "
            f"{pcb.remaining_time:<7} {pcb.priority:<6} {pcb.arrival_time:<8}"
        )


@register_command("kill", "Terminate a process: kill <pid>")
def cmd_kill(args):
    if not args:
        print("kill: usage: kill <pid>")
        return

    try:
        pid = int(args[0])
    except ValueError:
        print(f"kill: invalid pid '{args[0]}'")
        return

    pcb = get_process(pid)
    if pcb is None:
        print(f"kill: no such process: PID {pid}")
        return

    if pcb.state == TERMINATED:
        print(f"kill: PID {pid} is already terminated")
        return

    pcb.state = TERMINATED
    pcb.remaining_time = 0
    print(f"Process PID {pid} ({pcb.name}) terminated.")
