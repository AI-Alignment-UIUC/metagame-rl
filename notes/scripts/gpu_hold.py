"""Row 73's hold, shared by the overnight queue drivers (overnight_c84.py, queue_c90.py)."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import loop                                              # noqa: E402

GPU_PAUSE = ROOT / "runs" / "GPU-PAUSE"   # Evan's pause (333-10 creates and removes it): arms checkpoint and wait (22:25)


def hold(log, stop=None) -> bool:
    """Row 73: wait while runs/GPU-PAUSE exists, free RAM < 2 GB or GPU memory > 80%, or nvidia-smi can't be read
    (loop.gpu_mem: 30 s timeout, None on failure). True once clear; False if stop() is true, checked on every pass
    (before a clear GPU returns True too, so a STOP made during a caller's sleep is seen before its next launch)."""
    while True:
        if stop and stop():
            return False
        free, _ = loop.ram_gb()
        g = loop.gpu_mem()                               # (used, total) GB, or None
        if not GPU_PAUSE.exists() and free >= 2 and g and g[0] <= 0.8 * g[1]:
            return True
        gpu = f"GPU {g[0] * 1024:.0f} of {g[1] * 1024:.0f} MiB" if g else "GPU memory unreadable (nvidia-smi)"
        log(f"holding: {'GPU-PAUSE, ' if GPU_PAUSE.exists() else ''}free RAM {free:.1f} GB, {gpu}")
        time.sleep(120)
