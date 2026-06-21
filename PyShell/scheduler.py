"""
PyShell — scheduler.py
=========================
Step 4: CPU Scheduler.

Operates on the PCBs created by process.py (spawn/ps/kill). Implements
four classic scheduling algorithms and renders a text Gantt chart plus
a results table (CT / TAT / WT + averages) — the same metrics KernelX
shows visually, just rendered as ASCII here.

Command: schedule <fcfs|sjf|priority|rr> [quantum]
"""

import copy

from shell_core import register_command
from process import get_all_processes, READY, TERMINATED


# ----------------------------------------------------------------------
# Gantt chart rendering
# ----------------------------------------------------------------------

def render_gantt_chart(timeline):
    """
    timeline: list of (name, start_time, end_time) tuples, in execution order.
    Prints something like:

        |  editor  |  browser  |  compiler  |
        0          5           13           16
    """
    if not timeline:
        print("(nothing was scheduled)")
        return

    top_row = "|"
    bottom_row = ""
    cursor = 0  # tracks the running width of top_row, to align bottom markers

    for name, start, end in timeline:
        label = f" {name} "
        cell = label + "|"
        top_row += cell

        # place the start-time marker under the left edge of this cell
        marker = str(start)
        padding = cursor - len(bottom_row)
        if padding > 0:
            bottom_row += " " * padding
        bottom_row += marker

        cursor += len(cell)

    # final end-time marker under the rightmost edge
    last_end = str(timeline[-1][2])
    padding = cursor - len(bottom_row)
    if padding > 0:
        bottom_row += " " * padding
    bottom_row += last_end

    print(top_row)
    print(bottom_row)


# ----------------------------------------------------------------------
# Results table
# ----------------------------------------------------------------------

def print_results_table(pcbs):
    header = f"{'PID':<5} {'NAME':<12} {'ARRIVAL':<8} {'BURST':<7} {'CT':<6} {'TAT':<6} {'WT':<6}"
    print()
    print(header)
    print("-" * len(header))

    total_tat = 0
    total_wt = 0
    for p in pcbs:
        print(
            f"{p.pid:<5} {p.name:<12} {p.arrival_time:<8} {p.burst_time:<7} "
            f"{p.completion_time:<6} {p.turnaround_time:<6} {p.waiting_time:<6}"
        )
        total_tat += p.turnaround_time
        total_wt += p.waiting_time

    n = len(pcbs)
    avg_tat = total_tat / n
    avg_wt = total_wt / n
    print("-" * len(header))
    print(f"Average Turnaround Time: {avg_tat:.2f}")
    print(f"Average Waiting Time:    {avg_wt:.2f}")


def finalize(original_pcb, sim_pcb):
    """Copies computed results from the simulation copy back onto the real PCB
    in process_table, and marks it TERMINATED."""
    original_pcb.completion_time = sim_pcb.completion_time
    original_pcb.turnaround_time = sim_pcb.turnaround_time
    original_pcb.waiting_time = sim_pcb.waiting_time
    original_pcb.remaining_time = 0
    original_pcb.state = TERMINATED


# ----------------------------------------------------------------------
# Algorithms
# Each takes a list of PCB copies and returns (ordered_results, timeline)
#   ordered_results: PCBs with CT/TAT/WT filled in (any order)
#   timeline: list of (name, start, end) for the Gantt chart
# ----------------------------------------------------------------------

def run_fcfs(pcbs):
    pcbs = sorted(pcbs, key=lambda p: p.arrival_time)
    time = 0
    timeline = []

    for p in pcbs:
        if time < p.arrival_time:
            time = p.arrival_time
        start = time
        time += p.burst_time
        p.completion_time = time
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time
        timeline.append((p.name, start, time))

    return pcbs, timeline


def run_sjf(pcbs):
    """Non-preemptive Shortest Job First."""
    remaining = list(pcbs)
    completed = []
    timeline = []
    time = 0

    while remaining:
        available = [p for p in remaining if p.arrival_time <= time]
        if not available:
            # CPU idle until the next process arrives
            next_arrival = min(p.arrival_time for p in remaining)
            time = next_arrival
            continue

        p = min(available, key=lambda x: x.burst_time)
        start = time
        time += p.burst_time
        p.completion_time = time
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time

        timeline.append((p.name, start, time))
        completed.append(p)
        remaining.remove(p)

    return completed, timeline


def run_priority(pcbs):
    """Non-preemptive Priority Scheduling (lower number = higher priority)."""
    remaining = list(pcbs)
    completed = []
    timeline = []
    time = 0

    while remaining:
        available = [p for p in remaining if p.arrival_time <= time]
        if not available:
            next_arrival = min(p.arrival_time for p in remaining)
            time = next_arrival
            continue

        p = min(available, key=lambda x: x.priority)
        start = time
        time += p.burst_time
        p.completion_time = time
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time

        timeline.append((p.name, start, time))
        completed.append(p)
        remaining.remove(p)

    return completed, timeline


def run_round_robin(pcbs, quantum):
    pcbs = sorted(pcbs, key=lambda p: p.arrival_time)
    n = len(pcbs)
    time = 0
    queue = []
    completed = []
    timeline = []

    arrived_index = 0  # next process in `pcbs` (by arrival order) not yet queued

    # seed the queue with whatever has arrived at time 0
    while arrived_index < n and pcbs[arrived_index].arrival_time <= time:
        queue.append(pcbs[arrived_index])
        arrived_index += 1

    while queue:
        p = queue.pop(0)
        if time < p.arrival_time:
            time = p.arrival_time

        slice_time = min(p.remaining_time, quantum)
        start = time
        time += slice_time
        p.remaining_time -= slice_time
        timeline.append((p.name, start, time))

        # enqueue any processes that have arrived during this slice
        while arrived_index < n and pcbs[arrived_index].arrival_time <= time:
            queue.append(pcbs[arrived_index])
            arrived_index += 1

        if p.remaining_time > 0:
            queue.append(p)
        else:
            p.completion_time = time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            completed.append(p)

    return completed, timeline


ALGORITHMS = {
    "fcfs": lambda pcbs, quantum: run_fcfs(pcbs),
    "sjf": lambda pcbs, quantum: run_sjf(pcbs),
    "priority": lambda pcbs, quantum: run_priority(pcbs),
    "rr": lambda pcbs, quantum: run_round_robin(pcbs, quantum),
}


# ----------------------------------------------------------------------
# Command
# ----------------------------------------------------------------------

@register_command(
    "schedule",
    "Run a scheduling algorithm on READY processes: schedule <fcfs|sjf|priority|rr> [quantum]"
)
def cmd_schedule(args):
    if not args:
        print("schedule: usage: schedule <fcfs|sjf|priority|rr> [quantum]")
        return

    algo = args[0].lower()
    if algo not in ALGORITHMS:
        print(f"schedule: unknown algorithm '{algo}'. Choose from: fcfs, sjf, priority, rr")
        return

    quantum = None
    if algo == "rr":
        if len(args) < 2:
            print("schedule: rr requires a quantum, e.g. 'schedule rr 2'")
            return
        try:
            quantum = int(args[1])
        except ValueError:
            print(f"schedule: quantum must be an integer, got '{args[1]}'")
            return
        if quantum <= 0:
            print("schedule: quantum must be a positive integer")
            return

    real_pcbs = [p for p in get_all_processes() if p.state == READY]
    if not real_pcbs:
        print("schedule: no READY processes to schedule. Use 'spawn' first.")
        return

    # Work on deep copies so a half-finished simulation never corrupts
    # the real process_table if something goes wrong mid-run.
    sim_pcbs = copy.deepcopy(real_pcbs)
    real_by_pid = {p.pid: p for p in real_pcbs}

    print(f"Running {algo.upper()} scheduler on {len(sim_pcbs)} process(es)...\n")

    completed, timeline = ALGORITHMS[algo](sim_pcbs, quantum)

    print("Gantt Chart:")
    render_gantt_chart(timeline)

    # sort results by PID for a stable, readable table
    completed_sorted = sorted(completed, key=lambda p: p.pid)
    print_results_table(completed_sorted)

    # commit results back to the real process table
    for sim_pcb in completed_sorted:
        finalize(real_by_pid[sim_pcb.pid], sim_pcb)
