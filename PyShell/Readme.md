# Example Execution

## File System Simulation

```bash
pwd
/
```

Displays the current working directory.

```bash
mkdir notes
cd notes
touch todo.txt
ls
```

Output:

```bash
todo.txt
```

Creates a directory, navigates into it, creates a file, and lists its contents.

```bash
tree
```

Output:

```text
/
└── notes/
    └── todo.txt
```

Displays the complete file system hierarchy.

---

## Process Management

### Create Processes

```bash
spawn editor 5
spawn browser 3 2
spawn compiler 4 1
```

Output:

```text
Process spawned: PID=1 name=editor burst=5 priority=1
Process spawned: PID=2 name=browser burst=3 priority=2
Process spawned: PID=3 name=compiler burst=4 priority=1
```

### View Process Table

```bash
ps
```

Output:

```text
PID  NAME      STATE   BURST  PRIO
1    editor    READY   5      1
2    browser   READY   3      2
3    compiler  READY   4      1
```

---

## CPU Scheduling (FCFS)

```bash
schedule fcfs
```

Output:

```text
Gantt Chart:
| editor | browser | compiler |
0        5         8          12

Average Turnaround Time: 7.33
Average Waiting Time: 3.33
```

The scheduler executes processes according to arrival order and calculates CT, TAT, and WT metrics.

---

## Memory Allocation

### View Memory Layout

```bash
meminfo
```

Output:

```text
Total Memory: 420 KB
Allocated: 0 KB
Free: 420 KB
```

### Allocate Memory

```bash
alloc P1 45
```

Output:

```text
Allocated 45 KB to P1
55 KB split off as free block
```

### Release Memory

```bash
free P1
```

Output:

```text
Freed block owned by P1
Adjacent free blocks coalesced
```

The allocator supports First Fit, Best Fit, and Worst Fit strategies with block splitting and coalescing.
