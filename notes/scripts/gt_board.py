"""Ground-truth scoreboard: every screen's best-12 deck shape vs the human medians (loop.py's ground_truth), sorted by time."""
import sys, os
from pathlib import Path
ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import loop
rows = []
for p in [*(ROOT / "runs" / "screens").glob("*/log.jsonl"), *(ROOT / "runs" / "screens").glob("*/*/log.jsonl")]:
    g = loop.ground_truth(p)                         # one level down too: runs with seed subfolders (C91-round479k/s5)
    if g:
        rows.append((p.stat().st_mtime, p.parent.relative_to(ROOT / "runs" / "screens").as_posix(), g))
rows.sort()
import time
for t, name, g in rows:
    P, T, E = g["top12"]
    print(f"{time.strftime('%m-%d %H:%M', time.localtime(t))}  {name[:34]:34s} it{g['iter']:>4}  "
          f"{P:5.1f}/{T:5.1f}/{E:5.1f}  dist {g['dist']:5.1f} mean5 {g['dist5']:5.1f}  med {g['median']}")
