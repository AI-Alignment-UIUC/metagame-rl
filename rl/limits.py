"""Load caps for this machine (CLAUDE.md, "Machine load limits").

It crashed or hung three times on 2026-10-04 to 06, so jobs keep to about 80% of it: GPU memory
at most 80% of the card, and at most 80% of the CPU threads (16 of 20). Each Node rollout worker
runs ONNX single-threaded, so it uses about one core; the Python process keeps the rest.

GPU *utilization* is held to ~80% in training updates by Pace (rests a quarter of each step);
the watchdog warns when the card still sits near 100% or runs hot. The hard cap is a lower power limit set from an admin shell
(nvidia-smi -pl 240).

Shares (the lab, rl/lab.py and notes/plan-lab.md): RL_GPU_SHARE (e.g. 0.333) holds a process and its children to that
share of the GPU, in memory (the per-process fraction) and in time (Pace rests 1 / share - 1 of each step, and the
inference server as much of each served batch), so Evan can use the rest of the card; RL_CPU_THREADS caps the threads
the same way. Unset, nothing changes.
"""
import os
import subprocess
import sys
import threading
import time

import torch

LOAD = 0.8
CPU_THREADS = max(1, int((os.cpu_count() or 1) * LOAD))    # 16 of 20
if os.environ.get("RL_CPU_THREADS"):
    CPU_THREADS = max(3, min(CPU_THREADS, int(os.environ["RL_CPU_THREADS"])))
MAX_WORKERS = max(1, CPU_THREADS - 2)                       # 14: two threads left for Python
_share = os.environ.get("RL_GPU_SHARE")
GPU_SHARE = min(LOAD, float(_share)) if _share else LOAD    # of the card, in memory and in time
GPU_MEM_FRACTION = GPU_SHARE
SERVER_PACE = 1 / GPU_SHARE - 1 if _share else 0.0          # the inference server's least rest (rl/remote.py)
WARN_UTIL, WARN_TEMP = 95, 83                               # %, degrees C
_watching = False


def cap_workers(n: int) -> int:
    if n > MAX_WORKERS:
        print(f"[limits] --workers {n} -> {MAX_WORKERS} (load cap, CLAUDE.md)", file=sys.stderr)
    return min(n, MAX_WORKERS)


def apply(device: str, workers: int = 0, mem_fraction: float = GPU_MEM_FRACTION, watch: bool = True):
    """Caps this process's threads and GPU memory; call before building models or workers."""
    torch.set_num_threads(max(1, min(torch.get_num_threads(), CPU_THREADS - workers)))
    if device == "cuda":
        # The allocator frees its cache before failing, so a lower cap costs speed, not the run.
        torch.cuda.set_per_process_memory_fraction(min(mem_fraction or GPU_MEM_FRACTION, GPU_MEM_FRACTION))
        if watch:
            _watch()


def _watch(every: float = 30.0, strikes: int = 3):
    """Warns on stderr when the GPU sits at >= WARN_UTIL% for `strikes` polls in a row, or runs hot. One per process."""
    global _watching
    if _watching:
        return
    _watching = True
    def loop():
        hot = 0
        while True:
            time.sleep(every)
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu",
                                      "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
                util, temp = (int(x) for x in out.split("\n")[0].split(","))
            except (OSError, ValueError, subprocess.SubprocessError):
                return
            hot = hot + 1 if util >= WARN_UTIL else 0
            if hot == strikes or temp >= WARN_TEMP:
                print(f"[limits] GPU at {util}% / {temp} C: lower --concurrency or the batch size "
                      f"(cap is ~80%, CLAUDE.md)", file=sys.stderr)
    threading.Thread(target=loop, daemon=True, name="gpu-watch").start()


class Pace:
    """Keeps the GPU busy at most LOAD of the time in a loop of GPU steps: each tick() waits for
    the GPU, then sleeps (1 / LOAD - 1) x the time since the last tick (a quarter of it at 0.8).
    Costs that share of the loop's wall time; a no-op on the CPU."""

    def __init__(self, device: str, load: float = LOAD):
        load = min(load, GPU_SHARE)
        self.on = device == "cuda" and load < 1
        self.rest = 1 / load - 1 if self.on else 0.0
        self.t = time.perf_counter()

    def tick(self):
        if not self.on:
            return
        torch.cuda.synchronize()
        now = time.perf_counter()
        time.sleep((now - self.t) * self.rest)
        self.t = time.perf_counter()
